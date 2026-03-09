"""
企業モデル＆JSONファイルストレージ
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent.parent / "data"
COMPANIES_FILE = DATA_DIR / "companies.json"


@dataclass
class Company:
    """登録企業"""
    id: str
    name: str
    industry: str           # "it" | "retail" | ...
    fixed_cost_monthly: int
    staff_count: int
    tax_rate: float = 0.30
    annual_target: int = 0
    target_margin: float = 0.0
    categories: list[dict] = field(default_factory=list)  # 業種別カテゴリ/部門
    staff: list[dict] = field(default_factory=list)       # 社員一覧
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Company:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CompanyStore:
    """JSONファイルベースの企業ストレージ"""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not COMPANIES_FILE.exists():
            self._save_all({})

    def _load_all(self) -> dict[str, dict]:
        try:
            return json.loads(COMPANIES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_all(self, data: dict[str, dict]) -> None:
        COMPANIES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create(self, company: Company) -> Company:
        data = self._load_all()
        data[company.id] = company.to_dict()
        self._save_all(data)
        return company

    def get(self, company_id: str) -> Company | None:
        data = self._load_all()
        if company_id in data:
            return Company.from_dict(data[company_id])
        return None

    def list_all(self) -> list[Company]:
        data = self._load_all()
        return [Company.from_dict(v) for v in data.values()]

    def delete(self, company_id: str) -> bool:
        data = self._load_all()
        if company_id in data:
            del data[company_id]
            self._save_all(data)
            return True
        return False

    @staticmethod
    def generate_id() -> str:
        return uuid.uuid4().hex[:12]
