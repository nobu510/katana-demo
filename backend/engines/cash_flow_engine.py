"""
キャッシュフロー計算エンジン
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from .profit_engine import Project, CompanyConfig


@dataclass
class MonthlyCashFlow:
    month_index: int
    month_label: str
    inflow: int       # 入金額
    outflow: int      # 支出額 (原価+固定費)
    net: int           # 純CF
    cumulative: int    # 累積CF


class CashFlowEngine:
    """月別キャッシュフロー計算"""

    def __init__(self, config: CompanyConfig):
        self.config = config

    def monthly_cash_flows(
        self,
        projects: Sequence[Project],
    ) -> list[MonthlyCashFlow]:
        """12ヶ月のキャッシュフローを計算"""
        months = self.config.fiscal_months
        flows: list[MonthlyCashFlow] = []
        cumulative = 0

        for mi in range(12):
            inflow = sum(p.revenue for p in projects if p.payment_month == mi)
            cost_out = sum(p.cost for p in projects if p.contract_month == mi)
            outflow = cost_out + self.config.fixed_cost_monthly
            net = inflow - outflow
            cumulative += net
            flows.append(MonthlyCashFlow(
                month_index=mi,
                month_label=months[mi],
                inflow=inflow,
                outflow=outflow,
                net=net,
                cumulative=cumulative,
            ))

        return flows

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
