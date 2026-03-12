"""
利益計算エンジン
業種テンプレートに依存しない共通アルゴリズム。

3つの経営視点:
  未来の数字 = 契約済売上 - 原価 - 固定費 - 税金
  今の数字   = 請求済売上 - 原価 - 固定費 - 税金
  キャッシュフロー = 入金額 - 支払額 - 固定費 - 税金

案件別/商品別/社員別の利益計算を提供。
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


# =====================================================================
# 共通データ型
# =====================================================================

@dataclass
class StaffAssignment:
    """案件へのスタッフアサイン"""
    staff_id: str       # S001-C001 形式
    name: str
    hours: float
    hourly_rate: int


@dataclass
class Project:
    """業種共通の案件/商品モデル"""
    id: str                # P001-C001 形式
    name: str              # 取引先名
    full_name: str         # 正式名称
    project_name: str      # 案件名/商品名
    revenue: int           # 売上
    cost: int              # 原価 (外注費・材料費等の変動費)
    contract_month: int    # 契約月 (0-11, 4月=0)
    invoice_month: int     # 請求月
    payment_month: int     # 入金月
    contact: str = ""
    staff: list[StaffAssignment] = field(default_factory=list)
    progress: int = 0      # 進捗率 (0-100)
    category: str = ""     # 案件カテゴリ/商品カテゴリ
    extra: dict = field(default_factory=dict)


@dataclass
class Staff:
    """業種共通の社員モデル"""
    id: str                # S001-C001 形式
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
    tax_rate: float           # 概算税率 (0.0-1.0)
    annual_target: int        # 年間売上目標
    target_margin: float      # 利益率目標 (0.0-1.0)
    staff_count: int = 0
    fiscal_months: list[str] = field(default_factory=lambda: [
        "4月", "5月", "6月", "7月", "8月", "9月",
        "10月", "11月", "12月", "1月", "2月", "3月",
    ])


# =====================================================================
# 計算結果データ型
# =====================================================================

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


@dataclass
class ProjectProfit:
    """案件別利益"""
    project_id: str
    project_name: str
    revenue: int
    cost: int
    gross_profit: int
    gross_margin: float
    labor_cost: int
    net_profit: int
    status: str           # "未契約" / "契約済" / "請求済" / "入金済"


@dataclass
class StaffProfit:
    """社員別利益"""
    staff_id: str
    name: str
    monthly_salary: int
    total_hours: float
    total_labor_cost: int
    assigned_revenue: int     # 担当案件の売上合計
    assigned_profit: int      # 担当案件の粗利合計
    project_count: int
    projects: list[str]       # 担当案件名リスト


@dataclass
class CategoryProfit:
    """カテゴリ別（商品別）利益"""
    category: str
    revenue: int
    cost: int
    gross_profit: int
    gross_margin: float
    count: int


# =====================================================================
# 利益計算エンジン
# =====================================================================

class ProfitEngine:
    """
    業種共通の利益計算エンジン
    3つの経営視点 + 案件別/社員別/カテゴリ別の利益を算出
    """

    def __init__(self, config: CompanyConfig):
        self.config = config

    # ----- 基本計算 -----

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
        tax = max(0, int(gross * self.config.tax_rate)) if gross > 0 else 0
        return ViewData(
            revenue=rev, cost=cost, fixed=fixed,
            tax=tax, profit=gross - tax, count=count,
        )

    def calc_three_views(
        self,
        projects: Sequence[Project],
        current_month: int,
        extra_revenue: int = 0,
    ) -> ThreeViewResult:
        """
        3つの経営視点で利益を計算

        未来: 契約済 (contract_month <= current_month)
        今:   請求済 (invoice_month <= current_month)
        CF:   入金済 (payment_month <= current_month)
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

        months_elapsed = current_month + 1

        return ThreeViewResult(
            future=self.calc_view(fu_rev, fu_cost, fu_cnt, months_elapsed, extra_revenue),
            now=self.calc_view(nw_rev, nw_cost, nw_cnt, months_elapsed, extra_revenue),
            cash=self.calc_view(cf_rev, cf_cost, cf_cnt, months_elapsed, extra_revenue),
        )

    # ----- 案件別利益 -----

    def project_status(self, project: Project, current_month: int) -> str:
        """案件のステータス"""
        if current_month >= project.payment_month:
            return "入金済"
        if current_month >= project.invoice_month:
            return "請求済"
        if current_month >= project.contract_month:
            return "契約済"
        return "未契約"

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
        return sum(int(s.hours * s.hourly_rate) for s in project.staff)

    def net_profit(self, project: Project) -> int:
        """案件の純利益 (粗利 - 人件費)"""
        return self.gross_profit(project) - self.labor_cost(project)

    def calc_project_profits(
        self,
        projects: Sequence[Project],
        current_month: int,
    ) -> list[ProjectProfit]:
        """全案件の利益を一括計算"""
        results: list[ProjectProfit] = []
        for p in projects:
            gp = self.gross_profit(p)
            gm = self.gross_margin(p)
            lc = self.labor_cost(p)
            results.append(ProjectProfit(
                project_id=p.id,
                project_name=p.project_name,
                revenue=p.revenue,
                cost=p.cost,
                gross_profit=gp,
                gross_margin=gm,
                labor_cost=lc,
                net_profit=gp - lc,
                status=self.project_status(p, current_month),
            ))
        return results

    # ----- 社員別利益 -----

    def calc_staff_profit(
        self,
        staff: Staff,
        projects: Sequence[Project],
        current_month: int,
    ) -> StaffProfit:
        """1社員の利益貢献を計算"""
        total_hours = 0.0
        total_labor = 0
        assigned_rev = 0
        assigned_gp = 0
        project_names: list[str] = []

        for p in projects:
            if current_month < p.contract_month:
                continue
            for sa in p.staff:
                if sa.staff_id == staff.id or sa.name == staff.short_name:
                    total_hours += sa.hours
                    total_labor += int(sa.hours * sa.hourly_rate)
                    assigned_rev += p.revenue
                    assigned_gp += self.gross_profit(p)
                    project_names.append(p.project_name)
                    break

        return StaffProfit(
            staff_id=staff.id,
            name=staff.full_name,
            monthly_salary=staff.monthly_salary,
            total_hours=total_hours,
            total_labor_cost=total_labor,
            assigned_revenue=assigned_rev,
            assigned_profit=assigned_gp,
            project_count=len(project_names),
            projects=project_names,
        )

    def calc_all_staff_profits(
        self,
        staff_list: Sequence[Staff],
        projects: Sequence[Project],
        current_month: int,
    ) -> list[StaffProfit]:
        """全社員の利益貢献を計算"""
        return [self.calc_staff_profit(s, projects, current_month) for s in staff_list]

    # ----- カテゴリ別（商品別）利益 -----

    def calc_category_profits(
        self,
        projects: Sequence[Project],
    ) -> list[CategoryProfit]:
        """カテゴリ（商品種別）ごとの利益を計算"""
        by_cat: dict[str, dict] = {}
        for p in projects:
            cat = p.category or "未分類"
            if cat not in by_cat:
                by_cat[cat] = {"revenue": 0, "cost": 0, "count": 0}
            by_cat[cat]["revenue"] += p.revenue
            by_cat[cat]["cost"] += p.cost
            by_cat[cat]["count"] += 1

        results: list[CategoryProfit] = []
        for cat, data in sorted(by_cat.items()):
            rev = data["revenue"]
            cost = data["cost"]
            gp = rev - cost
            results.append(CategoryProfit(
                category=cat,
                revenue=rev,
                cost=cost,
                gross_profit=gp,
                gross_margin=gp / rev if rev else 0.0,
                count=data["count"],
            ))
        return results

    # ----- 月別利益推移 -----

    def calc_monthly_profit(
        self,
        projects: Sequence[Project],
    ) -> list[dict]:
        """月別の売上・原価・粗利を計算 (12ヶ月分)"""
        months: list[dict] = []
        for mi in range(12):
            rev = sum(p.revenue for p in projects if p.contract_month == mi)
            cost = sum(p.cost for p in projects if p.contract_month == mi)
            fixed = self.config.fixed_cost_monthly
            gross = rev - cost - fixed
            tax = max(0, int(gross * self.config.tax_rate)) if gross > 0 else 0
            months.append({
                "month_index": mi,
                "month_label": self.config.fiscal_months[mi],
                "revenue": rev,
                "cost": cost,
                "fixed_cost": fixed,
                "tax": tax,
                "profit": gross - tax,
                "project_count": sum(1 for p in projects if p.contract_month == mi),
            })
        return months

    # ----- KPI -----

    def achievement_rate(self, projects: Sequence[Project], current_month: int) -> float:
        """年間目標達成率"""
        contracted = sum(p.revenue for p in projects if current_month >= p.contract_month)
        if self.config.annual_target == 0:
            return 0.0
        return contracted / self.config.annual_target

    def working_capital_gap(self, result: ThreeViewResult) -> int:
        """運転資金ギャップ (未来利益 - CF利益)"""
        return result.future.profit - result.cash.profit

    def breakeven_revenue(self) -> int:
        """損益分岐点売上高 (年間)"""
        annual_fixed = self.config.fixed_cost_monthly * 12
        if self.config.target_margin <= 0:
            return 0
        return int(annual_fixed / self.config.target_margin)

    # ----- サマリ -----

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
            "breakeven": self.breakeven_revenue(),
        }
