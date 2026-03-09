"""
共通利益計算エンジン
業種を問わず: 売上 - 原価 - 固定費 - 税金 = 利益
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Sequence


# ===== 共通データ型 =====

@dataclass
class StaffAssignment:
    name: str
    hours: float
    hourly_rate: int


@dataclass
class Project:
    """業種共通の案件/取引モデル"""
    id: str
    name: str              # 取引先名
    full_name: str         # 正式名称
    project_name: str      # 案件名/商品名
    revenue: int           # 売上
    cost: int              # 原価
    contract_month: int    # 契約月 (0-11 index)
    invoice_month: int     # 請求月
    payment_month: int     # 入金月
    contact: str = ""
    staff: list[StaffAssignment] = field(default_factory=list)
    progress: int = 0
    extra: dict = field(default_factory=dict)  # 業種固有データ


@dataclass
class Staff:
    """業種共通の社員モデル"""
    id: str
    short_name: str
    full_name: str
    role: str
    hourly_rate: int
    monthly_salary: int


@dataclass
class CompanyConfig:
    """会社設定"""
    name: str
    fixed_cost_monthly: int   # 月額固定費
    tax_rate: float           # 税率 (0.0-1.0)
    annual_target: int        # 年間売上目標
    target_margin: float      # 利益率目標 (0.0-1.0)
    staff_count: int = 0
    fiscal_months: list[str] = field(default_factory=lambda: [
        "4月", "5月", "6月", "7月", "8月", "9月",
        "10月", "11月", "12月", "1月", "2月", "3月",
    ])


@dataclass
class ViewData:
    """1つの経営視点の計算結果"""
    revenue: int
    cost: int
    fixed: int
    tax: int
    profit: int
    count: int


@dataclass
class ThreeViewResult:
    """3視点の計算結果"""
    future: ViewData   # 未来の数字 (契約済)
    now: ViewData      # 今の数字 (請求済)
    cash: ViewData     # キャッシュフロー (入金済)


# ===== 利益計算エンジン =====

class ProfitEngine:
    """
    業種共通の利益計算エンジン
    3つの経営視点（未来・今・キャッシュフロー）で利益を算出
    """

    def __init__(self, config: CompanyConfig):
        self.config = config

    def calc_view(
        self,
        revenue: int,
        cost: int,
        count: int,
        months: int,
        extra_revenue: int = 0,
    ) -> ViewData:
        """1つの視点の利益を計算"""
        rev = revenue + extra_revenue
        fixed = self.config.fixed_cost_monthly * months
        gross = rev - cost - fixed
        tax = max(0, int(gross * self.config.tax_rate))
        return ViewData(
            revenue=rev,
            cost=cost,
            fixed=fixed,
            tax=tax,
            profit=gross - tax,
            count=count,
        )

    def calc_three_views(
        self,
        projects: Sequence[Project],
        current_month: int,
        extra_revenue: int = 0,
    ) -> ThreeViewResult:
        """
        3つの経営視点で利益を計算

        - 未来: 契約済 (contract_month <= current_month)
        - 今:   請求済 (invoice_month <= current_month)
        - CF:   入金済 (payment_month <= current_month)
        """
        fu_rev, fu_cost, fu_cnt = 0, 0, 0
        nw_rev, nw_cost, nw_cnt = 0, 0, 0
        cf_rev, cf_cost, cf_cnt = 0, 0, 0

        for p in projects:
            if current_month >= p.contract_month:
                fu_rev += p.revenue
                fu_cost += p.cost
                fu_cnt += 1
            if current_month >= p.invoice_month:
                nw_rev += p.revenue
                nw_cost += p.cost
                nw_cnt += 1
            if current_month >= p.payment_month:
                cf_rev += p.revenue
                cf_cost += p.cost
                cf_cnt += 1

        months_future = current_month + 1
        months_cash = max(1, current_month)

        return ThreeViewResult(
            future=self.calc_view(fu_rev, fu_cost, fu_cnt, months_future, extra_revenue),
            now=self.calc_view(nw_rev, nw_cost, nw_cnt, months_future, extra_revenue),
            cash=self.calc_view(cf_rev, cf_cost, cf_cnt, months_cash, extra_revenue),
        )

    def gross_profit(self, project: Project) -> int:
        """案件の粗利"""
        return project.revenue - project.cost

    def gross_margin(self, project: Project) -> float:
        """案件の粗利率"""
        if project.revenue == 0:
            return 0.0
        return (project.revenue - project.cost) / project.revenue

    def labor_cost(self, project: Project) -> int:
        """案件の人件費 (工数ベース)"""
        return sum(s.hours * s.hourly_rate for s in project.staff)

    def net_profit(self, project: Project) -> int:
        """案件の純利益 (粗利 - 人件費)"""
        return self.gross_profit(project) - self.labor_cost(project)

    def achievement_rate(self, projects: Sequence[Project], current_month: int) -> float:
        """年間目標達成率"""
        contracted_rev = sum(
            p.revenue for p in projects if current_month >= p.contract_month
        )
        if self.config.annual_target == 0:
            return 0.0
        return contracted_rev / self.config.annual_target

    def working_capital_gap(self, result: ThreeViewResult) -> int:
        """運転資金ギャップ (未来利益 - CF利益)"""
        return result.future.profit - result.cash.profit

    def staff_utilization(
        self,
        staff: Staff,
        projects: Sequence[Project],
        current_month: int,
    ) -> dict:
        """社員の稼働状況"""
        total_hours = 0
        assigned_projects: list[str] = []
        for p in projects:
            if current_month < p.contract_month:
                continue
            for sa in p.staff:
                if sa.name == staff.short_name:
                    total_hours += sa.hours
                    assigned_projects.append(p.name)
        return {
            "staff_id": staff.id,
            "name": staff.full_name,
            "total_hours": total_hours,
            "projects": assigned_projects,
            "hourly_rate": staff.hourly_rate,
            "monthly_salary": staff.monthly_salary,
        }

    def project_status(self, project: Project, current_month: int) -> str:
        """案件のステータス"""
        if current_month >= project.payment_month:
            return "入金済"
        if current_month >= project.invoice_month:
            return "請求済"
        if current_month >= project.contract_month:
            return "契約済"
        return "未契約"

    def summary(
        self,
        projects: Sequence[Project],
        current_month: int,
        extra_revenue: int = 0,
    ) -> dict:
        """経営サマリを生成"""
        result = self.calc_three_views(projects, current_month, extra_revenue)
        gap = self.working_capital_gap(result)
        ach = self.achievement_rate(projects, current_month)
        total_rev = sum(p.revenue for p in projects)
        total_cost = sum(p.cost for p in projects)

        return {
            "three_views": result,
            "gap": gap,
            "achievement_rate": ach,
            "total_revenue": total_rev,
            "total_cost": total_cost,
            "total_gross_profit": total_rev - total_cost,
            "gross_margin": (total_rev - total_cost) / total_rev if total_rev else 0,
            "month_label": self.config.fiscal_months[current_month],
        }
