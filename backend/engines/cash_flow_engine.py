"""
キャッシュフロー計算エンジン

月別キャッシュフロー・資金繰り表・運転資金分析・資金ショート予測。
経営者が「今月いくら足りない/余る」を即座に把握できる。

全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .profit_engine import Project, CompanyConfig


# =====================================================================
# データ型
# =====================================================================

@dataclass
class MonthlyCashFlow:
    """月次キャッシュフロー"""
    month_index: int
    month_label: str
    inflow: int            # 入金額 (売上入金)
    outflow: int           # 支出額 (原価+固定費)
    net: int               # 純CF
    cumulative: int        # 累積CF
    # 内訳
    cost_outflow: int = 0  # 変動費支出
    fixed_outflow: int = 0 # 固定費支出
    financing: int = 0     # 財務CF (借入/返済)


@dataclass
class CashFlowForecast:
    """キャッシュフロー予測結果"""
    monthly_flows: list[MonthlyCashFlow]
    total_inflow: int
    total_outflow: int
    net_annual: int
    worst_month: MonthlyCashFlow
    peak_shortage: int           # 最大資金不足額
    months_until_positive: int | None
    needs_financing: bool        # 資金調達が必要か
    required_financing: int      # 必要調達額


@dataclass
class WorkingCapital:
    """運転資金分析"""
    accounts_receivable: int     # 売掛金 (入金待ち)
    accounts_payable: int        # 買掛金 (支払待ち)
    working_capital: int         # 運転資金 = 売掛金 - 買掛金
    average_collection_days: float   # 平均回収日数
    average_payment_days: float      # 平均支払日数
    cash_conversion_cycle: float     # キャッシュコンバージョンサイクル (日)


@dataclass
class FinancingItem:
    """資金調達/返済"""
    month_index: int
    amount: int                  # 正=調達, 負=返済
    description: str = ""


# =====================================================================
# キャッシュフローエンジン
# =====================================================================

class CashFlowEngine:
    """
    キャッシュフロー計算エンジン。
    月別CFの計算、資金繰り予測、運転資金分析を提供。
    """

    def __init__(self, config: CompanyConfig):
        self.config = config

    # ----- 月別キャッシュフロー -----

    def monthly_cash_flows(
        self,
        projects: Sequence[Project],
        beginning_cash: int = 0,
        financing: Sequence[FinancingItem] | None = None,
    ) -> list[MonthlyCashFlow]:
        """
        12ヶ月のキャッシュフローを計算。

        入金タイミング: payment_month
        原価支払タイミング: contract_month (着手時に発生と想定)
        固定費: 毎月固定
        """
        months = self.config.fiscal_months
        fin_by_month: dict[int, int] = {}
        if financing:
            for f in financing:
                fin_by_month[f.month_index] = fin_by_month.get(f.month_index, 0) + f.amount

        flows: list[MonthlyCashFlow] = []
        cumulative = beginning_cash

        for mi in range(12):
            inflow = sum(p.revenue for p in projects if p.payment_month == mi)
            cost_out = sum(p.cost for p in projects if p.contract_month == mi)
            fixed_out = self.config.fixed_cost_monthly
            fin = fin_by_month.get(mi, 0)
            outflow = cost_out + fixed_out
            net = inflow - outflow + fin
            cumulative += net

            flows.append(MonthlyCashFlow(
                month_index=mi,
                month_label=months[mi],
                inflow=inflow,
                outflow=outflow,
                net=net,
                cumulative=cumulative,
                cost_outflow=cost_out,
                fixed_outflow=fixed_out,
                financing=fin,
            ))

        return flows

    # ----- 資金繰り予測 -----

    def forecast(
        self,
        projects: Sequence[Project],
        beginning_cash: int = 0,
        financing: Sequence[FinancingItem] | None = None,
    ) -> CashFlowForecast:
        """キャッシュフロー予測の全体結果を返す"""
        flows = self.monthly_cash_flows(projects, beginning_cash, financing)

        total_in = sum(f.inflow for f in flows)
        total_out = sum(f.outflow for f in flows)
        worst = min(flows, key=lambda f: f.cumulative)
        peak_shortage = min(0, worst.cumulative)

        months_positive = None
        for f in flows:
            if f.cumulative > 0:
                months_positive = f.month_index + 1
                break

        needs_fin = peak_shortage < 0
        required = abs(peak_shortage) if needs_fin else 0

        return CashFlowForecast(
            monthly_flows=flows,
            total_inflow=total_in,
            total_outflow=total_out,
            net_annual=total_in - total_out,
            worst_month=worst,
            peak_shortage=peak_shortage,
            months_until_positive=months_positive,
            needs_financing=needs_fin,
            required_financing=required,
        )

    # ----- 運転資金分析 -----

    def working_capital_analysis(
        self,
        projects: Sequence[Project],
        current_month: int,
    ) -> WorkingCapital:
        """
        運転資金分析。

        売掛金: 請求済だが未入金の案件
        買掛金: 契約済だが未支払の原価
        CCC: 回収日数 - 支払日数 (短いほど資金効率が良い)
        """
        # 売掛金: 請求済 (invoice_month <= current) かつ 未入金 (payment_month > current)
        ar = sum(
            p.revenue for p in projects
            if p.invoice_month <= current_month < p.payment_month
        )

        # 買掛金: 契約済 (contract_month <= current) で原価発生中
        # 簡易: 原価は契約月に全額発生、支払は翌月と想定
        ap = sum(
            p.cost for p in projects
            if p.contract_month <= current_month < p.contract_month + 2
        )

        wc = ar - ap

        # 平均回収日数 (請求→入金の平均月数 × 30日)
        collection_months = []
        payment_months = []
        for p in projects:
            if p.revenue > 0:
                collection_months.append(p.payment_month - p.invoice_month)
                payment_months.append(max(1, p.contract_month + 1 - p.contract_month))

        avg_collection = (
            sum(collection_months) / len(collection_months) * 30
            if collection_months else 0
        )
        avg_payment = (
            sum(payment_months) / len(payment_months) * 30
            if payment_months else 0
        )

        return WorkingCapital(
            accounts_receivable=ar,
            accounts_payable=ap,
            working_capital=wc,
            average_collection_days=avg_collection,
            average_payment_days=avg_payment,
            cash_conversion_cycle=avg_collection - avg_payment,
        )

    # ----- ユーティリティ -----

    def worst_month(self, projects: Sequence[Project]) -> MonthlyCashFlow:
        """最もCFが厳しい月を特定"""
        flows = self.monthly_cash_flows(projects)
        return min(flows, key=lambda f: f.cumulative)

    def months_until_positive(self, projects: Sequence[Project]) -> int | None:
        """累積CFがプラスになるまでの月数"""
        flows = self.monthly_cash_flows(projects)
        for f in flows:
            if f.cumulative > 0:
                return f.month_index + 1
        return None

    def burn_rate(self, projects: Sequence[Project]) -> int:
        """月間バーンレート (固定費 + 平均変動費)"""
        total_cost = sum(p.cost for p in projects)
        avg_variable = total_cost // 12 if projects else 0
        return self.config.fixed_cost_monthly + avg_variable

    def runway_months(
        self,
        projects: Sequence[Project],
        current_cash: int,
    ) -> float:
        """現在の現金で何ヶ月持つか (ランウェイ)"""
        br = self.burn_rate(projects)
        if br <= 0:
            return float("inf")
        return current_cash / br

    def required_monthly_revenue(self) -> int:
        """損益分岐の月間売上 (固定費 / (1 - 税率))"""
        if self.config.tax_rate >= 1.0:
            return 0
        return int(self.config.fixed_cost_monthly / (1 - self.config.tax_rate))
