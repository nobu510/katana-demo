"""
売上管理エンジン
売上計上・売上分析（日次/月次/年次）・目標管理を提供。

全関数はpure Python、DB非依存。
採番: SL001-C001
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Sequence

from .numbering_engine import NumberingState, generate_sales_id


# =====================================================================
# データ型
# =====================================================================

class SalesStatus(str, Enum):
    """売上ステータス"""
    CONTRACTED = "契約済"
    DELIVERED = "納品済"
    INVOICED = "請求済"
    COLLECTED = "入金済"
    CANCELLED = "キャンセル"


@dataclass
class SalesRecord:
    """売上レコード"""
    id: str                    # SL001-C001 形式
    company_id: str            # C001
    project_id: str = ""       # P001-C001
    client_name: str = ""
    product_name: str = ""
    category: str = ""         # 商品カテゴリ
    amount: int = 0            # 税抜売上金額
    tax_amount: int = 0        # 消費税額
    total_amount: int = 0      # 税込金額
    cost: int = 0              # 原価
    sales_date: date = field(default_factory=date.today)
    invoice_date: date | None = None
    payment_date: date | None = None
    status: SalesStatus = SalesStatus.CONTRACTED
    staff_id: str = ""         # 担当者 S001-C001
    memo: str = ""


@dataclass
class SalesTarget:
    """売上目標"""
    year: int
    month: int                 # 1-12
    target_amount: int
    category: str = ""         # カテゴリ別目標 (空=全社)
    staff_id: str = ""         # 担当者別目標 (空=全社)


# =====================================================================
# 集計結果データ型
# =====================================================================

@dataclass
class SalesSummary:
    """売上集計結果"""
    total_amount: int
    total_tax: int
    total_cost: int
    gross_profit: int
    gross_margin: float
    count: int


@dataclass
class SalesTargetResult:
    """目標vs実績"""
    target: int
    actual: int
    achievement_rate: float
    gap: int                   # 未達額 (負=超過)


@dataclass
class SalesRanking:
    """売上ランキング項目"""
    key: str                   # 商品名/カテゴリ名/取引先名/担当者名
    amount: int
    count: int
    gross_profit: int
    share: float               # 構成比


# =====================================================================
# 売上管理エンジン
# =====================================================================

class SalesEngine:
    """
    売上管理エンジン
    売上計上・日次/月次/年次分析・目標管理・ランキングを提供。
    """

    def __init__(self, company_id: str = ""):
        self.company_id = company_id
        self._numbering_state = NumberingState()

    # ----- 採番 -----

    def create_sales_record(
        self,
        client_name: str,
        product_name: str,
        amount: int,
        sales_date: date | None = None,
        tax_rate: float = 0.10,
        cost: int = 0,
        project_id: str = "",
        category: str = "",
        staff_id: str = "",
    ) -> SalesRecord:
        """売上レコードを採番付きで作成"""
        nid, self._numbering_state = generate_sales_id(
            self._numbering_state, self.company_id
        )
        tax = int(amount * tax_rate)
        return SalesRecord(
            id=nid.id,
            company_id=self.company_id,
            project_id=project_id,
            client_name=client_name,
            product_name=product_name,
            category=category,
            amount=amount,
            tax_amount=tax,
            total_amount=amount + tax,
            cost=cost,
            sales_date=sales_date or date.today(),
            status=SalesStatus.CONTRACTED,
            staff_id=staff_id,
        )

    # ----- 集計 -----

    @staticmethod
    def summarize(records: Sequence[SalesRecord]) -> SalesSummary:
        """売上レコードを集計"""
        active = [r for r in records if r.status != SalesStatus.CANCELLED]
        total = sum(r.amount for r in active)
        tax = sum(r.tax_amount for r in active)
        cost = sum(r.cost for r in active)
        gp = total - cost
        return SalesSummary(
            total_amount=total,
            total_tax=tax,
            total_cost=cost,
            gross_profit=gp,
            gross_margin=gp / total if total else 0.0,
            count=len(active),
        )

    # ----- 期間フィルタ -----

    @staticmethod
    def filter_by_date(
        records: Sequence[SalesRecord],
        start: date,
        end: date,
    ) -> list[SalesRecord]:
        """日付範囲でフィルタ"""
        return [r for r in records if start <= r.sales_date <= end]

    @staticmethod
    def filter_by_month(
        records: Sequence[SalesRecord],
        year: int,
        month: int,
    ) -> list[SalesRecord]:
        """月でフィルタ"""
        return [r for r in records
                if r.sales_date.year == year and r.sales_date.month == month]

    @staticmethod
    def filter_by_year(
        records: Sequence[SalesRecord],
        year: int,
    ) -> list[SalesRecord]:
        """年でフィルタ"""
        return [r for r in records if r.sales_date.year == year]

    # ----- 日次/月次/年次集計 -----

    @staticmethod
    def daily_summary(
        records: Sequence[SalesRecord],
        start: date,
        end: date,
    ) -> list[dict]:
        """日次売上集計"""
        by_date: dict[str, list[SalesRecord]] = {}
        for r in records:
            if start <= r.sales_date <= end and r.status != SalesStatus.CANCELLED:
                key = r.sales_date.isoformat()
                by_date.setdefault(key, []).append(r)

        result: list[dict] = []
        current = start
        from datetime import timedelta
        while current <= end:
            key = current.isoformat()
            day_records = by_date.get(key, [])
            amount = sum(r.amount for r in day_records)
            result.append({
                "date": key,
                "amount": amount,
                "count": len(day_records),
            })
            current += timedelta(days=1)
        return result

    @staticmethod
    def monthly_summary(
        records: Sequence[SalesRecord],
        year: int,
    ) -> list[dict]:
        """月次売上集計 (1-12月)"""
        by_month: dict[int, int] = {m: 0 for m in range(1, 13)}
        counts: dict[int, int] = {m: 0 for m in range(1, 13)}

        for r in records:
            if r.sales_date.year == year and r.status != SalesStatus.CANCELLED:
                by_month[r.sales_date.month] += r.amount
                counts[r.sales_date.month] += 1

        return [
            {"month": m, "amount": by_month[m], "count": counts[m]}
            for m in range(1, 13)
        ]

    @staticmethod
    def yearly_summary(
        records: Sequence[SalesRecord],
    ) -> list[dict]:
        """年次売上集計"""
        by_year: dict[int, dict] = {}
        for r in records:
            if r.status == SalesStatus.CANCELLED:
                continue
            y = r.sales_date.year
            if y not in by_year:
                by_year[y] = {"amount": 0, "count": 0}
            by_year[y]["amount"] += r.amount
            by_year[y]["count"] += 1

        return [
            {"year": y, "amount": d["amount"], "count": d["count"]}
            for y, d in sorted(by_year.items())
        ]

    # ----- ランキング・分析 -----

    @staticmethod
    def _ranking(
        records: Sequence[SalesRecord],
        key_fn,
    ) -> list[SalesRanking]:
        """汎用ランキング生成"""
        active = [r for r in records if r.status != SalesStatus.CANCELLED]
        total_all = sum(r.amount for r in active)
        by_key: dict[str, dict] = {}
        for r in active:
            k = key_fn(r)
            if k not in by_key:
                by_key[k] = {"amount": 0, "count": 0, "gp": 0}
            by_key[k]["amount"] += r.amount
            by_key[k]["count"] += 1
            by_key[k]["gp"] += r.amount - r.cost

        result = [
            SalesRanking(
                key=k,
                amount=d["amount"],
                count=d["count"],
                gross_profit=d["gp"],
                share=d["amount"] / total_all if total_all else 0.0,
            )
            for k, d in by_key.items()
        ]
        return sorted(result, key=lambda x: x.amount, reverse=True)

    @staticmethod
    def ranking_by_product(records: Sequence[SalesRecord]) -> list[SalesRanking]:
        """商品別売上ランキング"""
        return SalesEngine._ranking(records, lambda r: r.product_name or "未設定")

    @staticmethod
    def ranking_by_category(records: Sequence[SalesRecord]) -> list[SalesRanking]:
        """カテゴリ別売上ランキング"""
        return SalesEngine._ranking(records, lambda r: r.category or "未分類")

    @staticmethod
    def ranking_by_client(records: Sequence[SalesRecord]) -> list[SalesRanking]:
        """取引先別売上ランキング"""
        return SalesEngine._ranking(records, lambda r: r.client_name or "未設定")

    @staticmethod
    def ranking_by_staff(records: Sequence[SalesRecord]) -> list[SalesRanking]:
        """担当者別売上ランキング"""
        return SalesEngine._ranking(records, lambda r: r.staff_id or "未設定")

    # ----- 目標管理 -----

    @staticmethod
    def calc_target_achievement(
        records: Sequence[SalesRecord],
        targets: Sequence[SalesTarget],
        year: int,
        month: int,
    ) -> list[SalesTargetResult]:
        """月次目標vs実績を計算"""
        month_records = [
            r for r in records
            if r.sales_date.year == year
            and r.sales_date.month == month
            and r.status != SalesStatus.CANCELLED
        ]
        month_targets = [t for t in targets if t.year == year and t.month == month]

        results: list[SalesTargetResult] = []
        for t in month_targets:
            if t.category:
                actual = sum(r.amount for r in month_records if r.category == t.category)
            elif t.staff_id:
                actual = sum(r.amount for r in month_records if r.staff_id == t.staff_id)
            else:
                actual = sum(r.amount for r in month_records)

            results.append(SalesTargetResult(
                target=t.target_amount,
                actual=actual,
                achievement_rate=actual / t.target_amount if t.target_amount else 0.0,
                gap=t.target_amount - actual,
            ))
        return results

    @staticmethod
    def calc_ytd_achievement(
        records: Sequence[SalesRecord],
        targets: Sequence[SalesTarget],
        year: int,
        up_to_month: int,
    ) -> SalesTargetResult:
        """年度累計の目標vs実績"""
        ytd_target = sum(
            t.target_amount for t in targets
            if t.year == year and t.month <= up_to_month and not t.category and not t.staff_id
        )
        ytd_actual = sum(
            r.amount for r in records
            if r.sales_date.year == year
            and r.sales_date.month <= up_to_month
            and r.status != SalesStatus.CANCELLED
        )
        return SalesTargetResult(
            target=ytd_target,
            actual=ytd_actual,
            achievement_rate=ytd_actual / ytd_target if ytd_target else 0.0,
            gap=ytd_target - ytd_actual,
        )

    # ----- 前年比較 -----

    @staticmethod
    def year_over_year(
        records: Sequence[SalesRecord],
        year: int,
        month: int,
    ) -> dict:
        """前年同月比"""
        this_month = [
            r for r in records
            if r.sales_date.year == year and r.sales_date.month == month
            and r.status != SalesStatus.CANCELLED
        ]
        last_month = [
            r for r in records
            if r.sales_date.year == year - 1 and r.sales_date.month == month
            and r.status != SalesStatus.CANCELLED
        ]
        this_total = sum(r.amount for r in this_month)
        last_total = sum(r.amount for r in last_month)
        return {
            "current": this_total,
            "previous": last_total,
            "change": this_total - last_total,
            "change_rate": (this_total - last_total) / last_total if last_total else 0.0,
        }
