"""
税金計算エンジン
法人税・消費税・地方税・源泉徴収税を計算する純粋関数群。

全関数はDB非依存。数値を受け取り、計算結果を返すだけ。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# =====================================================================
# 消費税
# =====================================================================

class TaxRate(str, Enum):
    """消費税率区分"""
    STANDARD = "標準税率"        # 10%
    REDUCED = "軽減税率"         # 8%
    EXEMPT = "非課税"            # 0%
    NON_TAXABLE = "不課税"       # 0%
    ZERO_RATED = "免税"          # 0% (輸出等)

# 消費税率テーブル
CONSUMPTION_TAX_RATES: dict[TaxRate, float] = {
    TaxRate.STANDARD: 0.10,
    TaxRate.REDUCED: 0.08,
    TaxRate.EXEMPT: 0.0,
    TaxRate.NON_TAXABLE: 0.0,
    TaxRate.ZERO_RATED: 0.0,
}

# 消費税の内訳 (国税 + 地方消費税)
CONSUMPTION_TAX_BREAKDOWN: dict[TaxRate, tuple[float, float]] = {
    TaxRate.STANDARD: (0.078, 0.022),   # 国税7.8% + 地方2.2%
    TaxRate.REDUCED: (0.063, 0.017),     # 国税6.24% + 地方1.76% (端数調整)
}


@dataclass
class ConsumptionTaxResult:
    """消費税計算結果"""
    tax_inclusive: int       # 税込金額
    tax_exclusive: int       # 税抜金額
    tax_amount: int          # 消費税額
    national_tax: int        # 国税分
    local_tax: int           # 地方消費税分
    rate: TaxRate
    rate_pct: float


def calc_consumption_tax_inclusive(amount_inclusive: int, rate: TaxRate = TaxRate.STANDARD) -> ConsumptionTaxResult:
    """税込金額から消費税を計算（内税方式）"""
    pct = CONSUMPTION_TAX_RATES[rate]
    if pct == 0.0:
        return ConsumptionTaxResult(
            tax_inclusive=amount_inclusive, tax_exclusive=amount_inclusive,
            tax_amount=0, national_tax=0, local_tax=0,
            rate=rate, rate_pct=pct,
        )
    tax_exclusive = int(amount_inclusive * 1000 / (1000 + int(pct * 1000)))
    tax_amount = amount_inclusive - tax_exclusive
    # 国税/地方按分
    breakdown = CONSUMPTION_TAX_BREAKDOWN.get(rate, (pct, 0.0))
    total_rate = breakdown[0] + breakdown[1]
    national = int(tax_amount * breakdown[0] / total_rate) if total_rate else 0
    local = tax_amount - national
    return ConsumptionTaxResult(
        tax_inclusive=amount_inclusive, tax_exclusive=tax_exclusive,
        tax_amount=tax_amount, national_tax=national, local_tax=local,
        rate=rate, rate_pct=pct,
    )


def calc_consumption_tax_exclusive(amount_exclusive: int, rate: TaxRate = TaxRate.STANDARD) -> ConsumptionTaxResult:
    """税抜金額から消費税を計算（外税方式）"""
    pct = CONSUMPTION_TAX_RATES[rate]
    tax_amount = int(amount_exclusive * pct)
    tax_inclusive = amount_exclusive + tax_amount
    breakdown = CONSUMPTION_TAX_BREAKDOWN.get(rate, (pct, 0.0))
    total_rate = breakdown[0] + breakdown[1]
    national = int(tax_amount * breakdown[0] / total_rate) if total_rate else 0
    local = tax_amount - national
    return ConsumptionTaxResult(
        tax_inclusive=tax_inclusive, tax_exclusive=amount_exclusive,
        tax_amount=tax_amount, national_tax=national, local_tax=local,
        rate=rate, rate_pct=pct,
    )


# =====================================================================
# インボイス制度対応
# =====================================================================

@dataclass
class InvoiceLineItem:
    """インボイス明細行"""
    description: str
    amount: int           # 税抜金額
    rate: TaxRate


@dataclass
class InvoiceTaxSummary:
    """インボイス税率別集計"""
    rate: TaxRate
    rate_pct: float
    taxable_amount: int   # 課税標準額 (税抜合計)
    tax_amount: int       # 消費税額


def calc_invoice_tax(items: list[InvoiceLineItem]) -> list[InvoiceTaxSummary]:
    """
    インボイス制度準拠: 税率ごとに合算してから消費税を計算（端数処理は1回）
    """
    by_rate: dict[TaxRate, int] = {}
    for item in items:
        by_rate[item.rate] = by_rate.get(item.rate, 0) + item.amount

    summaries: list[InvoiceTaxSummary] = []
    for rate, total in sorted(by_rate.items(), key=lambda x: x[0].value):
        pct = CONSUMPTION_TAX_RATES[rate]
        tax = int(total * pct)  # 税率ごとに1回だけ端数切捨て
        summaries.append(InvoiceTaxSummary(
            rate=rate, rate_pct=pct,
            taxable_amount=total, tax_amount=tax,
        ))
    return summaries


# =====================================================================
# 法人税
# =====================================================================

# 法人税率テーブル (2024年度基準)
# 普通法人: 資本金1億円以下の中小法人は軽減税率適用
@dataclass
class CorpTaxBracket:
    """法人税率区間"""
    upper_limit: int | None   # この金額まで (None=上限なし)
    rate: float


# 中小法人 (資本金1億円以下)
CORP_TAX_SME: list[CorpTaxBracket] = [
    CorpTaxBracket(upper_limit=8_000_000, rate=0.15),    # 800万円以下: 15%
    CorpTaxBracket(upper_limit=None, rate=0.232),         # 800万円超: 23.2%
]

# 大法人
CORP_TAX_LARGE: list[CorpTaxBracket] = [
    CorpTaxBracket(upper_limit=None, rate=0.232),         # 一律23.2%
]


@dataclass
class CorpTaxResult:
    """法人税計算結果"""
    taxable_income: int       # 課税所得
    corp_tax: int             # 法人税額
    effective_rate: float     # 実効税率
    brackets: list[dict]      # 税率区間ごとの内訳


def calc_corporate_tax(
    taxable_income: int,
    is_sme: bool = True,
) -> CorpTaxResult:
    """
    法人税を計算

    Args:
        taxable_income: 課税所得 (税引前利益から調整後)
        is_sme: 中小法人かどうか (資本金1億円以下)
    """
    if taxable_income <= 0:
        return CorpTaxResult(
            taxable_income=taxable_income, corp_tax=0,
            effective_rate=0.0, brackets=[],
        )

    brackets = CORP_TAX_SME if is_sme else CORP_TAX_LARGE
    total_tax = 0
    remaining = taxable_income
    details: list[dict] = []

    for bracket in brackets:
        if remaining <= 0:
            break
        if bracket.upper_limit is not None:
            taxable_in_bracket = min(remaining, bracket.upper_limit)
        else:
            taxable_in_bracket = remaining
        tax_in_bracket = int(taxable_in_bracket * bracket.rate)
        total_tax += tax_in_bracket
        remaining -= taxable_in_bracket
        details.append({
            "taxable": taxable_in_bracket,
            "rate": bracket.rate,
            "tax": tax_in_bracket,
        })

    return CorpTaxResult(
        taxable_income=taxable_income,
        corp_tax=total_tax,
        effective_rate=total_tax / taxable_income if taxable_income else 0.0,
        brackets=details,
    )


# =====================================================================
# 地方税 (法人住民税・法人事業税)
# =====================================================================

@dataclass
class LocalTaxResult:
    """地方税計算結果"""
    inhabitant_tax: int       # 法人住民税 (法人税割 + 均等割)
    inhabitant_tax_rate_portion: int   # 法人税割
    inhabitant_equalization: int       # 均等割
    enterprise_tax: int       # 法人事業税
    special_enterprise_tax: int  # 特別法人事業税
    total: int


# 法人住民税の税率
INHABITANT_TAX_RATE = 0.104       # 法人税割: 法人税額 × 10.4% (標準)
# 均等割 (資本金・従業員数で変動、ここでは最小: 資本金1千万円以下・50人以下)
EQUALIZATION_TAX_DEFAULT = 70_000  # 7万円

# 法人事業税率 (所得割、中小法人・標準税率)
ENTERPRISE_TAX_BRACKETS = [
    (4_000_000, 0.035),      # 400万以下: 3.5%
    (8_000_000, 0.053),      # 800万以下: 5.3%
    (None, 0.070),           # 800万超: 7.0%
]

# 特別法人事業税率
SPECIAL_ENTERPRISE_TAX_RATE = 0.37  # 基準法人所得割額 × 37%


def calc_local_tax(
    corp_tax_amount: int,
    taxable_income: int,
    capital: int = 10_000_000,
    employee_count: int = 10,
) -> LocalTaxResult:
    """
    地方税を計算 (法人住民税 + 法人事業税)

    Args:
        corp_tax_amount: 法人税額
        taxable_income: 課税所得
        capital: 資本金
        employee_count: 従業員数
    """
    # --- 法人住民税 ---
    rate_portion = int(corp_tax_amount * INHABITANT_TAX_RATE)
    # 均等割 (簡易: 資本金と従業員で判定)
    if capital <= 10_000_000:
        equalization = 70_000 if employee_count <= 50 else 140_000
    elif capital <= 100_000_000:
        equalization = 180_000 if employee_count <= 50 else 200_000
    elif capital <= 1_000_000_000:
        equalization = 290_000 if employee_count <= 50 else 530_000
    else:
        equalization = 410_000 if employee_count <= 50 else 3_000_000

    inhabitant = rate_portion + equalization

    # --- 法人事業税 ---
    enterprise = 0
    remaining = max(0, taxable_income)
    prev_limit = 0
    for limit, rate in ENTERPRISE_TAX_BRACKETS:
        if remaining <= 0:
            break
        if limit is not None:
            bracket_amount = min(remaining, limit - prev_limit)
            prev_limit = limit
        else:
            bracket_amount = remaining
        enterprise += int(bracket_amount * rate)
        remaining -= bracket_amount

    # --- 特別法人事業税 ---
    special_enterprise = int(enterprise * SPECIAL_ENTERPRISE_TAX_RATE)

    total = inhabitant + enterprise + special_enterprise

    return LocalTaxResult(
        inhabitant_tax=inhabitant,
        inhabitant_tax_rate_portion=rate_portion,
        inhabitant_equalization=equalization,
        enterprise_tax=enterprise,
        special_enterprise_tax=special_enterprise,
        total=total,
    )


# =====================================================================
# 源泉徴収税
# =====================================================================

class WithholdingType(str, Enum):
    """源泉徴収対象区分"""
    SALARY = "給与"
    BONUS = "賞与"
    PROFESSIONAL = "報酬"          # 弁護士・税理士等
    DIRECTORS = "役員報酬"


# 給与所得の源泉徴収税額表 (月額・甲欄、扶養0人、簡易版)
# 実際は国税庁の税額表を使うが、ここでは累進近似
# 社会保険料控除後の課税対象金額に適用
SALARY_WITHHOLDING_BRACKETS = [
    (88_000, 0.0, 0),            # 8.8万以下: 非課税
    (162_000, 0.05, 0),          # 16.2万以下: 5%
    (300_000, 0.10, 0),          # 30万以下: 10%
    (None, 0.20, 0),             # 30万超: 20%
]

# 報酬の源泉徴収
PROFESSIONAL_WITHHOLDING_RATE = 0.1021         # 100万円以下: 10.21%
PROFESSIONAL_WITHHOLDING_RATE_OVER = 0.2042    # 100万円超: 20.42%


@dataclass
class WithholdingResult:
    """源泉徴収計算結果"""
    gross_amount: int        # 支給総額 / 報酬総額
    withholding_tax: int     # 源泉徴収税額
    net_amount: int          # 差引支給額
    type: WithholdingType


def calc_withholding_salary(
    monthly_gross: int,
    dependents: int = 0,
) -> WithholdingResult:
    """
    給与の源泉徴収税を計算（月額・甲欄・簡易）

    Args:
        monthly_gross: 月額総支給額
        dependents: 扶養親族数
    """
    # 社会保険料控除後の金額を概算 (総支給額の約15%を控除)
    social_ins_deduction = int(monthly_gross * 0.15)
    taxable = monthly_gross - social_ins_deduction

    # 扶養控除 (1人あたり約31,667円/月)
    dependent_deduction = dependents * 31_667
    taxable = max(0, taxable - dependent_deduction)

    # 簡易税率適用
    tax = 0
    for limit, rate, _ in SALARY_WITHHOLDING_BRACKETS:
        if limit is not None and taxable <= limit:
            tax = int(taxable * rate)
            break
        elif limit is None:
            tax = int(taxable * rate)
    # 最低保証: 非課税範囲
    if taxable <= 88_000:
        tax = 0

    return WithholdingResult(
        gross_amount=monthly_gross,
        withholding_tax=tax,
        net_amount=monthly_gross - tax,
        type=WithholdingType.SALARY,
    )


def calc_withholding_professional(
    gross_amount: int,
) -> WithholdingResult:
    """
    報酬の源泉徴収税を計算（弁護士・税理士・デザイナー等）
    100万円以下: 10.21%
    100万円超部分: 20.42%
    """
    if gross_amount <= 1_000_000:
        tax = int(gross_amount * PROFESSIONAL_WITHHOLDING_RATE)
    else:
        tax = (int(1_000_000 * PROFESSIONAL_WITHHOLDING_RATE)
               + int((gross_amount - 1_000_000) * PROFESSIONAL_WITHHOLDING_RATE_OVER))

    return WithholdingResult(
        gross_amount=gross_amount,
        withholding_tax=tax,
        net_amount=gross_amount - tax,
        type=WithholdingType.PROFESSIONAL,
    )


# =====================================================================
# 統合: 全税金まとめて計算
# =====================================================================

@dataclass
class TotalTaxResult:
    """全税金の統合結果"""
    corp_tax: CorpTaxResult
    local_tax: LocalTaxResult
    total_tax: int                # 法人税 + 地方税の合計
    effective_rate: float         # 実効税率


def calc_total_tax(
    taxable_income: int,
    is_sme: bool = True,
    capital: int = 10_000_000,
    employee_count: int = 10,
) -> TotalTaxResult:
    """
    法人税 + 地方税の全額を計算

    Args:
        taxable_income: 課税所得
        is_sme: 中小法人か
        capital: 資本金
        employee_count: 従業員数
    """
    corp = calc_corporate_tax(taxable_income, is_sme)
    local = calc_local_tax(corp.corp_tax, taxable_income, capital, employee_count)
    total = corp.corp_tax + local.total

    return TotalTaxResult(
        corp_tax=corp,
        local_tax=local,
        total_tax=total,
        effective_rate=total / taxable_income if taxable_income > 0 else 0.0,
    )
