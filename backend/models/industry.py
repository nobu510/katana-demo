"""
業種定義
各業種のメタ情報・入力フォーム定義・デフォルト値
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class FormField:
    """動的フォームの1フィールド"""
    key: str
    label: str
    type: str  # "text" | "number" | "select" | "staff_list" | "category_list"
    placeholder: str = ""
    default: str | int | float | None = None
    required: bool = False
    options: list[str] = field(default_factory=list)  # select用


@dataclass
class IndustryDef:
    """業種定義"""
    key: str
    label: str
    icon: str
    description: str
    template_class: str  # "ITCompanyTemplate" | "RetailTemplate" | etc.
    available: bool  # 実装済みかどうか
    default_fixed_cost: int
    default_tax_rate: float
    default_target_margin: float
    form_fields: list[FormField] = field(default_factory=list)
    sample_categories: list[dict] = field(default_factory=list)


INDUSTRIES: dict[str, IndustryDef] = {
    "it": IndustryDef(
        key="it",
        label="IT・ソフトウェア",
        icon="💻",
        description="受託開発・SaaS・コンサルティング",
        template_class="ITCompanyTemplate",
        available=True,
        default_fixed_cost=2_800_000,
        default_tax_rate=0.30,
        default_target_margin=0.35,
        form_fields=[
            FormField("project_name", "案件名", "text", "例: クラウド導入", required=True),
            FormField("client_name", "取引先", "text", "例: 株式会社アルファ", required=True),
            FormField("revenue", "受注額", "number", "例: 5000000", required=True),
            FormField("cost", "原価", "number", "例: 2000000", required=True),
            FormField("contract_month", "契約月", "select", options=[
                "4月", "5月", "6月", "7月", "8月", "9月",
                "10月", "11月", "12月", "1月", "2月", "3月",
            ]),
            FormField("invoice_month", "請求月", "select", options=[
                "4月", "5月", "6月", "7月", "8月", "9月",
                "10月", "11月", "12月", "1月", "2月", "3月",
            ]),
            FormField("payment_month", "入金月", "select", options=[
                "4月", "5月", "6月", "7月", "8月", "9月",
                "10月", "11月", "12月", "1月", "2月", "3月",
            ]),
            FormField("staff_assignments", "担当者", "staff_list", "担当者と工数"),
        ],
        sample_categories=[
            {"name": "受託開発", "example": "Webアプリ開発 500万〜"},
            {"name": "SaaS", "example": "月額課金サービス"},
            {"name": "コンサルティング", "example": "DX支援・AI導入"},
            {"name": "研修・教育", "example": "技術研修 1回30万〜"},
        ],
    ),
    "retail": IndustryDef(
        key="retail",
        label="小売・スーパー",
        icon="🏪",
        description="食品スーパー・ドラッグストア・専門店",
        template_class="RetailTemplate",
        available=True,
        default_fixed_cost=1_800_000,
        default_tax_rate=0.30,
        default_target_margin=0.15,
        form_fields=[
            FormField("dept_name", "部門名", "text", "例: 生鮮食品", required=True),
            FormField("monthly_revenue", "月間売上", "number", "例: 4200000", required=True),
            FormField("cost_ratio", "原価率(%)", "number", "例: 65", default=65, required=True),
            FormField("turnover_days", "在庫回転日数", "number", "例: 2", default=7),
            FormField("waste_rate", "廃棄率(%)", "number", "例: 5", default=0),
            FormField("staff_count", "担当者数", "number", "例: 3", default=2),
        ],
        sample_categories=[
            {"name": "生鮮食品", "revenue": 4200000, "cost_ratio": 65, "turnover": 2, "waste": 5.0},
            {"name": "惣菜・弁当", "revenue": 2800000, "cost_ratio": 55, "turnover": 1, "waste": 8.0},
            {"name": "日配品", "revenue": 1800000, "cost_ratio": 70, "turnover": 3, "waste": 3.0},
            {"name": "菓子・飲料", "revenue": 1500000, "cost_ratio": 72, "turnover": 7, "waste": 1.0},
            {"name": "日用品", "revenue": 900000, "cost_ratio": 68, "turnover": 14, "waste": 0},
            {"name": "酒類", "revenue": 800000, "cost_ratio": 75, "turnover": 10, "waste": 0},
        ],
    ),
    "restaurant": IndustryDef(
        key="restaurant",
        label="飲食・レストラン",
        icon="🍽️",
        description="レストラン・カフェ・居酒屋",
        template_class="RestaurantTemplate",
        available=False,
        default_fixed_cost=1_500_000,
        default_tax_rate=0.30,
        default_target_margin=0.20,
        sample_categories=[
            {"name": "ランチ", "example": "日替わり定食 800円〜"},
            {"name": "ディナー", "example": "コース 3000円〜"},
            {"name": "ドリンク", "example": "原価率20%"},
            {"name": "テイクアウト", "example": "弁当・惣菜"},
        ],
    ),
    "construction": IndustryDef(
        key="construction",
        label="建設・工事",
        icon="🏗️",
        description="建築・土木・リフォーム",
        template_class="ConstructionTemplate",
        available=False,
        default_fixed_cost=3_000_000,
        default_tax_rate=0.30,
        default_target_margin=0.25,
        sample_categories=[
            {"name": "新築工事", "example": "住宅 2000万〜"},
            {"name": "リフォーム", "example": "水回り 100万〜"},
            {"name": "外構工事", "example": "駐車場・フェンス"},
            {"name": "設備工事", "example": "電気・空調"},
        ],
    ),
    "manufacturing": IndustryDef(
        key="manufacturing",
        label="製造業",
        icon="🏭",
        description="部品製造・食品加工・組立",
        template_class="ManufacturingTemplate",
        available=False,
        default_fixed_cost=5_000_000,
        default_tax_rate=0.30,
        default_target_margin=0.20,
        sample_categories=[
            {"name": "部品製造", "example": "金属加工・樹脂成形"},
            {"name": "組立", "example": "ユニット組立"},
            {"name": "検査", "example": "品質検査"},
        ],
    ),
    "service": IndustryDef(
        key="service",
        label="サービス業",
        icon="🤝",
        description="人材・教育・コンサル・清掃",
        template_class="ServiceTemplate",
        available=False,
        default_fixed_cost=1_200_000,
        default_tax_rate=0.30,
        default_target_margin=0.30,
        sample_categories=[
            {"name": "人材派遣", "example": "月額40万/人〜"},
            {"name": "教育研修", "example": "1日10万〜"},
            {"name": "清掃・メンテナンス", "example": "月額定額"},
        ],
    ),
}
