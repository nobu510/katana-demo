"""
人事労務エンジン
社員マスタ・給与計算・社会保険料・年末調整・有給休暇・36協定チェック。

採番: S001-C001
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Sequence

from .numbering_engine import NumberingState, generate_staff_id


# =====================================================================
# データ型
# =====================================================================

class EmploymentType(str, Enum):
    """雇用形態"""
    FULL_TIME = "正社員"
    PART_TIME = "パート"
    CONTRACT = "契約社員"
    DIRECTOR = "役員"
    INTERN = "インターン"


class EmployeeStatus(str, Enum):
    """社員ステータス"""
    ACTIVE = "在籍"
    ON_LEAVE = "休職"
    RETIRED = "退職"


@dataclass
class Employee:
    """社員マスタ"""
    id: str                    # S001-C001
    company_id: str
    name: str
    name_kana: str = ""
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    hire_date: date = field(default_factory=date.today)
    retire_date: date | None = None
    department: str = ""
    position: str = ""         # 役職
    # 給与
    base_salary: int = 0       # 基本給 (月額)
    hourly_rate: int = 0       # 時給 (パート用)
    commute_allowance: int = 0 # 通勤手当
    housing_allowance: int = 0 # 住宅手当
    position_allowance: int = 0  # 役職手当
    # 社会保険
    health_insurance_grade: int = 0   # 健康保険等級
    pension_grade: int = 0            # 厚生年金等級
    # 扶養
    dependents: int = 0        # 扶養親族数
    # 有給
    paid_leave_days: float = 0.0   # 有給残日数
    paid_leave_granted: float = 0.0  # 今年度付与日数


@dataclass
class Transfer:
    """異動記録"""
    employee_id: str
    transfer_date: date
    from_department: str
    to_department: str
    from_position: str = ""
    to_position: str = ""
    memo: str = ""


# =====================================================================
# 給与計算
# =====================================================================

@dataclass
class OvertimeDetail:
    """残業内訳"""
    normal_hours: float = 0.0     # 法定内残業
    over_hours: float = 0.0       # 法定外残業 (×1.25)
    late_night_hours: float = 0.0  # 深夜残業 (×1.5)
    holiday_hours: float = 0.0    # 休日残業 (×1.35)


@dataclass
class PaySlip:
    """給与明細"""
    employee_id: str
    year: int
    month: int
    # 支給
    base_salary: int = 0
    overtime_pay: int = 0
    commute_allowance: int = 0
    housing_allowance: int = 0
    position_allowance: int = 0
    other_allowance: int = 0
    gross_pay: int = 0             # 支給総額
    # 控除
    health_insurance: int = 0      # 健康保険料
    pension: int = 0               # 厚生年金保険料
    employment_insurance: int = 0  # 雇用保険料
    social_insurance_total: int = 0  # 社保合計
    income_tax: int = 0            # 所得税 (源泉徴収)
    resident_tax: int = 0          # 住民税
    other_deduction: int = 0
    total_deduction: int = 0       # 控除合計
    # 差引
    net_pay: int = 0               # 差引支給額
    # 明細
    overtime: OvertimeDetail = field(default_factory=OvertimeDetail)
    working_days: int = 0
    working_hours: float = 0.0


# =====================================================================
# 社会保険料率テーブル (2024年度概算)
# =====================================================================

HEALTH_INSURANCE_RATE = 0.10       # 健康保険料率 (労使折半前、協会けんぽ東京)
PENSION_RATE = 0.183               # 厚生年金保険料率 (労使折半前)
EMPLOYMENT_INSURANCE_RATE_EMPLOYEE = 0.006  # 雇用保険料率 (被保険者負担、一般)
EMPLOYMENT_INSURANCE_RATE_EMPLOYER = 0.0095 # 雇用保険料率 (事業主負担)
WORKERS_COMP_RATE = 0.003          # 労災保険料率 (事業主全額、事務職)

# 残業割増率
OVERTIME_RATE_NORMAL = 1.25
OVERTIME_RATE_LATE_NIGHT = 1.50
OVERTIME_RATE_HOLIDAY = 1.35
OVERTIME_RATE_OVER60 = 1.50        # 月60時間超


# =====================================================================
# 人事労務エンジン
# =====================================================================

class HREngine:
    """人事労務エンジン"""

    def __init__(self, company_id: str = ""):
        self.company_id = company_id
        self._numbering_state = NumberingState()

    # ----- 社員マスタ -----

    def create_employee(
        self,
        name: str,
        base_salary: int = 0,
        employment_type: EmploymentType = EmploymentType.FULL_TIME,
        hire_date: date | None = None,
        department: str = "",
        hourly_rate: int = 0,
        **kwargs,
    ) -> Employee:
        """社員を採番付きで登録"""
        nid, self._numbering_state = generate_staff_id(
            self._numbering_state, self.company_id
        )
        emp = Employee(
            id=nid.id,
            company_id=self.company_id,
            name=name,
            employment_type=employment_type,
            hire_date=hire_date or date.today(),
            department=department,
            base_salary=base_salary,
            hourly_rate=hourly_rate or (base_salary // 160 if base_salary else 0),
        )
        for k, v in kwargs.items():
            if hasattr(emp, k):
                setattr(emp, k, v)
        return emp

    @staticmethod
    def retire_employee(employee: Employee, retire_date: date | None = None) -> Employee:
        """退職処理"""
        employee.status = EmployeeStatus.RETIRED
        employee.retire_date = retire_date or date.today()
        return employee

    @staticmethod
    def transfer(
        employee: Employee,
        to_department: str,
        to_position: str = "",
        transfer_date: date | None = None,
    ) -> Transfer:
        """異動処理"""
        t = Transfer(
            employee_id=employee.id,
            transfer_date=transfer_date or date.today(),
            from_department=employee.department,
            to_department=to_department,
            from_position=employee.position,
            to_position=to_position,
        )
        employee.department = to_department
        if to_position:
            employee.position = to_position
        return t

    # ----- 社会保険料計算 -----

    @staticmethod
    def calc_social_insurance(
        monthly_salary: int,
        include_employer: bool = False,
    ) -> dict:
        """
        社会保険料を計算 (標準報酬月額ベースの簡易計算)
        """
        # 健康保険 (労使折半)
        health_full = int(monthly_salary * HEALTH_INSURANCE_RATE)
        health_employee = health_full // 2
        health_employer = health_full - health_employee

        # 厚生年金 (労使折半)
        pension_full = int(monthly_salary * PENSION_RATE)
        pension_employee = pension_full // 2
        pension_employer = pension_full - pension_employee

        # 雇用保険
        emp_insurance = int(monthly_salary * EMPLOYMENT_INSURANCE_RATE_EMPLOYEE)
        employer_insurance = int(monthly_salary * EMPLOYMENT_INSURANCE_RATE_EMPLOYER)

        # 労災 (事業主のみ)
        workers_comp = int(monthly_salary * WORKERS_COMP_RATE)

        result = {
            "health_insurance": health_employee,
            "pension": pension_employee,
            "employment_insurance": emp_insurance,
            "employee_total": health_employee + pension_employee + emp_insurance,
        }

        if include_employer:
            result["employer_health"] = health_employer
            result["employer_pension"] = pension_employer
            result["employer_employment"] = employer_insurance
            result["workers_comp"] = workers_comp
            result["employer_total"] = (
                health_employer + pension_employer + employer_insurance + workers_comp
            )

        return result

    # ----- 給与計算 -----

    @staticmethod
    def calc_payslip(
        employee: Employee,
        year: int,
        month: int,
        working_days: int = 20,
        working_hours: float = 160.0,
        overtime: OvertimeDetail | None = None,
        resident_tax: int = 0,
        other_allowance: int = 0,
        other_deduction: int = 0,
    ) -> PaySlip:
        """月次給与を計算"""
        ot = overtime or OvertimeDetail()

        # 時給計算
        if employee.employment_type == EmploymentType.PART_TIME:
            hourly = employee.hourly_rate
            base = int(hourly * working_hours)
        else:
            base = employee.base_salary
            hourly = base // 160 if base else 0

        # 残業代
        ot_normal = int(hourly * OVERTIME_RATE_NORMAL * ot.normal_hours)
        ot_late = int(hourly * OVERTIME_RATE_LATE_NIGHT * ot.late_night_hours)
        ot_holiday = int(hourly * OVERTIME_RATE_HOLIDAY * ot.holiday_hours)
        # 60時間超
        over_60 = max(0, ot.over_hours - 60)
        ot_over60 = int(hourly * OVERTIME_RATE_OVER60 * over_60)
        ot_regular = int(hourly * OVERTIME_RATE_NORMAL * min(ot.over_hours, 60))
        overtime_pay = ot_normal + ot_late + ot_holiday + ot_regular + ot_over60

        # 支給総額
        gross = (base + overtime_pay + employee.commute_allowance
                 + employee.housing_allowance + employee.position_allowance
                 + other_allowance)

        # 社保計算 (通勤手当を除いた標準報酬月額で計算)
        si_base = gross - employee.commute_allowance
        si = HREngine.calc_social_insurance(si_base)

        # 源泉徴収 (簡易計算: 社保控除後の課税対象額)
        taxable = gross - si["employee_total"]
        # 扶養控除
        dependent_deduction = employee.dependents * 31_667
        taxable = max(0, taxable - dependent_deduction)
        if taxable <= 88_000:
            income_tax = 0
        elif taxable <= 162_000:
            income_tax = int(taxable * 0.05)
        elif taxable <= 300_000:
            income_tax = int(taxable * 0.10)
        else:
            income_tax = int(taxable * 0.20)

        total_deduction = (si["employee_total"] + income_tax
                          + resident_tax + other_deduction)

        return PaySlip(
            employee_id=employee.id,
            year=year,
            month=month,
            base_salary=base,
            overtime_pay=overtime_pay,
            commute_allowance=employee.commute_allowance,
            housing_allowance=employee.housing_allowance,
            position_allowance=employee.position_allowance,
            other_allowance=other_allowance,
            gross_pay=gross,
            health_insurance=si["health_insurance"],
            pension=si["pension"],
            employment_insurance=si["employment_insurance"],
            social_insurance_total=si["employee_total"],
            income_tax=income_tax,
            resident_tax=resident_tax,
            other_deduction=other_deduction,
            total_deduction=total_deduction,
            net_pay=gross - total_deduction,
            overtime=ot,
            working_days=working_days,
            working_hours=working_hours,
        )

    # ----- 年末調整 (簡易) -----

    @staticmethod
    def year_end_adjustment(
        payslips: Sequence[PaySlip],
        life_insurance_deduction: int = 0,
        earthquake_insurance_deduction: int = 0,
        mortgage_deduction: int = 0,
        medical_expense_deduction: int = 0,
    ) -> dict:
        """
        年末調整 (簡易計算)
        年間給与所得から所得税を再計算し、過不足を算出
        """
        annual_gross = sum(p.gross_pay for p in payslips)
        annual_si = sum(p.social_insurance_total for p in payslips)
        annual_tax_withheld = sum(p.income_tax for p in payslips)

        # 給与所得控除 (2024年)
        if annual_gross <= 1_625_000:
            employment_deduction = 550_000
        elif annual_gross <= 1_800_000:
            employment_deduction = int(annual_gross * 0.4) - 100_000
        elif annual_gross <= 3_600_000:
            employment_deduction = int(annual_gross * 0.3) + 80_000
        elif annual_gross <= 6_600_000:
            employment_deduction = int(annual_gross * 0.2) + 440_000
        elif annual_gross <= 8_500_000:
            employment_deduction = int(annual_gross * 0.1) + 1_100_000
        else:
            employment_deduction = 1_950_000

        # 所得控除
        basic_deduction = 480_000   # 基礎控除
        total_deductions = (
            employment_deduction + annual_si + basic_deduction
            + life_insurance_deduction + earthquake_insurance_deduction
            + medical_expense_deduction
        )

        taxable_income = max(0, annual_gross - total_deductions)

        # 所得税率テーブル
        if taxable_income <= 1_950_000:
            tax = int(taxable_income * 0.05)
        elif taxable_income <= 3_300_000:
            tax = int(taxable_income * 0.10) - 97_500
        elif taxable_income <= 6_950_000:
            tax = int(taxable_income * 0.20) - 427_500
        elif taxable_income <= 9_000_000:
            tax = int(taxable_income * 0.23) - 636_000
        elif taxable_income <= 18_000_000:
            tax = int(taxable_income * 0.33) - 1_536_000
        else:
            tax = int(taxable_income * 0.40) - 2_796_000

        # 復興特別所得税 2.1%
        tax = int(tax * 1.021)

        # 住宅ローン控除
        tax = max(0, tax - mortgage_deduction)

        # 過不足
        difference = annual_tax_withheld - tax

        return {
            "annual_gross": annual_gross,
            "employment_deduction": employment_deduction,
            "social_insurance": annual_si,
            "total_deductions": total_deductions,
            "taxable_income": taxable_income,
            "annual_tax": tax,
            "withheld_total": annual_tax_withheld,
            "refund": difference if difference > 0 else 0,
            "additional": -difference if difference < 0 else 0,
        }

    # ----- 有給休暇 -----

    @staticmethod
    def calc_paid_leave_grant(
        hire_date: date,
        as_of: date | None = None,
    ) -> float:
        """入社日から有給付与日数を計算"""
        today = as_of or date.today()
        years = (today - hire_date).days / 365.25

        # 勤続年数別の法定付与日数
        if years < 0.5:
            return 0
        elif years < 1.5:
            return 10
        elif years < 2.5:
            return 11
        elif years < 3.5:
            return 12
        elif years < 4.5:
            return 14
        elif years < 5.5:
            return 16
        elif years < 6.5:
            return 18
        else:
            return 20

    @staticmethod
    def use_paid_leave(employee: Employee, days: float) -> tuple[bool, str]:
        """有給休暇を消化"""
        if days > employee.paid_leave_days:
            return False, f"残日数不足: 残{employee.paid_leave_days}日 < 申請{days}日"
        employee.paid_leave_days -= days
        return True, ""

    # ----- 36協定チェック -----

    @staticmethod
    def check_overtime_limit(
        overtime: OvertimeDetail,
        monthly_overtimes: Sequence[OvertimeDetail] | None = None,
    ) -> list[str]:
        """
        36協定の残業時間チェック

        上限:
          - 月45時間
          - 年360時間
          - 特別条項: 月100時間未満 (休日含む)
          - 特別条項: 2-6ヶ月平均80時間以内
        """
        warnings: list[str] = []
        total_month = (overtime.normal_hours + overtime.over_hours
                       + overtime.late_night_hours + overtime.holiday_hours)

        # 月45時間
        if total_month > 45:
            warnings.append(f"月45時間超: {total_month:.1f}時間 (特別条項要)")

        # 月100時間未満
        if total_month >= 100:
            warnings.append(f"月100時間以上: {total_month:.1f}時間 (違法)")

        # 年間チェック
        if monthly_overtimes:
            all_months = list(monthly_overtimes) + [overtime]

            # 年360時間
            annual_total = sum(
                m.normal_hours + m.over_hours + m.late_night_hours + m.holiday_hours
                for m in all_months
            )
            if annual_total > 360:
                warnings.append(f"年360時間超: {annual_total:.1f}時間")

            # 2-6ヶ月平均80時間
            for span in range(2, min(7, len(all_months) + 1)):
                recent = all_months[-span:]
                avg = sum(
                    m.normal_hours + m.over_hours + m.late_night_hours + m.holiday_hours
                    for m in recent
                ) / span
                if avg > 80:
                    warnings.append(f"直近{span}ヶ月平均80時間超: {avg:.1f}時間")
                    break

            # 月45時間超が年6回まで
            over_45_count = sum(
                1 for m in all_months
                if (m.normal_hours + m.over_hours + m.late_night_hours + m.holiday_hours) > 45
            )
            if over_45_count > 6:
                warnings.append(f"月45時間超が年7回以上: {over_45_count}回")

        return warnings

    # ----- 一括集計 -----

    @staticmethod
    def headcount(
        employees: Sequence[Employee],
        as_of: date | None = None,
    ) -> dict:
        """在籍人数集計"""
        today = as_of or date.today()
        active = [e for e in employees if e.status == EmployeeStatus.ACTIVE]

        by_type: dict[str, int] = {}
        by_dept: dict[str, int] = {}
        for e in active:
            by_type[e.employment_type.value] = by_type.get(e.employment_type.value, 0) + 1
            dept = e.department or "未配属"
            by_dept[dept] = by_dept.get(dept, 0) + 1

        return {
            "total": len(active),
            "by_type": by_type,
            "by_department": by_dept,
        }

    @staticmethod
    def monthly_labor_cost(payslips: Sequence[PaySlip]) -> int:
        """月次人件費合計 (支給総額)"""
        return sum(p.gross_pay for p in payslips)
