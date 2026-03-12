"""
勤怠管理エンジン
チャットで「出勤」「退勤」→ 勤怠記録 → 残業計算 → 給与連携。

採番: AT001-S001-C001 (勤怠-社員紐づけ)
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from enum import Enum
from typing import Sequence

from .numbering_engine import NumberingState, generate_attendance_id
from .hr_engine import OvertimeDetail


# =====================================================================
# データ型
# =====================================================================

class AttendanceType(str, Enum):
    """勤怠種別"""
    WORK = "出勤"
    HOLIDAY = "休日"
    PAID_LEAVE = "有給"
    HALF_LEAVE = "半休"
    SICK_LEAVE = "病欠"
    SPECIAL_LEAVE = "特別休暇"
    ABSENT = "欠勤"


@dataclass
class AttendanceRecord:
    """勤怠レコード (1日1レコード)"""
    id: str                    # AT001-S001-C001
    staff_id: str              # S001-C001
    work_date: date
    attendance_type: AttendanceType = AttendanceType.WORK
    clock_in: time | None = None
    clock_out: time | None = None
    break_minutes: int = 60    # 休憩時間 (分)
    actual_hours: float = 0.0  # 実労働時間
    overtime_hours: float = 0.0  # 残業時間
    late_night_hours: float = 0.0  # 深夜時間 (22:00-5:00)
    is_holiday: bool = False   # 休日出勤
    memo: str = ""
    # 業務報告からの自動記録
    project_hours: list[ProjectHourEntry] = field(default_factory=list)


@dataclass
class ProjectHourEntry:
    """案件別工数 (1勤怠レコード内)"""
    project_id: str            # P001-C001
    project_name: str
    hours: float
    description: str = ""


@dataclass
class ShiftPattern:
    """シフトパターン"""
    name: str                  # "日勤", "早番", "遅番" etc.
    start_time: time
    end_time: time
    break_minutes: int = 60


# デフォルトシフト
DEFAULT_SHIFT = ShiftPattern("日勤", time(9, 0), time(18, 0), 60)

# 法定労働時間
LEGAL_DAILY_HOURS = 8.0
LEGAL_WEEKLY_HOURS = 40.0
LATE_NIGHT_START = time(22, 0)
LATE_NIGHT_END = time(5, 0)


# =====================================================================
# 勤怠管理エンジン
# =====================================================================

class AttendanceEngine:
    """勤怠管理エンジン"""

    def __init__(self, company_id: str = ""):
        self.company_id = company_id
        self._numbering_state = NumberingState()

    # ----- チャットから勤怠記録 -----

    def clock_in(
        self,
        staff_id: str,
        work_date: date | None = None,
        clock_time: time | None = None,
    ) -> AttendanceRecord:
        """出勤打刻 (チャットで「出勤」)"""
        nid, self._numbering_state = generate_attendance_id(
            self._numbering_state, staff_id
        )
        dt = work_date or date.today()
        ct = clock_time or datetime.now().time().replace(second=0, microsecond=0)

        return AttendanceRecord(
            id=nid.id,
            staff_id=staff_id,
            work_date=dt,
            clock_in=ct,
        )

    @staticmethod
    def clock_out(
        record: AttendanceRecord,
        clock_time: time | None = None,
        shift: ShiftPattern | None = None,
    ) -> AttendanceRecord:
        """退勤打刻 (チャットで「退勤」)"""
        ct = clock_time or datetime.now().time().replace(second=0, microsecond=0)
        record.clock_out = ct

        # 労働時間を自動計算
        if record.clock_in and record.clock_out:
            record.actual_hours, record.overtime_hours, record.late_night_hours = (
                AttendanceEngine._calc_hours(
                    record.clock_in, record.clock_out,
                    record.break_minutes, record.is_holiday, shift,
                )
            )
        return record

    # ----- 業務報告からの自動記録 -----

    @staticmethod
    def add_project_hours(
        record: AttendanceRecord,
        project_id: str,
        project_name: str,
        hours: float,
        description: str = "",
    ) -> AttendanceRecord:
        """
        チャットで「A案件5時間」→ 勤怠に工数を追加。
        勤怠 → 工数 → 原価 → 利益 → 会計 の自動連携の起点。
        """
        record.project_hours.append(ProjectHourEntry(
            project_id=project_id,
            project_name=project_name,
            hours=hours,
            description=description,
        ))
        return record

    @staticmethod
    def parse_work_report(text: str) -> list[dict]:
        """
        チャットの業務報告をパース。
        例: "A案件5時間 B案件3時間" → [{project: "A案件", hours: 5}, ...]
        """
        import re
        results: list[dict] = []
        # パターン: 案件名 + 数字 + 時間
        pattern = r'([^\s\d]+?)[案件]?\s*(\d+(?:\.\d+)?)\s*[時h]間?'
        for m in re.finditer(pattern, text):
            results.append({
                "project_name": m.group(1),
                "hours": float(m.group(2)),
            })
        # フォールバック: "5時間" だけのパターン
        if not results:
            m = re.search(r'(\d+(?:\.\d+)?)\s*[時h]間?', text)
            if m:
                results.append({"project_name": "", "hours": float(m.group(1))})
        return results

    # ----- 労働時間計算 -----

    @staticmethod
    def _calc_hours(
        clock_in: time,
        clock_out: time,
        break_minutes: int,
        is_holiday: bool,
        shift: ShiftPattern | None = None,
    ) -> tuple[float, float, float]:
        """
        (実労働時間, 残業時間, 深夜時間) を計算

        Returns:
            (actual_hours, overtime_hours, late_night_hours)
        """
        # time → 分に変換
        in_min = clock_in.hour * 60 + clock_in.minute
        out_min = clock_out.hour * 60 + clock_out.minute
        if out_min <= in_min:
            out_min += 24 * 60  # 日跨ぎ

        total_min = out_min - in_min - break_minutes
        total_hours = max(0, total_min / 60)

        # 残業 = 法定超過分
        if is_holiday:
            overtime = total_hours  # 休日はすべて残業
        else:
            overtime = max(0, total_hours - LEGAL_DAILY_HOURS)

        # 深夜時間 (22:00-5:00)
        late_start = 22 * 60   # 22:00
        late_end = 5 * 60      # 05:00 (翌日)
        late_night = 0.0

        # 22:00以降
        if out_min > late_start:
            late_from = max(in_min, late_start)
            late_to = out_min
            late_night += max(0, (late_to - late_from) / 60)

        # 翌5:00まで (日跨ぎ)
        if out_min > 24 * 60:
            late_night_next = min(out_min - 24 * 60, late_end)
            if late_night_next > 0 and in_min <= 24 * 60:
                late_night += late_night_next / 60

        # 5:00前出勤
        if in_min < late_end:
            early_to = min(clock_out.hour * 60 + clock_out.minute, late_end) if out_min < 24 * 60 else late_end
            late_night += max(0, (early_to - in_min) / 60)

        return round(total_hours, 2), round(overtime, 2), round(late_night, 2)

    # ----- 月次集計 -----

    @staticmethod
    def monthly_summary(
        records: Sequence[AttendanceRecord],
        year: int,
        month: int,
    ) -> dict:
        """月次勤怠集計"""
        month_records = [
            r for r in records
            if r.work_date.year == year and r.work_date.month == month
        ]

        work_days = sum(1 for r in month_records if r.attendance_type == AttendanceType.WORK)
        paid_leave_days = sum(
            1 for r in month_records if r.attendance_type == AttendanceType.PAID_LEAVE
        ) + sum(
            0.5 for r in month_records if r.attendance_type == AttendanceType.HALF_LEAVE
        )
        absent_days = sum(1 for r in month_records if r.attendance_type == AttendanceType.ABSENT)
        total_hours = sum(r.actual_hours for r in month_records)
        total_overtime = sum(r.overtime_hours for r in month_records)
        total_late_night = sum(r.late_night_hours for r in month_records)
        holiday_work_days = sum(1 for r in month_records if r.is_holiday and r.attendance_type == AttendanceType.WORK)
        holiday_hours = sum(r.actual_hours for r in month_records if r.is_holiday)

        return {
            "year": year,
            "month": month,
            "work_days": work_days,
            "paid_leave_days": paid_leave_days,
            "absent_days": absent_days,
            "total_hours": round(total_hours, 2),
            "total_overtime": round(total_overtime, 2),
            "total_late_night": round(total_late_night, 2),
            "holiday_work_days": holiday_work_days,
            "holiday_hours": round(holiday_hours, 2),
        }

    @staticmethod
    def to_overtime_detail(
        records: Sequence[AttendanceRecord],
        year: int,
        month: int,
    ) -> OvertimeDetail:
        """
        月次勤怠 → 給与計算用のOvertimeDetailに変換。
        勤怠→給与への自動連携。
        """
        month_records = [
            r for r in records
            if r.work_date.year == year and r.work_date.month == month
            and r.attendance_type == AttendanceType.WORK
        ]

        normal_ot = sum(r.overtime_hours for r in month_records if not r.is_holiday)
        late_night = sum(r.late_night_hours for r in month_records)
        holiday_hours = sum(r.actual_hours for r in month_records if r.is_holiday)

        return OvertimeDetail(
            normal_hours=0,  # 法定内残業 (通常はなし)
            over_hours=round(normal_ot, 2),
            late_night_hours=round(late_night, 2),
            holiday_hours=round(holiday_hours, 2),
        )

    # ----- 案件別工数集計 -----

    @staticmethod
    def project_hours_summary(
        records: Sequence[AttendanceRecord],
        year: int | None = None,
        month: int | None = None,
    ) -> list[dict]:
        """
        案件別の工数集計。
        勤怠 → 工数 → 原価計算に連携。
        """
        filtered = records
        if year:
            filtered = [r for r in filtered if r.work_date.year == year]
        if month:
            filtered = [r for r in filtered if r.work_date.month == month]

        by_project: dict[str, dict] = {}
        for r in filtered:
            for ph in r.project_hours:
                pid = ph.project_id
                if pid not in by_project:
                    by_project[pid] = {"name": ph.project_name, "hours": 0.0, "entries": 0}
                by_project[pid]["hours"] += ph.hours
                by_project[pid]["entries"] += 1

        return [
            {
                "project_id": pid,
                "project_name": d["name"],
                "total_hours": round(d["hours"], 2),
                "entry_count": d["entries"],
            }
            for pid, d in sorted(by_project.items())
        ]

    # ----- シフト管理 -----

    @staticmethod
    def generate_shift_schedule(
        staff_ids: Sequence[str],
        start_date: date,
        days: int = 7,
        shift: ShiftPattern | None = None,
        holidays: Sequence[date] | None = None,
    ) -> list[dict]:
        """シフトスケジュールを生成"""
        s = shift or DEFAULT_SHIFT
        hols = set(holidays or [])
        schedule: list[dict] = []

        for staff_id in staff_ids:
            for d in range(days):
                day = start_date + timedelta(days=d)
                is_weekend = day.weekday() >= 5
                is_hol = day in hols
                schedule.append({
                    "staff_id": staff_id,
                    "date": day.isoformat(),
                    "shift": s.name if not (is_weekend or is_hol) else "休日",
                    "start": s.start_time.isoformat() if not (is_weekend or is_hol) else None,
                    "end": s.end_time.isoformat() if not (is_weekend or is_hol) else None,
                    "is_holiday": is_weekend or is_hol,
                })

        return schedule
