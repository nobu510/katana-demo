"""
自動仕訳エンジン
チャット入力 → 勘定科目自動判定 → 複式簿記仕訳を自動生成
日本の勘定科目体系（資産・負債・純資産・収益・費用）に完全準拠
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Sequence

from .numbering_engine import NumberingState, generate_journal_id


# =====================================================================
# 勘定科目体系
# =====================================================================

class AccountCategory(str, Enum):
    """勘定科目の5大分類"""
    ASSET = "資産"
    LIABILITY = "負債"
    EQUITY = "純資産"
    REVENUE = "収益"
    EXPENSE = "費用"


class NormalBalance(str, Enum):
    """正常残高の方向"""
    DEBIT = "借方"
    CREDIT = "貸方"


@dataclass(frozen=True)
class Account:
    """勘定科目"""
    code: str           # 勘定科目コード
    name: str           # 勘定科目名
    category: AccountCategory
    normal_balance: NormalBalance
    sub_category: str = ""    # 小分類
    tax_category: str = ""    # 消費税区分: "課税", "非課税", "不課税", "免税"
    description: str = ""


# ===== 勘定科目マスタ（日本基準） =====

ACCOUNTS: dict[str, Account] = {}

def _a(code: str, name: str, cat: AccountCategory, nb: NormalBalance,
       sub: str = "", tax: str = "", desc: str = "") -> Account:
    acct = Account(code=code, name=name, category=cat, normal_balance=nb,
                   sub_category=sub, tax_category=tax, description=desc)
    ACCOUNTS[code] = acct
    return acct

# ----- 資産 (1xxx) -----
# 流動資産
CASH                = _a("1100", "現金",           AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
DEPOSITS            = _a("1110", "普通預金",        AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
CHECKING            = _a("1120", "当座預金",        AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
ACCOUNTS_RECEIVABLE = _a("1130", "売掛金",         AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
NOTES_RECEIVABLE    = _a("1140", "受取手形",        AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
INVENTORY           = _a("1150", "商品",           AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
WORK_IN_PROGRESS    = _a("1160", "仕掛品",         AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
SUPPLIES            = _a("1170", "貯蔵品",         AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
PREPAID_EXPENSE     = _a("1180", "前払費用",        AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
ADVANCE_PAYMENT     = _a("1190", "前払金",         AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
ACCRUED_REVENUE     = _a("1200", "未収入金",        AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
CONSUMPTION_TAX_RCV = _a("1210", "仮払消費税",      AccountCategory.ASSET, NormalBalance.DEBIT, "流動資産", "不課税")
# 固定資産 - 有形
BUILDINGS           = _a("1300", "建物",           AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
EQUIPMENT           = _a("1310", "機械装置",        AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
VEHICLES            = _a("1320", "車両運搬具",      AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
TOOLS               = _a("1330", "工具器具備品",     AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
LAND                = _a("1340", "土地",           AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
CONSTRUCTION_WIP    = _a("1350", "建設仮勘定",      AccountCategory.ASSET, NormalBalance.DEBIT, "有形固定資産", "不課税")
# 固定資産 - 無形
SOFTWARE            = _a("1400", "ソフトウェア",     AccountCategory.ASSET, NormalBalance.DEBIT, "無形固定資産", "不課税")
GOODWILL            = _a("1410", "のれん",         AccountCategory.ASSET, NormalBalance.DEBIT, "無形固定資産", "不課税")
# 固定資産 - 投資
INVESTMENT_SEC      = _a("1500", "投資有価証券",     AccountCategory.ASSET, NormalBalance.DEBIT, "投資その他", "不課税")
LONG_TERM_LOAN      = _a("1510", "長期貸付金",      AccountCategory.ASSET, NormalBalance.DEBIT, "投資その他", "不課税")
GUARANTEE_DEPOSIT   = _a("1520", "差入保証金",      AccountCategory.ASSET, NormalBalance.DEBIT, "投資その他", "不課税")
# 減価償却累計額
ACCUM_DEPR_BLDG     = _a("1390", "建物減価償却累計額",  AccountCategory.ASSET, NormalBalance.CREDIT, "有形固定資産", "不課税")
ACCUM_DEPR_EQUIP    = _a("1391", "機械装置減価償却累計額", AccountCategory.ASSET, NormalBalance.CREDIT, "有形固定資産", "不課税")
ACCUM_DEPR_VEHICLE  = _a("1392", "車両運搬具減価償却累計額", AccountCategory.ASSET, NormalBalance.CREDIT, "有形固定資産", "不課税")
ACCUM_DEPR_TOOLS    = _a("1393", "工具器具備品減価償却累計額", AccountCategory.ASSET, NormalBalance.CREDIT, "有形固定資産", "不課税")

# ----- 負債 (2xxx) -----
# 流動負債
ACCOUNTS_PAYABLE    = _a("2100", "買掛金",         AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
NOTES_PAYABLE       = _a("2110", "支払手形",        AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
SHORT_TERM_LOAN     = _a("2120", "短期借入金",      AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
UNEARNED_REVENUE    = _a("2130", "前受金",         AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
ACCRUED_EXPENSE     = _a("2140", "未払費用",        AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
ACCRUED_TAX         = _a("2150", "未払法人税等",     AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
ACCRUED_CONSUMPTION = _a("2160", "未払消費税",       AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
CONSUMPTION_TAX_PAY = _a("2170", "仮受消費税",      AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
DEPOSIT_RECEIVED    = _a("2180", "預り金",         AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
WITHHELD_TAX        = _a("2190", "源泉所得税預り金",  AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
SOCIAL_INS_PAYABLE  = _a("2200", "社会保険料預り金",  AccountCategory.LIABILITY, NormalBalance.CREDIT, "流動負債", "不課税")
# 固定負債
LONG_TERM_BORROW    = _a("2300", "長期借入金",      AccountCategory.LIABILITY, NormalBalance.CREDIT, "固定負債", "不課税")
RETIREMENT_ALLOW    = _a("2310", "退職給付引当金",    AccountCategory.LIABILITY, NormalBalance.CREDIT, "固定負債", "不課税")

# ----- 純資産 (3xxx) -----
CAPITAL             = _a("3100", "資本金",         AccountCategory.EQUITY, NormalBalance.CREDIT, "株主資本")
CAPITAL_RESERVE     = _a("3110", "資本準備金",      AccountCategory.EQUITY, NormalBalance.CREDIT, "株主資本")
RETAINED_EARNINGS   = _a("3200", "繰越利益剰余金",   AccountCategory.EQUITY, NormalBalance.CREDIT, "株主資本")
LEGAL_RESERVE       = _a("3210", "利益準備金",      AccountCategory.EQUITY, NormalBalance.CREDIT, "株主資本")

# ----- 収益 (4xxx) -----
SALES               = _a("4100", "売上高",         AccountCategory.REVENUE, NormalBalance.CREDIT, "売上高", "課税")
SERVICE_REVENUE     = _a("4110", "役務収益",        AccountCategory.REVENUE, NormalBalance.CREDIT, "売上高", "課税")
INTEREST_INCOME     = _a("4200", "受取利息",        AccountCategory.REVENUE, NormalBalance.CREDIT, "営業外収益", "非課税")
DIVIDEND_INCOME     = _a("4210", "受取配当金",      AccountCategory.REVENUE, NormalBalance.CREDIT, "営業外収益", "不課税")
GAIN_ON_SALE        = _a("4300", "固定資産売却益",   AccountCategory.REVENUE, NormalBalance.CREDIT, "特別利益", "課税")
MISC_INCOME         = _a("4900", "雑収入",         AccountCategory.REVENUE, NormalBalance.CREDIT, "営業外収益", "課税")

# ----- 費用 (5xxx) -----
# 売上原価
COST_OF_SALES       = _a("5100", "売上原価",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "売上原価", "課税")
PURCHASES           = _a("5110", "仕入高",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "売上原価", "課税")
OUTSOURCING         = _a("5120", "外注費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "売上原価", "課税")
MATERIAL_COST       = _a("5130", "材料費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "売上原価", "課税")
# 販管費 - 人件費
SALARY              = _a("5200", "給与手当",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
BONUS               = _a("5210", "賞与",           AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
STATUTORY_WELFARE   = _a("5220", "法定福利費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
WELFARE             = _a("5230", "福利厚生費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
RETIREMENT_EXP      = _a("5240", "退職給付費用",     AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
DIRECTORS_COMP      = _a("5250", "役員報酬",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
# 販管費 - 経費
RENT                = _a("5300", "地代家賃",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
UTILITIES           = _a("5310", "水道光熱費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
COMMUNICATION       = _a("5320", "通信費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
TRANSPORTATION      = _a("5330", "旅費交通費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
ENTERTAINMENT       = _a("5340", "接待交際費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
ADVERTISING         = _a("5350", "広告宣伝費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
SUPPLIES_EXP        = _a("5360", "消耗品費",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
INSURANCE_EXP       = _a("5370", "保険料",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "非課税")
REPAIR_EXP          = _a("5380", "修繕費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
DEPRECIATION        = _a("5390", "減価償却費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
LEASE_EXP           = _a("5400", "リース料",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
TAX_AND_DUES        = _a("5410", "租税公課",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "不課税")
PROFESSIONAL_FEE    = _a("5420", "支払報酬",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
TRAINING_EXP        = _a("5430", "研修費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
MEETING_EXP         = _a("5440", "会議費",         AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
PACKING_EXP         = _a("5450", "荷造運賃",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
SUBSCRIPTION        = _a("5460", "新聞図書費",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
COMMISSION          = _a("5470", "支払手数料",      AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
MISC_EXPENSE        = _a("5900", "雑費",           AccountCategory.EXPENSE, NormalBalance.DEBIT, "販管費", "課税")
# 営業外費用
INTEREST_EXPENSE    = _a("5600", "支払利息",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "営業外費用", "非課税")
LOSS_ON_SALE        = _a("5700", "固定資産売却損",   AccountCategory.EXPENSE, NormalBalance.DEBIT, "特別損失", "不課税")
# 法人税等
CORP_TAX            = _a("5800", "法人税等",        AccountCategory.EXPENSE, NormalBalance.DEBIT, "法人税等", "不課税")


def get_account(code: str) -> Account:
    """コードから勘定科目を取得"""
    return ACCOUNTS[code]


def find_account_by_name(name: str) -> Account | None:
    """名称から勘定科目を検索"""
    for acct in ACCOUNTS.values():
        if acct.name == name:
            return acct
    return None


def accounts_by_category(cat: AccountCategory) -> list[Account]:
    """分類で勘定科目を抽出"""
    return [a for a in ACCOUNTS.values() if a.category == cat]


# =====================================================================
# 仕訳データ型
# =====================================================================

@dataclass
class JournalLine:
    """仕訳行（1借方 or 1貸方）"""
    account: Account
    debit: int = 0      # 借方金額
    credit: int = 0     # 貸方金額
    tax_amount: int = 0  # 消費税額
    sub_account: str = ""  # 補助科目（取引先名など）
    memo: str = ""


@dataclass
class JournalEntry:
    """仕訳伝票"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    numbering_id: str = ""   # J001-C001 形式の採番ID
    company_id: str = ""     # C001 形式の企業ID
    project_id: str = ""     # P001-C001 形式の案件ID (紐づく場合)
    entry_date: date = field(default_factory=date.today)
    description: str = ""
    lines: list[JournalLine] = field(default_factory=list)
    source: str = ""         # "chat", "ocr", "auto", "manual"
    source_text: str = ""    # 元のチャットメッセージ
    fiscal_year: int = 0
    fiscal_month: int = 0    # 0-11 (4月=0)
    approved: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_debit(self) -> int:
        return sum(ln.debit for ln in self.lines)

    @property
    def total_credit(self) -> int:
        return sum(ln.credit for ln in self.lines)

    @property
    def is_balanced(self) -> bool:
        """借方合計 = 貸方合計 であるか"""
        return self.total_debit == self.total_credit

    def validate(self) -> list[str]:
        """仕訳の検証"""
        errors: list[str] = []
        if not self.lines:
            errors.append("仕訳行がありません")
        if not self.is_balanced:
            errors.append(
                f"貸借不一致: 借方{self.total_debit:,}円 ≠ 貸方{self.total_credit:,}円"
            )
        for i, ln in enumerate(self.lines):
            if ln.debit < 0 or ln.credit < 0:
                errors.append(f"行{i+1}: 金額が負です")
            if ln.debit == 0 and ln.credit == 0:
                errors.append(f"行{i+1}: 金額が0です")
            if ln.debit > 0 and ln.credit > 0:
                errors.append(f"行{i+1}: 借方と貸方の両方に金額があります")
        return errors


# =====================================================================
# 自動仕訳テンプレート
# =====================================================================

@dataclass
class JournalTemplate:
    """定型仕訳のテンプレート"""
    name: str
    description: str
    keywords: list[str]        # チャットから検出するキーワード
    debit_account: Account
    credit_account: Account
    tax_applicable: bool = True  # 消費税対象か
    category: str = ""           # "売上", "仕入", "経費", "給与", "資産" 等

    def _is_purchase_type(self) -> bool:
        """仕入・経費・資産取得 → 仮払消費税"""
        if self.debit_account.category == AccountCategory.EXPENSE:
            return True
        # 固定資産取得 (TOOLS, SOFTWARE 等)
        if (self.debit_account.category == AccountCategory.ASSET
                and self.debit_account.sub_category in (
                    "有形固定資産", "無形固定資産", "流動資産")
                and self.debit_account.tax_category != "不課税"):
            return True
        if self.category in ("仕入", "経費", "資産"):
            return True
        return False

    def _is_sale_type(self) -> bool:
        """売上 → 仮受消費税"""
        return self.credit_account.category == AccountCategory.REVENUE

    def generate(
        self,
        amount: int,
        entry_date: date | None = None,
        description: str = "",
        sub_account: str = "",
        source_text: str = "",
        include_tax: bool = True,
        tax_rate: float = 0.10,
        payment_method: str = "bank",  # "bank" or "cash"
    ) -> JournalEntry:
        """
        テンプレートから仕訳を生成。

        税込金額を受け取り、本体+消費税に分解して複式簿記仕訳を作る。
        - 仕入/経費/資産取得 → 仮払消費税 (借方)
        - 売上 → 仮受消費税 (貸方)
        - 不課税/非課税 → 税行なし

        payment_method: "cash" → 現金勘定, "bank" → 普通預金勘定
        """
        dt = entry_date or date.today()
        fiscal_month = (dt.month - 4) % 12  # 4月=0

        # 支払方法による貸方勘定の差し替え
        credit_acct = self.credit_account
        if payment_method == "cash" and self.credit_account == DEPOSITS:
            credit_acct = CASH
        debit_acct = self.debit_account
        if payment_method == "cash" and self.debit_account == DEPOSITS:
            debit_acct = CASH

        lines: list[JournalLine] = []

        if self.tax_applicable and include_tax and tax_rate > 0:
            # 税込金額 → 本体 + 消費税 (内税計算)
            tax_denom = int(round((1 + tax_rate) * 1000))
            tax = amount - amount * 1000 // tax_denom
            body = amount - tax

            if self._is_sale_type():
                # 売上系: 借方に税込金額、貸方に本体+仮受消費税
                lines.append(JournalLine(
                    account=debit_acct,
                    debit=amount,
                    sub_account=sub_account,
                    memo=description,
                ))
                lines.append(JournalLine(
                    account=self.credit_account,
                    credit=body,
                    sub_account=sub_account,
                    memo=description,
                ))
                lines.append(JournalLine(
                    account=CONSUMPTION_TAX_PAY,
                    credit=tax,
                    memo=f"消費税({description})",
                ))
            elif self._is_purchase_type():
                # 仕入/経費/資産取得: 借方に本体+仮払消費税、貸方に税込金額
                lines.append(JournalLine(
                    account=self.debit_account,
                    debit=body,
                    sub_account=sub_account,
                    memo=description,
                ))
                lines.append(JournalLine(
                    account=CONSUMPTION_TAX_RCV,
                    debit=tax,
                    memo=f"消費税({description})",
                ))
                lines.append(JournalLine(
                    account=credit_acct,
                    credit=amount,
                    sub_account=sub_account,
                    memo=description,
                ))
            else:
                # 課税だがどちらにも当てはまらない場合 → 単純仕訳
                lines.append(JournalLine(
                    account=debit_acct,
                    debit=amount,
                    sub_account=sub_account,
                    memo=description,
                ))
                lines.append(JournalLine(
                    account=credit_acct,
                    credit=amount,
                    sub_account=sub_account,
                    memo=description,
                ))
        else:
            # 不課税・非課税取引
            lines.append(JournalLine(
                account=debit_acct,
                debit=amount,
                sub_account=sub_account,
                memo=description,
            ))
            lines.append(JournalLine(
                account=credit_acct,
                credit=amount,
                sub_account=sub_account,
                memo=description,
            ))

        return JournalEntry(
            entry_date=dt,
            description=description or self.description,
            lines=lines,
            source="chat",
            source_text=source_text,
            fiscal_year=dt.year if dt.month >= 4 else dt.year - 1,
            fiscal_month=fiscal_month,
        )


# ===== 定型仕訳テンプレート集 =====

TEMPLATES: list[JournalTemplate] = [
    # --- 売上系 ---
    JournalTemplate(
        "売上計上",
        "売上高の計上",
        ["売上", "売れた", "売った", "受注", "納品", "検収"],
        ACCOUNTS_RECEIVABLE, SALES,
        tax_applicable=True,
        category="売上",
    ),
    JournalTemplate(
        "売上入金",
        "売掛金の回収（入金）",
        ["入金", "振込", "振り込", "回収", "受取"],
        DEPOSITS, ACCOUNTS_RECEIVABLE,
        tax_applicable=False,
        category="売上",
    ),
    JournalTemplate(
        "前受金受領",
        "前受金の受領",
        ["前受", "着手金", "手付金", "デポジット"],
        DEPOSITS, UNEARNED_REVENUE,
        tax_applicable=False,
        category="売上",
    ),
    # --- 仕入・原価系 ---
    JournalTemplate(
        "仕入計上",
        "仕入高の計上",
        ["仕入", "購入", "買った"],
        PURCHASES, ACCOUNTS_PAYABLE,
        tax_applicable=True,
        category="仕入",
    ),
    JournalTemplate(
        "外注費計上",
        "外注費の計上",
        ["外注", "委託", "下請", "業務委託"],
        OUTSOURCING, ACCOUNTS_PAYABLE,
        tax_applicable=True,
        category="仕入",
    ),
    JournalTemplate(
        "材料費計上",
        "材料費の計上",
        ["材料", "原材料", "部材", "食材"],
        MATERIAL_COST, ACCOUNTS_PAYABLE,
        tax_applicable=True,
        category="仕入",
    ),
    JournalTemplate(
        "買掛金支払",
        "買掛金の支払い",
        ["買掛金", "仕入代金"],
        ACCOUNTS_PAYABLE, DEPOSITS,
        tax_applicable=False,
        category="仕入",
    ),
    # --- 給与・人件費系 ---
    JournalTemplate(
        "給与支払",
        "給与の支払い",
        ["給与", "給料", "月給", "賃金"],
        SALARY, DEPOSITS,
        tax_applicable=False,
        category="給与",
    ),
    JournalTemplate(
        "賞与支払",
        "賞与の支払い",
        ["賞与", "ボーナス"],
        BONUS, DEPOSITS,
        tax_applicable=False,
        category="給与",
    ),
    JournalTemplate(
        "役員報酬",
        "役員報酬の支払い",
        ["役員報酬", "役員"],
        DIRECTORS_COMP, DEPOSITS,
        tax_applicable=False,
        category="給与",
    ),
    JournalTemplate(
        "法定福利費",
        "社会保険料の事業主負担分",
        ["社会保険", "厚生年金", "健康保険", "雇用保険", "労災"],
        STATUTORY_WELFARE, DEPOSITS,
        tax_applicable=False,
        category="給与",
    ),
    # --- 経費系 ---
    JournalTemplate(
        "家賃支払",
        "地代家賃の支払い",
        ["家賃", "賃料", "テナント料"],
        RENT, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "水道光熱費",
        "水道光熱費の支払い",
        ["水道", "電気", "ガス", "光熱"],
        UTILITIES, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "通信費",
        "通信費の支払い",
        ["通信", "電話", "ネット", "インターネット", "Wi-Fi", "クラウド", "AWS", "サーバー代"],
        COMMUNICATION, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "旅費交通費",
        "旅費交通費の支払い",
        ["交通費", "旅費", "タクシー", "新幹線", "飛行機", "電車", "出張"],
        TRANSPORTATION, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "接待交際費",
        "接待交際費の支払い",
        ["接待", "交際", "懇親会", "飲み会", "ゴルフ"],
        ENTERTAINMENT, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "広告宣伝費",
        "広告宣伝費の支払い",
        ["広告", "宣伝", "PR", "マーケティング", "SEO", "リスティング"],
        ADVERTISING, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "消耗品費",
        "消耗品費の支払い",
        ["消耗品", "文房具", "事務用品", "コピー用紙", "トナー", "USB"],
        SUPPLIES_EXP, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "保険料",
        "保険料の支払い",
        ["保険料", "損害保険", "火災保険", "賠償保険"],
        INSURANCE_EXP, DEPOSITS,
        tax_applicable=False,
        category="経費",
    ),
    JournalTemplate(
        "修繕費",
        "修繕費の支払い",
        ["修繕", "修理", "メンテナンス"],
        REPAIR_EXP, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "リース料",
        "リース料の支払い",
        ["リース", "レンタル"],
        LEASE_EXP, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "研修費",
        "研修費の支払い",
        ["研修", "セミナー", "講習"],
        TRAINING_EXP, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "会議費",
        "会議費の支払い",
        ["会議", "ミーティング", "打ち合わせ"],
        MEETING_EXP, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "支払手数料",
        "手数料の支払い",
        ["手数料", "振込手数料", "決済手数料"],
        COMMISSION, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "租税公課",
        "税金・公課の支払い",
        ["税金", "印紙", "固定資産税", "自動車税", "印紙税", "登録免許税"],
        TAX_AND_DUES, DEPOSITS,
        tax_applicable=False,
        category="経費",
    ),
    JournalTemplate(
        "支払報酬",
        "専門家報酬の支払い",
        ["税理士", "会計士", "弁護士", "社労士", "司法書士", "顧問料", "コンサル"],
        PROFESSIONAL_FEE, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "新聞図書費",
        "書籍・サブスク",
        ["書籍", "本", "新聞", "雑誌", "サブスク"],
        SUBSCRIPTION, DEPOSITS,
        tax_applicable=True,
        category="経費",
    ),
    JournalTemplate(
        "支払利息",
        "借入金利息の支払い",
        ["利息", "利子", "金利"],
        INTEREST_EXPENSE, DEPOSITS,
        tax_applicable=False,
        category="経費",
    ),
    # --- 資産系 ---
    JournalTemplate(
        "備品購入",
        "工具器具備品の取得",
        ["PC", "パソコン", "モニター", "備品", "什器", "家具"],
        TOOLS, DEPOSITS,
        tax_applicable=True,
        category="資産",
    ),
    JournalTemplate(
        "ソフトウェア購入",
        "ソフトウェアの取得",
        ["ソフトウェア", "ライセンス", "SaaS年間"],
        SOFTWARE, DEPOSITS,
        tax_applicable=True,
        category="資産",
    ),
    # --- 借入系 ---
    JournalTemplate(
        "借入",
        "借入金の受入",
        ["借入", "融資", "ローン"],
        DEPOSITS, LONG_TERM_BORROW,
        tax_applicable=False,
        category="借入",
    ),
    JournalTemplate(
        "借入返済",
        "借入金の返済",
        ["返済", "ローン返済"],
        LONG_TERM_BORROW, DEPOSITS,
        tax_applicable=False,
        category="借入",
    ),
]


@dataclass
class TemplateMatch:
    """テンプレートマッチ結果"""
    template: JournalTemplate
    score: int            # マッチしたキーワード数
    confidence: float     # 0.0 ~ 1.0
    matched_keywords: list[str]


def find_template(text: str) -> JournalTemplate | None:
    """テキストからマッチするテンプレートを探す（スコア最高のもの）"""
    result = find_template_with_score(text)
    return result.template if result else None


def find_template_with_score(text: str) -> TemplateMatch | None:
    """テキストからマッチするテンプレートをスコア付きで探す"""
    best: TemplateMatch | None = None
    best_score = 0

    for tmpl in TEMPLATES:
        matched = [kw for kw in tmpl.keywords if kw in text]
        score = len(matched)
        if score > best_score:
            best_score = score
            # 信頼度: マッチ数 / キーワード総数 (最低でもマッチ1で0.3以上)
            confidence = min(1.0, score / max(len(tmpl.keywords), 1) + 0.2 * (score - 1))
            best = TemplateMatch(
                template=tmpl,
                score=score,
                confidence=round(confidence, 2),
                matched_keywords=matched,
            )

    return best


# =====================================================================
# 仕訳帳 (Journal Ledger)
# =====================================================================

class JournalLedger:
    """仕訳帳 - 全仕訳を時系列管理"""

    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    @property
    def entries(self) -> list[JournalEntry]:
        return list(self._entries)

    def add(self, entry: JournalEntry) -> list[str]:
        """仕訳を追加（検証付き）"""
        errors = entry.validate()
        if errors:
            return errors
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.entry_date)
        return []

    def get_by_month(self, fiscal_month: int) -> list[JournalEntry]:
        """月別の仕訳を取得"""
        return [e for e in self._entries if e.fiscal_month == fiscal_month]

    def get_by_account(self, account_code: str) -> list[JournalEntry]:
        """特定科目を含む仕訳を取得"""
        return [
            e for e in self._entries
            if any(ln.account.code == account_code for ln in e.lines)
        ]

    def get_by_date_range(self, start: date, end: date) -> list[JournalEntry]:
        """期間指定で仕訳を取得"""
        return [e for e in self._entries if start <= e.entry_date <= end]

    # ===== 総勘定元帳 =====

    def general_ledger(self, account_code: str) -> list[dict]:
        """
        総勘定元帳: 指定科目の全取引明細を返す
        """
        rows: list[dict] = []
        balance = 0
        acct = ACCOUNTS.get(account_code)
        if not acct:
            return rows

        for entry in self._entries:
            for ln in entry.lines:
                if ln.account.code != account_code:
                    continue
                if acct.normal_balance == NormalBalance.DEBIT:
                    balance += ln.debit - ln.credit
                else:
                    balance += ln.credit - ln.debit
                rows.append({
                    "date": entry.entry_date.isoformat(),
                    "description": entry.description,
                    "debit": ln.debit,
                    "credit": ln.credit,
                    "balance": balance,
                    "sub_account": ln.sub_account,
                    "memo": ln.memo,
                    "entry_id": entry.id,
                })
        return rows

    # ===== 試算表 =====

    def trial_balance(self) -> dict:
        """
        残高試算表を生成
        Returns: { account_code: { name, category, debit_total, credit_total, balance } }
        """
        tb: dict[str, dict] = {}

        for entry in self._entries:
            for ln in entry.lines:
                code = ln.account.code
                if code not in tb:
                    tb[code] = {
                        "code": code,
                        "name": ln.account.name,
                        "category": ln.account.category.value,
                        "sub_category": ln.account.sub_category,
                        "debit_total": 0,
                        "credit_total": 0,
                    }
                tb[code]["debit_total"] += ln.debit
                tb[code]["credit_total"] += ln.credit

        # 残高を計算
        for code, row in tb.items():
            acct = ACCOUNTS[code]
            if acct.normal_balance == NormalBalance.DEBIT:
                row["balance"] = row["debit_total"] - row["credit_total"]
            else:
                row["balance"] = row["credit_total"] - row["debit_total"]

        return tb

    # ===== 損益計算書 (P/L) =====

    def profit_and_loss(self) -> dict:
        """
        損益計算書を生成
        """
        tb = self.trial_balance()
        revenue_items: list[dict] = []
        cogs_items: list[dict] = []
        sga_items: list[dict] = []
        non_op_income: list[dict] = []
        non_op_expense: list[dict] = []
        special_income: list[dict] = []
        special_loss: list[dict] = []

        for row in tb.values():
            acct = ACCOUNTS[row["code"]]
            entry = {"code": row["code"], "name": row["name"], "amount": row["balance"]}

            if acct.category == AccountCategory.REVENUE:
                if acct.sub_category == "売上高":
                    revenue_items.append(entry)
                elif acct.sub_category == "営業外収益":
                    non_op_income.append(entry)
                elif acct.sub_category == "特別利益":
                    special_income.append(entry)
            elif acct.category == AccountCategory.EXPENSE:
                if acct.sub_category == "売上原価":
                    cogs_items.append(entry)
                elif acct.sub_category == "販管費":
                    sga_items.append(entry)
                elif acct.sub_category == "営業外費用":
                    non_op_expense.append(entry)
                elif acct.sub_category == "特別損失":
                    special_loss.append(entry)

        sales_total = sum(i["amount"] for i in revenue_items)
        cogs_total = sum(i["amount"] for i in cogs_items)
        gross_profit = sales_total - cogs_total
        sga_total = sum(i["amount"] for i in sga_items)
        operating_profit = gross_profit - sga_total
        non_op_income_total = sum(i["amount"] for i in non_op_income)
        non_op_expense_total = sum(i["amount"] for i in non_op_expense)
        ordinary_profit = operating_profit + non_op_income_total - non_op_expense_total
        special_income_total = sum(i["amount"] for i in special_income)
        special_loss_total = sum(i["amount"] for i in special_loss)
        income_before_tax = ordinary_profit + special_income_total - special_loss_total

        # 法人税等
        tax_items = [r for r in tb.values() if ACCOUNTS[r["code"]].sub_category == "法人税等"]
        tax_total = sum(i["balance"] for i in tax_items)
        net_income = income_before_tax - tax_total

        return {
            "売上高": {"items": revenue_items, "total": sales_total},
            "売上原価": {"items": cogs_items, "total": cogs_total},
            "売上総利益": gross_profit,
            "販管費": {"items": sga_items, "total": sga_total},
            "営業利益": operating_profit,
            "営業外収益": {"items": non_op_income, "total": non_op_income_total},
            "営業外費用": {"items": non_op_expense, "total": non_op_expense_total},
            "経常利益": ordinary_profit,
            "特別利益": {"items": special_income, "total": special_income_total},
            "特別損失": {"items": special_loss, "total": special_loss_total},
            "税引前当期純利益": income_before_tax,
            "法人税等": tax_total,
            "当期純利益": net_income,
        }

    # ===== 貸借対照表 (B/S) =====

    def balance_sheet(self) -> dict:
        """
        貸借対照表を生成
        """
        tb = self.trial_balance()
        assets: dict[str, list[dict]] = {
            "流動資産": [], "有形固定資産": [], "無形固定資産": [], "投資その他": [],
        }
        liabilities: dict[str, list[dict]] = {
            "流動負債": [], "固定負債": [],
        }
        equity: list[dict] = []

        for row in tb.values():
            acct = ACCOUNTS[row["code"]]
            entry = {"code": row["code"], "name": row["name"], "balance": row["balance"]}

            if acct.category == AccountCategory.ASSET:
                sub = acct.sub_category or "流動資産"
                if sub in assets:
                    assets[sub].append(entry)
            elif acct.category == AccountCategory.LIABILITY:
                sub = acct.sub_category or "流動負債"
                if sub in liabilities:
                    liabilities[sub].append(entry)
            elif acct.category == AccountCategory.EQUITY:
                equity.append(entry)

        # P/Lから当期純利益を加算
        pl = self.profit_and_loss()
        net_income = pl["当期純利益"]

        asset_total = sum(
            sum(e["balance"] for e in items)
            for items in assets.values()
        )
        liability_total = sum(
            sum(e["balance"] for e in items)
            for items in liabilities.values()
        )
        equity_total = sum(e["balance"] for e in equity) + net_income

        return {
            "資産の部": {
                "sections": assets,
                "total": asset_total,
            },
            "負債の部": {
                "sections": liabilities,
                "total": liability_total,
            },
            "純資産の部": {
                "items": equity,
                "当期純利益": net_income,
                "total": equity_total,
            },
            "負債・純資産合計": liability_total + equity_total,
        }


# =====================================================================
# 自動仕訳エンジン
# =====================================================================

class JournalEngine:
    """
    チャット入力から自動仕訳を生成するエンジン
    使い方:
        engine = JournalEngine()
        result = engine.process_chat("今月売上300万")
        # result = { "entry": JournalEntry, "template": "売上計上", "confidence": 0.9 }
    """

    def __init__(self, company_id: str = "") -> None:
        self.ledger = JournalLedger()
        self._templates = TEMPLATES
        self.company_id = company_id
        self._numbering_state = NumberingState()

    def _assign_numbering(self, entry: JournalEntry) -> JournalEntry:
        """仕訳に採番IDを付与"""
        if self.company_id:
            nid, self._numbering_state = generate_journal_id(
                self._numbering_state, self.company_id
            )
            entry.numbering_id = nid.id
            entry.company_id = self.company_id
        return entry

    def process_chat(
        self,
        text: str,
        entry_date: date | None = None,
        sub_account: str = "",
        project_id: str = "",
        payment_method: str = "",  # "cash", "bank", "" (自動検出)
    ) -> dict:
        """
        チャットテキストから仕訳を自動生成

        Returns:
            {
                "success": bool,
                "entry": JournalEntry | None,
                "template_name": str,
                "confidence": float,  # テンプレートマッチの信頼度
                "description": str,
                "errors": list[str],
                "amount": int,
                "detected_date": str | None,  # テキストから検出した日付
                "payment_method": str,
                "needs_ai": bool,  # AI判定が必要かどうか
            }
        """
        # 金額を抽出
        amount = self._extract_amount(text)
        if amount == 0:
            return {
                "success": False,
                "entry": None,
                "template_name": "",
                "confidence": 0.0,
                "description": "金額を読み取れませんでした",
                "errors": ["金額が含まれていません"],
                "amount": 0,
                "detected_date": None,
                "payment_method": "",
                "needs_ai": True,
            }

        # 日付を抽出 (明示的に渡されていない場合)
        detected_date = self._extract_date(text) if not entry_date else None
        effective_date = entry_date or detected_date

        # テンプレートマッチ (スコア付き)
        match = find_template_with_score(text)
        if not match:
            return {
                "success": False,
                "entry": None,
                "template_name": "",
                "confidence": 0.0,
                "description": "仕訳パターンを特定できませんでした",
                "errors": ["該当する仕訳テンプレートが見つかりません"],
                "amount": amount,
                "detected_date": detected_date.isoformat() if detected_date else None,
                "payment_method": "",
                "needs_ai": True,
            }

        tmpl = match.template

        # 支払方法の自動検出
        if not payment_method:
            payment_method = self._detect_payment_method(text)

        # 取引先名を抽出（「」内など）
        detected_sub = sub_account or self._extract_sub_account(text)

        # 軽減税率の検出
        tax_rate = 0.08 if self._is_reduced_tax(text) else 0.10

        # 仕訳を生成
        entry = tmpl.generate(
            amount=amount,
            entry_date=effective_date,
            description=self._build_description(tmpl, text, detected_sub),
            sub_account=detected_sub,
            source_text=text,
            payment_method=payment_method or "bank",
            tax_rate=tax_rate,
        )

        # 採番・案件紐づけ
        self._assign_numbering(entry)
        if project_id:
            entry.project_id = project_id

        # 帳簿に追加
        errors = self.ledger.add(entry)
        if errors:
            return {
                "success": False,
                "entry": entry,
                "template_name": tmpl.name,
                "confidence": match.confidence,
                "description": f"仕訳エラー: {', '.join(errors)}",
                "errors": errors,
                "amount": amount,
                "detected_date": detected_date.isoformat() if detected_date else None,
                "payment_method": payment_method,
                "needs_ai": False,
            }

        return {
            "success": True,
            "entry": entry,
            "template_name": tmpl.name,
            "confidence": match.confidence,
            "description": self._format_entry_summary(entry),
            "errors": [],
            "amount": amount,
            "detected_date": detected_date.isoformat() if detected_date else None,
            "payment_method": payment_method,
            "needs_ai": match.confidence < 0.3,
        }

    def add_entry(self, entry: JournalEntry) -> list[str]:
        """AI生成の仕訳を追加"""
        return self.ledger.add(entry)

    def get_pl(self) -> dict:
        """損益計算書"""
        return self.ledger.profit_and_loss()

    def get_bs(self) -> dict:
        """貸借対照表"""
        return self.ledger.balance_sheet()

    def get_tb(self) -> dict:
        """試算表"""
        return self.ledger.trial_balance()

    def get_journal(self, fiscal_month: int | None = None) -> list[JournalEntry]:
        """仕訳帳"""
        if fiscal_month is not None:
            return self.ledger.get_by_month(fiscal_month)
        return self.ledger.entries

    def get_general_ledger(self, account_code: str) -> list[dict]:
        """総勘定元帳"""
        return self.ledger.general_ledger(account_code)

    # ===== ユーティリティ =====

    @staticmethod
    def _extract_amount(text: str) -> int:
        """
        テキストから金額を抽出。

        対応パターン:
          - 3億円, 1.5億
          - 300万円, 300万
          - 3,000,000円
          - 50000円, 500円, 100円
          - ¥3000, ￥5000
        """
        patterns = [
            (r"(\d+(?:\.\d+)?)\s*億円?", 100_000_000),
            (r"(\d+(?:\.\d+)?)\s*千万円?", 10_000_000),
            (r"(\d+(?:\.\d+)?)\s*百万円?", 1_000_000),
            (r"(\d+(?:\.\d+)?)\s*万円?", 10_000),
            (r"(\d{1,3}(?:,\d{3})+)\s*円?", 1),
            (r"[¥￥]\s*(\d+(?:,\d{3})*)", 1),
            (r"(\d+)\s*円", 1),  # 「500円」「100円」も対応
        ]
        for pat, mult in patterns:
            m = re.search(pat, text)
            if m:
                val_str = m.group(1).replace(",", "")
                return int(float(val_str) * mult)
        return 0

    @staticmethod
    def _extract_date(text: str) -> date | None:
        """
        テキストから日付を抽出。

        対応パターン:
          - 2024年6月15日, 2024/6/15, 2024-06-15
          - 6月15日, 6/15 (今年として解釈)
          - 今日, 昨日, 先月
        """
        # フル日付: 2024年6月15日, 2024/6/15
        m = re.search(r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?', text)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass

        # 月日のみ: 6月15日, 6/15
        m = re.search(r'(\d{1,2})[月/](\d{1,2})日?', text)
        if m:
            try:
                today = date.today()
                return date(today.year, int(m.group(1)), int(m.group(2)))
            except ValueError:
                pass

        # 相対日付
        if '昨日' in text:
            from datetime import timedelta
            return date.today() - timedelta(days=1)
        if '一昨日' in text:
            from datetime import timedelta
            return date.today() - timedelta(days=2)

        return None

    @staticmethod
    def _extract_sub_account(text: str) -> str:
        """テキストから取引先名を抽出"""
        # 「A社」「株式会社○○」
        m = re.search(r"「(.+?)」", text)
        if m:
            return m.group(1)
        m = re.search(r"([A-Za-zＡ-Ｚ]+社)", text)
        if m:
            return m.group(1)
        m = re.search(r"(株式会社\S+|有限会社\S+|\S+株式会社)", text)
        if m:
            return m.group(1)
        return ""

    @staticmethod
    def _detect_payment_method(text: str) -> str:
        """テキストから支払方法を検出"""
        if re.search(r'(現金|キャッシュ|cash)', text, re.IGNORECASE):
            return "cash"
        if re.search(r'(振込|口座|銀行|引き落とし|カード|クレジット)', text):
            return "bank"
        return "bank"  # デフォルトは銀行振込

    @staticmethod
    def _is_reduced_tax(text: str) -> bool:
        """軽減税率(8%)対象かどうかを判定"""
        reduced_keywords = [
            "食品", "飲料", "食料", "食材", "弁当", "おにぎり",
            "新聞", "定期購読",  # 週2回以上発行の新聞
            "テイクアウト", "持ち帰り",
        ]
        return any(kw in text for kw in reduced_keywords)

    @staticmethod
    def _build_description(tmpl: JournalTemplate, text: str, sub: str) -> str:
        """仕訳の摘要を生成"""
        desc = tmpl.description
        if sub:
            desc = f"{sub} {desc}"
        return desc

    @staticmethod
    def _format_entry_summary(entry: JournalEntry) -> str:
        """仕訳の要約文を生成"""
        lines_desc: list[str] = []
        for ln in entry.lines:
            if ln.debit > 0:
                lines_desc.append(f"(借) {ln.account.name} {ln.debit:,}")
            else:
                lines_desc.append(f"(貸) {ln.account.name} {ln.credit:,}")
        return f"【{entry.description}】\n" + "\n".join(lines_desc)

    def summary_text(self) -> str:
        """現在の帳簿サマリ"""
        pl = self.get_pl()
        entries = self.ledger.entries
        lines = [
            f"仕訳件数: {len(entries)}件",
            f"売上高: {pl['売上高']['total']:,}円",
            f"売上原価: {pl['売上原価']['total']:,}円",
            f"売上総利益: {pl['売上総利益']:,}円",
            f"販管費: {pl['販管費']['total']:,}円",
            f"営業利益: {pl['営業利益']:,}円",
            f"経常利益: {pl['経常利益']:,}円",
            f"当期純利益: {pl['当期純利益']:,}円",
        ]
        return "\n".join(lines)
