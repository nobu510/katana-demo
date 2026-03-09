"""
資産管理エンジン（売掛金・固定資産）
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from .profit_engine import Project, CompanyConfig


@dataclass
class FixedAsset:
    name: str
    value: int
    annual_depreciation: int


@dataclass
class AccountsReceivable:
    project_name: str
    client_name: str
    amount: int
    invoice_month: int
    expected_payment_month: int
    status: str  # "未請求" | "請求済" | "入金済"


class AssetEngine:
    """資産管理"""

    def __init__(self, config: CompanyConfig):
        self.config = config

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

    def depreciation_total(self, assets: Sequence[FixedAsset]) -> int:
        """年間減価償却費合計"""
        return sum(a.annual_depreciation for a in assets)

    def net_asset_value(self, assets: Sequence[FixedAsset]) -> int:
        """固定資産簿価合計"""
        return sum(a.value - a.annual_depreciation for a in assets)
