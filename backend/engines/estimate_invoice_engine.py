"""
見積・請求エンジン
見積書作成 → 受注 → 請求書発行 → 入金消込の全フローを管理。

インボイス制度対応（登録番号・税率区分）。
採番: 見積 Q001-C001, 請求 IV001-C001
全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Sequence

from .numbering_engine import NumberingState, generate_estimate_id, generate_invoice_id
from .tax_engine import TaxRate, CONSUMPTION_TAX_RATES, calc_invoice_tax, InvoiceLineItem


# =====================================================================
# データ型
# =====================================================================

class EstimateStatus(str, Enum):
    """見積ステータス"""
    DRAFT = "下書き"
    SENT = "送付済"
    ACCEPTED = "受注"
    REJECTED = "失注"
    EXPIRED = "期限切れ"


class InvoiceStatus(str, Enum):
    """請求ステータス"""
    DRAFT = "下書き"
    ISSUED = "発行済"
    SENT = "送付済"
    PARTIAL_PAID = "一部入金"
    PAID = "入金済"
    OVERDUE = "延滞"
    CANCELLED = "取消"


@dataclass
class LineItem:
    """明細行"""
    description: str
    quantity: float = 1.0
    unit: str = "式"           # "式", "個", "時間", "人月" etc.
    unit_price: int = 0
    amount: int = 0            # quantity * unit_price (自動計算可)
    tax_rate: TaxRate = TaxRate.STANDARD


@dataclass
class Estimate:
    """見積書"""
    id: str                    # Q001-C001
    company_id: str            # C001
    project_id: str = ""       # P001-C001
    client_name: str = ""
    client_address: str = ""
    subject: str = ""          # 件名
    items: list[LineItem] = field(default_factory=list)
    subtotal: int = 0          # 税抜小計
    tax_total: int = 0         # 消費税合計
    total: int = 0             # 税込合計
    issue_date: date = field(default_factory=date.today)
    valid_until: date | None = None   # 見積有効期限
    status: EstimateStatus = EstimateStatus.DRAFT
    notes: str = ""            # 備考
    invoice_id: str = ""       # 受注後に紐づく請求ID


@dataclass
class Invoice:
    """請求書"""
    id: str                    # IV001-C001
    company_id: str            # C001
    project_id: str = ""       # P001-C001
    estimate_id: str = ""      # Q001-C001 (元見積)
    client_name: str = ""
    client_address: str = ""
    subject: str = ""
    items: list[LineItem] = field(default_factory=list)
    subtotal: int = 0
    tax_total: int = 0
    total: int = 0
    issue_date: date = field(default_factory=date.today)
    due_date: date | None = None      # 支払期限
    status: InvoiceStatus = InvoiceStatus.DRAFT
    # インボイス制度
    invoice_registration_number: str = ""   # T + 13桁
    tax_summary: list[dict] = field(default_factory=list)  # 税率別集計
    # 入金消込
    payments: list[Payment] = field(default_factory=list)
    paid_amount: int = 0
    notes: str = ""


@dataclass
class Payment:
    """入金レコード"""
    payment_date: date
    amount: int
    method: str = ""           # "振込", "現金", "カード" etc.
    memo: str = ""


# =====================================================================
# 見積・請求エンジン
# =====================================================================

class EstimateInvoiceEngine:
    """
    見積 → 受注 → 請求 → 入金消込の全フローを管理。
    """

    def __init__(self, company_id: str = "", registration_number: str = ""):
        self.company_id = company_id
        self.registration_number = registration_number  # インボイス登録番号
        self._numbering_state = NumberingState()

    # ----- 見積書作成 -----

    def create_estimate(
        self,
        client_name: str,
        subject: str,
        items: list[LineItem],
        issue_date: date | None = None,
        valid_days: int = 30,
        project_id: str = "",
        notes: str = "",
    ) -> Estimate:
        """見積書を作成"""
        nid, self._numbering_state = generate_estimate_id(
            self._numbering_state, self.company_id
        )
        dt = issue_date or date.today()

        # 明細の金額計算
        for item in items:
            if item.amount == 0:
                item.amount = int(item.quantity * item.unit_price)

        subtotal = sum(item.amount for item in items)

        # インボイス制度準拠: 税率ごとに合算して消費税計算
        inv_items = [
            InvoiceLineItem(description=it.description, amount=it.amount, rate=it.tax_rate)
            for it in items
        ]
        tax_summaries = calc_invoice_tax(inv_items)
        tax_total = sum(s.tax_amount for s in tax_summaries)

        return Estimate(
            id=nid.id,
            company_id=self.company_id,
            project_id=project_id,
            client_name=client_name,
            subject=subject,
            items=items,
            subtotal=subtotal,
            tax_total=tax_total,
            total=subtotal + tax_total,
            issue_date=dt,
            valid_until=dt + timedelta(days=valid_days),
            status=EstimateStatus.DRAFT,
            notes=notes,
        )

    # ----- 見積→受注→請求 自動フロー -----

    def accept_estimate(self, estimate: Estimate) -> Estimate:
        """見積を受注にする"""
        estimate.status = EstimateStatus.ACCEPTED
        return estimate

    def estimate_to_invoice(
        self,
        estimate: Estimate,
        issue_date: date | None = None,
        payment_terms_days: int = 30,
    ) -> Invoice:
        """受注済み見積から請求書を自動生成"""
        nid, self._numbering_state = generate_invoice_id(
            self._numbering_state, self.company_id
        )
        dt = issue_date or date.today()

        # 税率別集計
        inv_items = [
            InvoiceLineItem(description=it.description, amount=it.amount, rate=it.tax_rate)
            for it in estimate.items
        ]
        tax_summaries = calc_invoice_tax(inv_items)
        tax_summary_dicts = [
            {
                "rate": s.rate.value,
                "rate_pct": s.rate_pct,
                "taxable_amount": s.taxable_amount,
                "tax_amount": s.tax_amount,
            }
            for s in tax_summaries
        ]

        invoice = Invoice(
            id=nid.id,
            company_id=self.company_id,
            project_id=estimate.project_id,
            estimate_id=estimate.id,
            client_name=estimate.client_name,
            client_address=estimate.client_address,
            subject=estimate.subject,
            items=list(estimate.items),
            subtotal=estimate.subtotal,
            tax_total=estimate.tax_total,
            total=estimate.total,
            issue_date=dt,
            due_date=dt + timedelta(days=payment_terms_days),
            status=InvoiceStatus.ISSUED,
            invoice_registration_number=self.registration_number,
            tax_summary=tax_summary_dicts,
        )

        # 見積に請求IDを紐づけ
        estimate.invoice_id = invoice.id

        return invoice

    # ----- 請求書直接作成 -----

    def create_invoice(
        self,
        client_name: str,
        subject: str,
        items: list[LineItem],
        issue_date: date | None = None,
        payment_terms_days: int = 30,
        project_id: str = "",
        notes: str = "",
    ) -> Invoice:
        """見積なしで請求書を直接作成"""
        nid, self._numbering_state = generate_invoice_id(
            self._numbering_state, self.company_id
        )
        dt = issue_date or date.today()

        for item in items:
            if item.amount == 0:
                item.amount = int(item.quantity * item.unit_price)

        subtotal = sum(item.amount for item in items)

        inv_items = [
            InvoiceLineItem(description=it.description, amount=it.amount, rate=it.tax_rate)
            for it in items
        ]
        tax_summaries = calc_invoice_tax(inv_items)
        tax_total = sum(s.tax_amount for s in tax_summaries)
        tax_summary_dicts = [
            {
                "rate": s.rate.value,
                "rate_pct": s.rate_pct,
                "taxable_amount": s.taxable_amount,
                "tax_amount": s.tax_amount,
            }
            for s in tax_summaries
        ]

        return Invoice(
            id=nid.id,
            company_id=self.company_id,
            project_id=project_id,
            client_name=client_name,
            subject=subject,
            items=items,
            subtotal=subtotal,
            tax_total=tax_total,
            total=subtotal + tax_total,
            issue_date=dt,
            due_date=dt + timedelta(days=payment_terms_days),
            status=InvoiceStatus.ISSUED,
            invoice_registration_number=self.registration_number,
            tax_summary=tax_summary_dicts,
            notes=notes,
        )

    # ----- 入金消込 -----

    @staticmethod
    def record_payment(
        invoice: Invoice,
        amount: int,
        payment_date: date | None = None,
        method: str = "振込",
        memo: str = "",
    ) -> Invoice:
        """入金を記録し、消込処理"""
        payment = Payment(
            payment_date=payment_date or date.today(),
            amount=amount,
            method=method,
            memo=memo,
        )
        invoice.payments.append(payment)
        invoice.paid_amount += amount

        if invoice.paid_amount >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.paid_amount > 0:
            invoice.status = InvoiceStatus.PARTIAL_PAID

        return invoice

    @staticmethod
    def check_overdue(invoice: Invoice, as_of: date | None = None) -> bool:
        """延滞チェック"""
        today = as_of or date.today()
        if invoice.due_date and today > invoice.due_date:
            if invoice.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
                invoice.status = InvoiceStatus.OVERDUE
                return True
        return False

    # ----- 集計・分析 -----

    @staticmethod
    def outstanding_invoices(
        invoices: Sequence[Invoice],
        as_of: date | None = None,
    ) -> list[Invoice]:
        """未入金請求書一覧"""
        return [
            inv for inv in invoices
            if inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT)
        ]

    @staticmethod
    def total_outstanding(invoices: Sequence[Invoice]) -> int:
        """未入金総額"""
        return sum(
            inv.total - inv.paid_amount
            for inv in invoices
            if inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT)
        )

    @staticmethod
    def aging_report(
        invoices: Sequence[Invoice],
        as_of: date | None = None,
    ) -> dict[str, int]:
        """売掛金エイジング分析"""
        today = as_of or date.today()
        aging = {"current": 0, "30days": 0, "60days": 0, "90days": 0, "over90": 0}

        for inv in invoices:
            if inv.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT):
                continue
            remaining = inv.total - inv.paid_amount
            if not inv.due_date or today <= inv.due_date:
                aging["current"] += remaining
            else:
                days_overdue = (today - inv.due_date).days
                if days_overdue <= 30:
                    aging["30days"] += remaining
                elif days_overdue <= 60:
                    aging["60days"] += remaining
                elif days_overdue <= 90:
                    aging["90days"] += remaining
                else:
                    aging["over90"] += remaining

        return aging

    @staticmethod
    def monthly_invoiced(
        invoices: Sequence[Invoice],
        year: int,
    ) -> list[dict]:
        """月次請求額集計"""
        by_month: dict[int, int] = {m: 0 for m in range(1, 13)}
        for inv in invoices:
            if inv.issue_date.year == year and inv.status != InvoiceStatus.CANCELLED:
                by_month[inv.issue_date.month] += inv.total
        return [{"month": m, "amount": by_month[m]} for m in range(1, 13)]

    # ----- トレーサビリティ -----

    @staticmethod
    def trace_estimate_to_payment(
        estimate: Estimate,
        invoices: Sequence[Invoice],
    ) -> dict:
        """見積→請求→入金の追跡"""
        linked_invoice = None
        for inv in invoices:
            if inv.estimate_id == estimate.id:
                linked_invoice = inv
                break

        return {
            "estimate_id": estimate.id,
            "estimate_status": estimate.status.value,
            "estimate_total": estimate.total,
            "invoice_id": linked_invoice.id if linked_invoice else None,
            "invoice_status": linked_invoice.status.value if linked_invoice else None,
            "invoice_total": linked_invoice.total if linked_invoice else 0,
            "paid_amount": linked_invoice.paid_amount if linked_invoice else 0,
            "remaining": (linked_invoice.total - linked_invoice.paid_amount) if linked_invoice else estimate.total,
        }
