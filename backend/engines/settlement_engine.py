"""
決算エンジン
仕訳データから財務諸表を自動生成する。

- 損益計算書 (P/L)
- 貸借対照表 (B/S)
- キャッシュフロー計算書 (C/F)
- 試算表 (残高試算表・合計試算表)

全関数は純粋関数: 仕訳リストを受け取り、計算結果を返すだけ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from .journal_engine import (
    Account, AccountCategory, NormalBalance,
    JournalEntry, JournalLine,
    ACCOUNTS,
)


# =====================================================================
# 試算表
# =====================================================================

@dataclass
class TrialBalanceRow:
    """試算表の1行"""
    code: str
    name: str
    category: str          # 資産/負債/純資産/収益/費用
    sub_category: str
    debit_total: int       # 借方合計
    credit_total: int      # 貸方合計
    debit_balance: int     # 借方残高
    credit_balance: int    # 貸方残高


@dataclass
class TrialBalance:
    """試算表"""
    rows: list[TrialBalanceRow]
    total_debit: int
    total_credit: int
    is_balanced: bool


def calc_trial_balance(entries: Sequence[JournalEntry]) -> TrialBalance:
    """
    合計残高試算表を生成

    合計試算表: 各勘定科目の借方合計・貸方合計
    残高試算表: 各勘定科目の残高 (正常残高方向)
    → この関数は両方を含む合計残高試算表を返す
    """
    totals: dict[str, dict] = {}

    for entry in entries:
        for ln in entry.lines:
            code = ln.account.code
            if code not in totals:
                totals[code] = {"debit": 0, "credit": 0}
            totals[code]["debit"] += ln.debit
            totals[code]["credit"] += ln.credit

    rows: list[TrialBalanceRow] = []
    sum_debit = 0
    sum_credit = 0

    for code in sorted(totals.keys()):
        acct = ACCOUNTS[code]
        d = totals[code]["debit"]
        c = totals[code]["credit"]

        if acct.normal_balance == NormalBalance.DEBIT:
            debit_bal = d - c if d >= c else 0
            credit_bal = c - d if c > d else 0
        else:
            debit_bal = d - c if d > c else 0
            credit_bal = c - d if c >= d else 0

        rows.append(TrialBalanceRow(
            code=code,
            name=acct.name,
            category=acct.category.value,
            sub_category=acct.sub_category,
            debit_total=d,
            credit_total=c,
            debit_balance=debit_bal,
            credit_balance=credit_bal,
        ))
        sum_debit += d
        sum_credit += c

    return TrialBalance(
        rows=rows,
        total_debit=sum_debit,
        total_credit=sum_credit,
        is_balanced=(sum_debit == sum_credit),
    )


def calc_summary_trial_balance(entries: Sequence[JournalEntry]) -> dict[str, int]:
    """
    合計試算表 (勘定科目コード → 残高) を辞書で返す。
    正常残高方向で符号付き。
    """
    tb = calc_trial_balance(entries)
    result: dict[str, int] = {}
    for row in tb.rows:
        acct = ACCOUNTS[row.code]
        if acct.normal_balance == NormalBalance.DEBIT:
            result[row.code] = row.debit_total - row.credit_total
        else:
            result[row.code] = row.credit_total - row.debit_total
    return result


# =====================================================================
# 損益計算書 (P/L)
# =====================================================================

@dataclass
class PLLineItem:
    """P/Lの1科目"""
    code: str
    name: str
    amount: int


@dataclass
class ProfitAndLoss:
    """損益計算書"""
    # 売上高
    revenue_items: list[PLLineItem]
    sales_total: int

    # 売上原価
    cogs_items: list[PLLineItem]
    cogs_total: int

    # 売上総利益
    gross_profit: int

    # 販管費
    sga_items: list[PLLineItem]
    sga_total: int

    # 営業利益
    operating_profit: int

    # 営業外収益
    non_op_income_items: list[PLLineItem]
    non_op_income_total: int

    # 営業外費用
    non_op_expense_items: list[PLLineItem]
    non_op_expense_total: int

    # 経常利益
    ordinary_profit: int

    # 特別利益
    special_income_items: list[PLLineItem]
    special_income_total: int

    # 特別損失
    special_loss_items: list[PLLineItem]
    special_loss_total: int

    # 税引前当期純利益
    income_before_tax: int

    # 法人税等
    tax_expense: int

    # 当期純利益
    net_income: int


def calc_profit_and_loss(entries: Sequence[JournalEntry]) -> ProfitAndLoss:
    """仕訳データから損益計算書を生成"""
    balances = calc_summary_trial_balance(entries)

    def collect(category: AccountCategory, sub: str) -> list[PLLineItem]:
        items: list[PLLineItem] = []
        for code, bal in balances.items():
            acct = ACCOUNTS[code]
            if acct.category == category and acct.sub_category == sub and bal != 0:
                items.append(PLLineItem(code=code, name=acct.name, amount=bal))
        return sorted(items, key=lambda x: x.code)

    revenue = collect(AccountCategory.REVENUE, "売上高")
    cogs = collect(AccountCategory.EXPENSE, "売上原価")
    sga = collect(AccountCategory.EXPENSE, "販管費")
    non_op_inc = collect(AccountCategory.REVENUE, "営業外収益")
    non_op_exp = collect(AccountCategory.EXPENSE, "営業外費用")
    sp_inc = collect(AccountCategory.REVENUE, "特別利益")
    sp_loss = collect(AccountCategory.EXPENSE, "特別損失")
    tax_items = collect(AccountCategory.EXPENSE, "法人税等")

    sales_total = sum(i.amount for i in revenue)
    cogs_total = sum(i.amount for i in cogs)
    gross = sales_total - cogs_total
    sga_total = sum(i.amount for i in sga)
    operating = gross - sga_total
    noi_total = sum(i.amount for i in non_op_inc)
    noe_total = sum(i.amount for i in non_op_exp)
    ordinary = operating + noi_total - noe_total
    spi_total = sum(i.amount for i in sp_inc)
    spl_total = sum(i.amount for i in sp_loss)
    before_tax = ordinary + spi_total - spl_total
    tax = sum(i.amount for i in tax_items)
    net = before_tax - tax

    return ProfitAndLoss(
        revenue_items=revenue, sales_total=sales_total,
        cogs_items=cogs, cogs_total=cogs_total,
        gross_profit=gross,
        sga_items=sga, sga_total=sga_total,
        operating_profit=operating,
        non_op_income_items=non_op_inc, non_op_income_total=noi_total,
        non_op_expense_items=non_op_exp, non_op_expense_total=noe_total,
        ordinary_profit=ordinary,
        special_income_items=sp_inc, special_income_total=spi_total,
        special_loss_items=sp_loss, special_loss_total=spl_total,
        income_before_tax=before_tax,
        tax_expense=tax,
        net_income=net,
    )


# =====================================================================
# 貸借対照表 (B/S)
# =====================================================================

@dataclass
class BSSection:
    """B/Sのセクション"""
    label: str
    items: list[PLLineItem]
    total: int


@dataclass
class BalanceSheet:
    """貸借対照表"""
    # 資産の部
    current_assets: BSSection
    tangible_fixed_assets: BSSection
    intangible_fixed_assets: BSSection
    investments: BSSection
    total_assets: int

    # 負債の部
    current_liabilities: BSSection
    long_term_liabilities: BSSection
    total_liabilities: int

    # 純資産の部
    equity_items: list[PLLineItem]
    net_income: int          # 当期純利益
    total_equity: int

    # バランスチェック
    total_liabilities_and_equity: int
    is_balanced: bool


def calc_balance_sheet(entries: Sequence[JournalEntry]) -> BalanceSheet:
    """仕訳データから貸借対照表を生成"""
    balances = calc_summary_trial_balance(entries)
    pl = calc_profit_and_loss(entries)

    def collect_bs(category: AccountCategory, sub: str) -> list[PLLineItem]:
        items: list[PLLineItem] = []
        for code, bal in balances.items():
            acct = ACCOUNTS[code]
            if acct.category == category and acct.sub_category == sub and bal != 0:
                items.append(PLLineItem(code=code, name=acct.name, amount=bal))
        return sorted(items, key=lambda x: x.code)

    def section(label: str, cat: AccountCategory, sub: str) -> BSSection:
        items = collect_bs(cat, sub)
        return BSSection(label=label, items=items, total=sum(i.amount for i in items))

    # 資産
    ca = section("流動資産", AccountCategory.ASSET, "流動資産")
    tfa = section("有形固定資産", AccountCategory.ASSET, "有形固定資産")
    ifa = section("無形固定資産", AccountCategory.ASSET, "無形固定資産")
    inv = section("投資その他", AccountCategory.ASSET, "投資その他")
    total_assets = ca.total + tfa.total + ifa.total + inv.total

    # 負債
    cl = section("流動負債", AccountCategory.LIABILITY, "流動負債")
    ll = section("固定負債", AccountCategory.LIABILITY, "固定負債")
    total_liabilities = cl.total + ll.total

    # 純資産
    equity = collect_bs(AccountCategory.EQUITY, "株主資本")
    equity_total = sum(i.amount for i in equity) + pl.net_income

    total_le = total_liabilities + equity_total

    return BalanceSheet(
        current_assets=ca,
        tangible_fixed_assets=tfa,
        intangible_fixed_assets=ifa,
        investments=inv,
        total_assets=total_assets,
        current_liabilities=cl,
        long_term_liabilities=ll,
        total_liabilities=total_liabilities,
        equity_items=equity,
        net_income=pl.net_income,
        total_equity=equity_total,
        total_liabilities_and_equity=total_le,
        is_balanced=(total_assets == total_le),
    )


# =====================================================================
# キャッシュフロー計算書 (C/F)  間接法
# =====================================================================

@dataclass
class CashFlowStatement:
    """キャッシュフロー計算書"""
    # 営業活動
    net_income: int
    depreciation: int              # 減価償却費(加算)
    change_receivables: int        # 売掛金増減 (増→マイナス)
    change_payables: int           # 買掛金増減 (増→プラス)
    change_inventory: int          # 棚卸資産増減 (増→マイナス)
    other_operating: int
    operating_cf: int

    # 投資活動
    capex: int                     # 固定資産取得 (マイナス)
    other_investing: int
    investing_cf: int

    # 財務活動
    borrowings: int                # 借入 (プラス)
    repayments: int                # 返済 (マイナス)
    other_financing: int
    financing_cf: int

    # 合計
    net_change: int
    beginning_cash: int
    ending_cash: int


def calc_cash_flow_statement(
    entries: Sequence[JournalEntry],
    beginning_cash: int = 0,
) -> CashFlowStatement:
    """
    仕訳データからキャッシュフロー計算書を生成（間接法）

    間接法: 当期純利益からスタートし、非資金項目を調整
    """
    balances = calc_summary_trial_balance(entries)
    pl = calc_profit_and_loss(entries)

    net_income = pl.net_income

    # 減価償却費 (非資金費用 → 加算)
    depreciation = balances.get("5390", 0)

    # 売掛金の増減 (増加→CF減少)
    receivables = balances.get("1130", 0)
    change_receivables = -receivables

    # 買掛金の増減 (増加→CF増加)
    payables = balances.get("2100", 0)
    change_payables = payables

    # 棚卸資産の増減
    inventory = balances.get("1150", 0) + balances.get("1160", 0)
    change_inventory = -inventory

    # その他営業 (前払費用、未払費用等の増減)
    prepaid = balances.get("1180", 0)
    accrued = balances.get("2140", 0)
    other_op = -prepaid + accrued

    operating_cf = (net_income + depreciation + change_receivables
                    + change_payables + change_inventory + other_op)

    # 投資活動: 固定資産の増加
    fixed_asset_codes = [c for c in balances if c.startswith("13") or c.startswith("14") or c.startswith("15")]
    # 除: 減価償却累計額(139x)
    capex = -sum(balances.get(c, 0) for c in fixed_asset_codes
                 if not c.startswith("139"))
    investing_cf = capex

    # 財務活動
    long_borrow = balances.get("2300", 0)
    short_borrow = balances.get("2120", 0)
    borrowings = long_borrow + short_borrow
    # 資本金増加
    capital_change = balances.get("3100", 0) + balances.get("3110", 0)
    financing_cf = borrowings + capital_change

    net_change = operating_cf + investing_cf + financing_cf
    ending_cash = beginning_cash + net_change

    return CashFlowStatement(
        net_income=net_income,
        depreciation=depreciation,
        change_receivables=change_receivables,
        change_payables=change_payables,
        change_inventory=change_inventory,
        other_operating=other_op,
        operating_cf=operating_cf,
        capex=capex,
        other_investing=0,
        investing_cf=investing_cf,
        borrowings=borrowings,
        repayments=0,
        other_financing=capital_change,
        financing_cf=financing_cf,
        net_change=net_change,
        beginning_cash=beginning_cash,
        ending_cash=ending_cash,
    )


# =====================================================================
# 決算統合
# =====================================================================

@dataclass
class SettlementResult:
    """決算結果の全体"""
    trial_balance: TrialBalance
    profit_and_loss: ProfitAndLoss
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement
    period_start: date
    period_end: date
    entry_count: int


def generate_settlement(
    entries: Sequence[JournalEntry],
    period_start: date | None = None,
    period_end: date | None = None,
    beginning_cash: int = 0,
) -> SettlementResult:
    """
    仕訳データから決算書類一式を生成

    Args:
        entries: 仕訳データ
        period_start: 期首日 (省略時は仕訳の最古日)
        period_end: 期末日 (省略時は仕訳の最新日)
        beginning_cash: 期首現金残高
    """
    if not entries:
        today = date.today()
        p_start = period_start or today
        p_end = period_end or today
        empty_entries: list[JournalEntry] = []
        return SettlementResult(
            trial_balance=calc_trial_balance(empty_entries),
            profit_and_loss=calc_profit_and_loss(empty_entries),
            balance_sheet=calc_balance_sheet(empty_entries),
            cash_flow=calc_cash_flow_statement(empty_entries, beginning_cash),
            period_start=p_start,
            period_end=p_end,
            entry_count=0,
        )

    sorted_entries = sorted(entries, key=lambda e: e.entry_date)
    p_start = period_start or sorted_entries[0].entry_date
    p_end = period_end or sorted_entries[-1].entry_date

    # 期間内の仕訳のみ抽出
    filtered = [e for e in sorted_entries if p_start <= e.entry_date <= p_end]

    return SettlementResult(
        trial_balance=calc_trial_balance(filtered),
        profit_and_loss=calc_profit_and_loss(filtered),
        balance_sheet=calc_balance_sheet(filtered),
        cash_flow=calc_cash_flow_statement(filtered, beginning_cash),
        period_start=p_start,
        period_end=p_end,
        entry_count=len(filtered),
    )
