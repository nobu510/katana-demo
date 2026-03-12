"""
資産管理エンジン（売掛金・固定資産・減価償却）

固定資産の取得→減価償却→除却/売却のライフサイクルを管理。
定額法・定率法の減価償却計算。
売掛金の管理・回収予測。

全関数はpure Python、DB非依存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Sequence

from .profit_engine import Project, CompanyConfig


# =====================================================================
# 固定資産
# =====================================================================

class DepreciationMethod(str, Enum):
    """減価償却方法"""
    STRAIGHT_LINE = "定額法"
    DECLINING_BALANCE = "定率法"


class AssetStatus(str, Enum):
    """固定資産ステータス"""
    ACTIVE = "使用中"
    DISPOSED = "除却済"
    SOLD = "売却済"


# 法定耐用年数テーブル (主要なもの)
USEFUL_LIFE_TABLE: dict[str, int] = {
    "建物": 22,           # 鉄骨造事務所
    "建物附属設備": 15,
    "構築物": 15,
    "機械装置": 10,
    "車両運搬具": 6,
    "工具器具備品": 5,     # PC・事務機器
    "ソフトウェア": 5,     # 自社利用
    "ソフトウェア(市販)": 3,
}

# 定率法の償却率テーブ ル (主要な耐用年数)
DECLINING_BALANCE_RATES: dict[int, float] = {
    3: 0.667,
    4: 0.500,
    5: 0.400,
    6: 0.333,
    8: 0.250,
    10: 0.200,
    15: 0.133,
    20: 0.100,
    22: 0.091,
}

# 少額減価償却資産の特例上限 (中小企業)
SMALL_ASSET_LIMIT = 300_000       # 30万円未満: 即時償却可
CONSUMABLE_ASSET_LIMIT = 100_000  # 10万円未満: 消耗品費扱い
LUMP_SUM_LIMIT = 200_000          # 20万円未満: 一括償却 (3年均等)


@dataclass
class FixedAsset:
    """固定資産"""
    name: str
    value: int                     # 取得価額
    annual_depreciation: int = 0   # 年間償却額 (自動計算)
    # 詳細情報
    asset_type: str = "工具器具備品"
    acquisition_date: date = field(default_factory=date.today)
    useful_life: int = 5           # 耐用年数
    method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    residual_value: int = 1        # 残存価額 (備忘価額1円)
    status: AssetStatus = AssetStatus.ACTIVE
    # 累積情報
    accumulated_depreciation: int = 0  # 減価償却累計額
    book_value: int = 0            # 帳簿価額 (取得価額 - 累計額)
    memo: str = ""


@dataclass
class DepreciationSchedule:
    """減価償却スケジュール (1年分)"""
    year: int
    beginning_value: int       # 期首帳簿価額
    depreciation: int          # 当期償却額
    ending_value: int          # 期末帳簿価額
    accumulated: int           # 累計償却額


@dataclass
class AccountsReceivable:
    """売掛金"""
    project_name: str
    client_name: str
    amount: int
    invoice_month: int
    expected_payment_month: int
    status: str                # "未請求" | "請求済" | "入金済"


# =====================================================================
# 資産管理エンジン
# =====================================================================

class AssetEngine:
    """資産管理エンジン"""

    def __init__(self, config: CompanyConfig):
        self.config = config

    # ----- 固定資産の取得 -----

    @staticmethod
    def acquire_asset(
        name: str,
        value: int,
        asset_type: str = "工具器具備品",
        acquisition_date: date | None = None,
        useful_life: int | None = None,
        method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
    ) -> FixedAsset:
        """固定資産を取得登録"""
        life = useful_life or USEFUL_LIFE_TABLE.get(asset_type, 5)
        acq_date = acquisition_date or date.today()

        asset = FixedAsset(
            name=name,
            value=value,
            asset_type=asset_type,
            acquisition_date=acq_date,
            useful_life=life,
            method=method,
            book_value=value,
        )

        # 年間償却額を計算
        asset.annual_depreciation = AssetEngine.calc_annual_depreciation(asset, year=1)

        return asset

    # ----- 減価償却計算 -----

    @staticmethod
    def calc_annual_depreciation(asset: FixedAsset, year: int = 1) -> int:
        """
        年間減価償却額を計算。

        定額法: (取得価額 - 残存価額) / 耐用年数
        定率法: 期首帳簿価額 × 償却率 (保証額チェック付き)
        """
        if asset.status != AssetStatus.ACTIVE:
            return 0
        if asset.book_value <= asset.residual_value:
            return 0

        depreciable = asset.value - asset.residual_value

        if asset.method == DepreciationMethod.STRAIGHT_LINE:
            annual = depreciable // asset.useful_life
            # 最終年: 端数を調整して残存価額ぴったりにする
            remaining = asset.book_value - asset.residual_value
            if remaining <= annual + asset.useful_life:
                # 端数で残りが1年分+α以下なら全額償却
                return remaining
            return min(annual, remaining)

        else:  # 定率法
            rate = DECLINING_BALANCE_RATES.get(asset.useful_life, 1.0 / asset.useful_life * 2)
            # 保証額 = 取得価額 × 保証率 (簡易: 耐用年数末期は定額に切替)
            guarantee = depreciable // asset.useful_life
            declining = int(asset.book_value * rate)

            if declining < guarantee:
                # 定額法に切替 (改定取得価額方式)
                remaining = asset.book_value - asset.residual_value
                years_left = max(1, asset.useful_life - year + 1)
                return remaining // years_left

            return min(declining, asset.book_value - asset.residual_value)

    @staticmethod
    def depreciation_schedule(asset: FixedAsset) -> list[DepreciationSchedule]:
        """
        耐用年数全期間の減価償却スケジュールを生成。
        """
        schedule: list[DepreciationSchedule] = []
        book = asset.value
        accumulated = 0

        for year in range(1, asset.useful_life + 1):
            # 仮の資産状態で計算
            temp = FixedAsset(
                name=asset.name,
                value=asset.value,
                useful_life=asset.useful_life,
                method=asset.method,
                residual_value=asset.residual_value,
                book_value=book,
            )
            dep = AssetEngine.calc_annual_depreciation(temp, year)
            accumulated += dep
            ending = book - dep

            schedule.append(DepreciationSchedule(
                year=year,
                beginning_value=book,
                depreciation=dep,
                ending_value=ending,
                accumulated=accumulated,
            ))

            book = ending
            if book <= asset.residual_value:
                break

        return schedule

    @staticmethod
    def process_annual_depreciation(asset: FixedAsset, year: int = 1) -> int:
        """1年分の減価償却を実行し、資産の帳簿価額を更新"""
        dep = AssetEngine.calc_annual_depreciation(asset, year)
        asset.accumulated_depreciation += dep
        asset.book_value = asset.value - asset.accumulated_depreciation
        return dep

    # ----- 少額資産判定 -----

    @staticmethod
    def classify_asset(value: int) -> str:
        """
        取得価額から資産の会計処理方法を判定。

        Returns:
            "消耗品費": 10万円未満 → 費用処理
            "即時償却": 30万円未満 → 中小企業特例で即時償却
            "一括償却": 20万円未満 → 3年均等償却
            "通常償却": 上記以外 → 耐用年数で償却
        """
        if value < CONSUMABLE_ASSET_LIMIT:
            return "消耗品費"
        if value < LUMP_SUM_LIMIT:
            return "一括償却"
        if value < SMALL_ASSET_LIMIT:
            return "即時償却"
        return "通常償却"

    # ----- 除却・売却 -----

    @staticmethod
    def dispose_asset(asset: FixedAsset) -> dict:
        """固定資産の除却"""
        loss = asset.book_value - asset.residual_value
        asset.status = AssetStatus.DISPOSED
        return {
            "asset": asset.name,
            "book_value": asset.book_value,
            "disposal_loss": max(0, loss),
        }

    @staticmethod
    def sell_asset(asset: FixedAsset, sale_price: int) -> dict:
        """固定資産の売却"""
        gain_or_loss = sale_price - asset.book_value
        asset.status = AssetStatus.SOLD
        return {
            "asset": asset.name,
            "book_value": asset.book_value,
            "sale_price": sale_price,
            "gain": max(0, gain_or_loss),
            "loss": max(0, -gain_or_loss),
        }

    # ----- 売掛金管理 -----

    def accounts_receivable(
        self,
        projects: Sequence[Project],
        current_month: int,
    ) -> list[AccountsReceivable]:
        """売掛金一覧"""
        result = []
        for p in projects:
            if current_month < p.contract_month:
                continue
            if current_month >= p.payment_month:
                status = "入金済"
            elif current_month >= p.invoice_month:
                status = "請求済"
            else:
                status = "未請求"

            result.append(AccountsReceivable(
                project_name=p.project_name,
                client_name=p.name,
                amount=p.revenue,
                invoice_month=p.invoice_month,
                expected_payment_month=p.payment_month,
                status=status,
            ))
        return result

    def total_receivable(
        self,
        projects: Sequence[Project],
        current_month: int,
    ) -> int:
        """未回収売掛金合計"""
        return sum(
            p.revenue
            for p in projects
            if current_month >= p.invoice_month and current_month < p.payment_month
        )

    # ----- 集計 -----

    def depreciation_total(self, assets: Sequence[FixedAsset]) -> int:
        """年間減価償却費合計"""
        return sum(a.annual_depreciation for a in assets if a.status == AssetStatus.ACTIVE)

    def net_asset_value(self, assets: Sequence[FixedAsset]) -> int:
        """固定資産簿価合計"""
        return sum(a.book_value for a in assets if a.status == AssetStatus.ACTIVE)

    @staticmethod
    def asset_summary(assets: Sequence[FixedAsset]) -> dict:
        """固定資産サマリ"""
        active = [a for a in assets if a.status == AssetStatus.ACTIVE]
        by_type: dict[str, dict] = {}
        for a in active:
            t = a.asset_type
            if t not in by_type:
                by_type[t] = {"count": 0, "acquisition_total": 0, "book_total": 0}
            by_type[t]["count"] += 1
            by_type[t]["acquisition_total"] += a.value
            by_type[t]["book_total"] += a.book_value

        return {
            "total_count": len(active),
            "total_acquisition": sum(a.value for a in active),
            "total_book_value": sum(a.book_value for a in active),
            "total_depreciation": sum(a.accumulated_depreciation for a in active),
            "by_type": by_type,
        }
