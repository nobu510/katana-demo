"""
案件進捗エンジン
案件のステータス管理・進捗計算・工数管理・予算管理・ガントチャートデータ生成。

採番: P001-C001
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Sequence


# =====================================================================
# データ型
# =====================================================================

class ProjectStatus(str, Enum):
    """案件ステータス"""
    PROSPECT = "見込"
    CONTRACTED = "契約済"
    IN_PROGRESS = "進行中"
    INVOICED = "請求済"
    COLLECTED = "入金済"
    COMPLETED = "完了"
    ON_HOLD = "保留"
    CANCELLED = "中止"


@dataclass
class TaskItem:
    """案件内のタスク"""
    id: str                    # タスク連番
    name: str
    assignee_id: str = ""      # S001-C001
    assignee_name: str = ""
    planned_hours: float = 0.0
    actual_hours: float = 0.0
    start_date: date | None = None
    end_date: date | None = None
    completed: bool = False
    progress: int = 0          # 0-100


@dataclass
class WorkLog:
    """工数ログ"""
    staff_id: str              # S001-C001
    staff_name: str
    project_id: str            # P001-C001
    work_date: date
    hours: float
    description: str = ""
    task_id: str = ""


@dataclass
class ProjectData:
    """案件データ"""
    id: str                    # P001-C001
    company_id: str
    name: str                  # 案件名
    client_name: str = ""
    status: ProjectStatus = ProjectStatus.PROSPECT
    # 期間
    start_date: date | None = None
    end_date: date | None = None
    deadline: date | None = None
    # 金額
    budget_revenue: int = 0    # 予算売上
    budget_cost: int = 0       # 予算原価
    actual_revenue: int = 0    # 実績売上
    actual_cost: int = 0       # 実績原価
    # タスク・工数
    tasks: list[TaskItem] = field(default_factory=list)
    work_logs: list[WorkLog] = field(default_factory=list)
    # メタ
    category: str = ""
    tags: list[str] = field(default_factory=list)
    memo: str = ""


# =====================================================================
# 計算結果
# =====================================================================

@dataclass
class ProjectProgress:
    """案件進捗結果"""
    project_id: str
    name: str
    status: str
    task_progress: float       # タスク完了率 (0.0-1.0)
    hour_progress: float       # 工数消化率
    budget_progress: float     # 予算消化率
    planned_hours: float
    actual_hours: float
    remaining_hours: float
    days_until_deadline: int | None
    is_over_budget: bool
    is_overdue: bool


@dataclass
class BudgetVsActual:
    """予算vs実績"""
    budget_revenue: int
    actual_revenue: int
    revenue_variance: int
    budget_cost: int
    actual_cost: int
    cost_variance: int
    budget_profit: int
    actual_profit: int
    profit_variance: int


@dataclass
class GanttItem:
    """ガントチャート用データ"""
    project_id: str
    project_name: str
    task_id: str
    task_name: str
    assignee: str
    start_date: str            # ISO format
    end_date: str
    progress: int
    status: str


# =====================================================================
# 案件進捗エンジン
# =====================================================================

class ProjectEngine:
    """案件進捗管理エンジン"""

    # ----- ステータス遷移 -----

    VALID_TRANSITIONS: dict[ProjectStatus, list[ProjectStatus]] = {
        ProjectStatus.PROSPECT: [ProjectStatus.CONTRACTED, ProjectStatus.CANCELLED],
        ProjectStatus.CONTRACTED: [ProjectStatus.IN_PROGRESS, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED],
        ProjectStatus.IN_PROGRESS: [ProjectStatus.INVOICED, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED],
        ProjectStatus.INVOICED: [ProjectStatus.COLLECTED, ProjectStatus.IN_PROGRESS],
        ProjectStatus.COLLECTED: [ProjectStatus.COMPLETED],
        ProjectStatus.ON_HOLD: [ProjectStatus.IN_PROGRESS, ProjectStatus.CANCELLED],
        ProjectStatus.COMPLETED: [],
        ProjectStatus.CANCELLED: [],
    }

    @staticmethod
    def transition(project: ProjectData, new_status: ProjectStatus) -> tuple[bool, str]:
        """ステータス遷移（バリデーション付き）"""
        allowed = ProjectEngine.VALID_TRANSITIONS.get(project.status, [])
        if new_status not in allowed:
            return False, f"{project.status.value} → {new_status.value} は許可されていません"
        project.status = new_status
        return True, ""

    # ----- 進捗計算 -----

    @staticmethod
    def calc_progress(project: ProjectData, as_of: date | None = None) -> ProjectProgress:
        """案件の進捗率を計算"""
        today = as_of or date.today()

        # タスク完了率
        total_tasks = len(project.tasks)
        completed_tasks = sum(1 for t in project.tasks if t.completed)
        task_progress = completed_tasks / total_tasks if total_tasks else 0.0

        # 工数
        planned_hours = sum(t.planned_hours for t in project.tasks)
        actual_hours = sum(w.hours for w in project.work_logs)
        hour_progress = actual_hours / planned_hours if planned_hours else 0.0
        remaining = max(0, planned_hours - actual_hours)

        # 予算消化率
        budget_progress = project.actual_cost / project.budget_cost if project.budget_cost else 0.0

        # 期限
        days_left = None
        is_overdue = False
        if project.deadline:
            days_left = (project.deadline - today).days
            is_overdue = days_left < 0

        return ProjectProgress(
            project_id=project.id,
            name=project.name,
            status=project.status.value,
            task_progress=task_progress,
            hour_progress=hour_progress,
            budget_progress=budget_progress,
            planned_hours=planned_hours,
            actual_hours=actual_hours,
            remaining_hours=remaining,
            days_until_deadline=days_left,
            is_over_budget=project.actual_cost > project.budget_cost,
            is_overdue=is_overdue,
        )

    # ----- 工数管理 -----

    @staticmethod
    def add_work_log(
        project: ProjectData,
        staff_id: str,
        staff_name: str,
        hours: float,
        work_date: date | None = None,
        description: str = "",
        task_id: str = "",
    ) -> WorkLog:
        """工数を記録"""
        log = WorkLog(
            staff_id=staff_id,
            staff_name=staff_name,
            project_id=project.id,
            work_date=work_date or date.today(),
            hours=hours,
            description=description,
            task_id=task_id,
        )
        project.work_logs.append(log)

        # タスクの実績時間を更新
        if task_id:
            for task in project.tasks:
                if task.id == task_id:
                    task.actual_hours += hours
                    break

        return log

    @staticmethod
    def staff_hours_on_project(project: ProjectData, staff_id: str) -> float:
        """社員の案件別工数"""
        return sum(w.hours for w in project.work_logs if w.staff_id == staff_id)

    @staticmethod
    def hours_by_staff(project: ProjectData) -> list[dict]:
        """案件の社員別工数集計"""
        by_staff: dict[str, dict] = {}
        for w in project.work_logs:
            if w.staff_id not in by_staff:
                by_staff[w.staff_id] = {"name": w.staff_name, "hours": 0.0}
            by_staff[w.staff_id]["hours"] += w.hours
        return [
            {"staff_id": sid, "name": d["name"], "hours": d["hours"]}
            for sid, d in sorted(by_staff.items())
        ]

    @staticmethod
    def hours_by_date(project: ProjectData) -> list[dict]:
        """日別工数集計"""
        by_date: dict[str, float] = {}
        for w in project.work_logs:
            key = w.work_date.isoformat()
            by_date[key] = by_date.get(key, 0.0) + w.hours
        return [{"date": d, "hours": h} for d, h in sorted(by_date.items())]

    # ----- 予算vs実績 -----

    @staticmethod
    def budget_vs_actual(project: ProjectData) -> BudgetVsActual:
        """予算vs実績"""
        bp = project.budget_revenue - project.budget_cost
        ap = project.actual_revenue - project.actual_cost
        return BudgetVsActual(
            budget_revenue=project.budget_revenue,
            actual_revenue=project.actual_revenue,
            revenue_variance=project.actual_revenue - project.budget_revenue,
            budget_cost=project.budget_cost,
            actual_cost=project.actual_cost,
            cost_variance=project.actual_cost - project.budget_cost,
            budget_profit=bp,
            actual_profit=ap,
            profit_variance=ap - bp,
        )

    # ----- ガントチャート -----

    @staticmethod
    def gantt_data(projects: Sequence[ProjectData]) -> list[GanttItem]:
        """ガントチャート用データを生成"""
        items: list[GanttItem] = []
        for p in projects:
            if p.status in (ProjectStatus.CANCELLED, ProjectStatus.COMPLETED):
                continue
            for task in p.tasks:
                start = task.start_date or p.start_date or date.today()
                end = task.end_date or p.end_date or (start + timedelta(days=30))
                items.append(GanttItem(
                    project_id=p.id,
                    project_name=p.name,
                    task_id=task.id,
                    task_name=task.name,
                    assignee=task.assignee_name or task.assignee_id,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    progress=task.progress,
                    status="完了" if task.completed else "進行中",
                ))
        return items

    # ----- 一括集計 -----

    @staticmethod
    def portfolio_summary(
        projects: Sequence[ProjectData],
        as_of: date | None = None,
    ) -> dict:
        """全案件のポートフォリオサマリ"""
        active = [p for p in projects if p.status not in (ProjectStatus.CANCELLED,)]

        by_status: dict[str, int] = {}
        total_budget_rev = 0
        total_actual_rev = 0
        total_budget_cost = 0
        total_actual_cost = 0
        overdue_count = 0
        over_budget_count = 0

        for p in active:
            status_label = p.status.value
            by_status[status_label] = by_status.get(status_label, 0) + 1
            total_budget_rev += p.budget_revenue
            total_actual_rev += p.actual_revenue
            total_budget_cost += p.budget_cost
            total_actual_cost += p.actual_cost

            progress = ProjectEngine.calc_progress(p, as_of)
            if progress.is_overdue:
                overdue_count += 1
            if progress.is_over_budget:
                over_budget_count += 1

        return {
            "total_projects": len(active),
            "by_status": by_status,
            "total_budget_revenue": total_budget_rev,
            "total_actual_revenue": total_actual_rev,
            "total_budget_cost": total_budget_cost,
            "total_actual_cost": total_actual_cost,
            "total_budget_profit": total_budget_rev - total_budget_cost,
            "total_actual_profit": total_actual_rev - total_actual_cost,
            "overdue_count": overdue_count,
            "over_budget_count": over_budget_count,
        }
