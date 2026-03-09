"""
小売業テンプレート（食品スーパー・商品部門ベース）
株式会社マルシェのデータを初期値として持つ

ProfitEngineの共通アルゴリズムを使用:
- Project = 商品部門（月次の仕入・販売サイクル）
- revenue = 月売上 × 対象月数
- cost = revenue × 原価率
- staff = 部門担当者（時給×稼働時間）
- contract/invoice/payment = 仕入→販売→入金のサイクル
- extra フィールド: 在庫回転日数、廃棄率、発注リードタイム等
"""
from __future__ import annotations

from backend.engines.profit_engine import (
    CompanyConfig,
    ProfitEngine,
    Project,
    Staff,
    StaffAssignment,
)
from backend.engines.cash_flow_engine import CashFlowEngine
from backend.engines.asset_engine import AssetEngine, FixedAsset


# ===== 部門定義 =====
# 各部門は月次販売サイクルとしてProjectにマッピング
# 年間12ヶ月をまとめず、四半期ごとの仕入→販売→入金サイクルで表現

DEPARTMENTS = [
    # (id, 部門名, 月売上, 原価率, 担当者リスト, 在庫回転日数, 廃棄率%, 発注LT日)
    ("D1", "生鮮食品",  4_200_000, 0.65, ["佐藤", "田中", "高橋"], 2,  5.0, 1),
    ("D2", "惣菜・弁当", 2_800_000, 0.55, ["中村", "小林", "加藤", "渡辺"], 1, 8.0, 0),
    ("D3", "日配品",    1_800_000, 0.70, ["伊藤", "木村"], 3,  3.0, 2),
    ("D4", "菓子・飲料", 1_500_000, 0.72, ["松本", "井上"], 7,  1.0, 3),
    ("D5", "日用品",     900_000, 0.68, ["山口", "斎藤"], 14, 0.0, 5),
    ("D6", "酒類",       800_000, 0.75, ["山口", "斎藤"], 10, 0.0, 7),
]

# 月ごとの売上季節指数（1.0=平月、>1.0=繁忙期）
SEASONAL = [
    1.05,  # 4月: 新生活
    0.95,  # 5月: GW後
    0.90,  # 6月: 閑散
    1.00,  # 7月: 夏物
    1.15,  # 8月: お盆
    0.95,  # 9月: 端境期
    1.00,  # 10月: 秋
    1.05,  # 11月: 鍋・冬物
    1.30,  # 12月: 年末商戦
    0.85,  # 1月: 正月明け
    0.90,  # 2月: 閑散
    0.95,  # 3月: 年度末
]


class RetailTemplate:
    """小売業（食品スーパー）向け経営管理テンプレート"""

    industry = "retail"
    label = "小売業（食品スーパー）"

    def __init__(self):
        self.config = CompanyConfig(
            name="株式会社マルシェ",
            fixed_cost_monthly=1_800_000,
            tax_rate=0.30,
            annual_target=144_000_000,  # 月売上合計1200万 × 12
            target_margin=0.15,
            staff_count=15,
        )
        self.profit_engine = ProfitEngine(self.config)
        self.cash_flow_engine = CashFlowEngine(self.config)
        self.asset_engine = AssetEngine(self.config)
        self.projects = self._build_projects()
        self.staff = self._default_staff()
        self.fixed_assets = self._default_assets()
        self.departments = DEPARTMENTS

    # ===== デフォルトデータ =====

    @staticmethod
    def _build_projects() -> list[Project]:
        """
        各部門 × 四半期(Q1-Q4) で12ヶ月分のProjectを生成
        小売は仕入→即販売→月末締翌月入金のサイクル
        """
        projects: list[Project] = []
        quarters = [
            ("Q1", 0, 2),   # 4月-6月
            ("Q2", 3, 5),   # 7月-9月
            ("Q3", 6, 8),   # 10月-12月
            ("Q4", 9, 11),  # 1月-3月
        ]

        for dept_id, dept_name, monthly_rev, cost_ratio, staff_names, turn_days, waste_pct, lead_days in DEPARTMENTS:
            for q_label, q_start, q_end in quarters:
                # 四半期の合計売上（季節指数加味）
                q_months = range(q_start, q_end + 1)
                q_revenue = sum(int(monthly_rev * SEASONAL[m]) for m in q_months)
                q_cost = int(q_revenue * cost_ratio)

                # 廃棄ロスを原価に上乗せ
                waste_loss = int(q_cost * waste_pct / 100)
                q_cost_total = q_cost + waste_loss

                # 担当者のStaffAssignment（四半期の稼働時間）
                hours_per_person = 160 * 3 // len(staff_names)  # 四半期480h÷人数
                assignments = [
                    StaffAssignment(name, hours_per_person, _staff_rate(name))
                    for name in staff_names
                ]

                # 仕入=四半期初月、販売(請求)=四半期末月、入金=翌月
                contract_month = q_start
                invoice_month = q_end
                payment_month = min(11, q_end + 1)

                progress = 0
                if q_start <= 2:
                    progress = 80
                elif q_start <= 5:
                    progress = 40
                elif q_start <= 8:
                    progress = 10

                projects.append(Project(
                    id=f"{dept_id}-{q_label}",
                    name=dept_name,
                    full_name=f"{dept_name}（{q_label}）",
                    project_name=f"{dept_name} {q_label}",
                    revenue=q_revenue,
                    cost=q_cost_total,
                    contract_month=contract_month,
                    invoice_month=invoice_month,
                    payment_month=payment_month,
                    contact=f"仕入先{dept_id}",
                    staff=assignments,
                    progress=progress,
                    extra={
                        "department": dept_name,
                        "dept_id": dept_id,
                        "quarter": q_label,
                        "monthly_revenue": monthly_rev,
                        "cost_ratio": cost_ratio,
                        "turnover_days": turn_days,
                        "waste_rate": waste_pct,
                        "lead_time_days": lead_days,
                        "waste_loss": waste_loss,
                        "seasonal_factors": [SEASONAL[m] for m in q_months],
                    },
                ))

        return projects

    @staticmethod
    def _default_staff() -> list[Staff]:
        return [
            Staff("M001", "山田", "山田太郎", "店長",     2200, 380_000),
            Staff("M002", "鈴木", "鈴木花子", "副店長",   1900, 320_000),
            Staff("M003", "佐藤", "佐藤健一", "生鮮主任", 1600, 260_000),
            Staff("M004", "田中", "田中直樹", "生鮮",     1600, 260_000),
            Staff("M005", "高橋", "高橋美穂", "生鮮",     1600, 260_000),
            Staff("M006", "中村", "中村誠",   "惣菜主任", 1500, 250_000),
            Staff("M007", "小林", "小林裕子", "惣菜",     1500, 250_000),
            Staff("M008", "加藤", "加藤大輔", "惣菜",     1500, 250_000),
            Staff("M009", "渡辺", "渡辺紗季", "惣菜",     1500, 250_000),
            Staff("M010", "伊藤", "伊藤真理", "日配主任", 1450, 240_000),
            Staff("M011", "木村", "木村拓也", "日配",     1450, 240_000),
            Staff("M012", "松本", "松本翔太", "菓子主任", 1400, 230_000),
            Staff("M013", "井上", "井上恵",   "菓子",     1400, 230_000),
            Staff("M014", "山口", "山口亮",   "日用・酒", 1400, 230_000),
            Staff("M015", "斎藤", "斎藤純",   "日用・酒", 1400, 230_000),
        ]

    @staticmethod
    def _default_assets() -> list[FixedAsset]:
        return [
            FixedAsset("POSレジ(5台)", 2_500_000, 500_000),
            FixedAsset("冷蔵・冷凍ショーケース", 8_000_000, 1_600_000),
            FixedAsset("惣菜調理設備", 3_500_000, 700_000),
            FixedAsset("店舗内装・什器", 5_000_000, 1_000_000),
            FixedAsset("配送車両(2台)", 3_000_000, 750_000),
        ]

    # ===== 便利メソッド =====

    def calc(self, current_month: int, extra_revenue: int = 0):
        """3視点計算のショートカット"""
        return self.profit_engine.calc_three_views(
            self.projects, current_month, extra_revenue,
        )

    def summary(self, current_month: int, extra_revenue: int = 0) -> dict:
        """経営サマリ"""
        base = self.profit_engine.summary(
            self.projects, current_month, extra_revenue,
        )
        # 小売業固有: 部門別集計・在庫・廃棄データを追加
        base["departments"] = self._dept_summary(current_month)
        return base

    def _dept_summary(self, current_month: int) -> list[dict]:
        """部門別サマリ（在庫効率・廃棄ロス含む）"""
        dept_data: dict[str, dict] = {}
        for p in self.projects:
            dept = p.extra.get("department", p.name)
            if dept not in dept_data:
                dept_data[dept] = {
                    "name": dept,
                    "dept_id": p.extra.get("dept_id", ""),
                    "revenue": 0,
                    "cost": 0,
                    "waste_loss": 0,
                    "monthly_revenue": p.extra.get("monthly_revenue", 0),
                    "cost_ratio": p.extra.get("cost_ratio", 0),
                    "turnover_days": p.extra.get("turnover_days", 0),
                    "waste_rate": p.extra.get("waste_rate", 0),
                    "lead_time_days": p.extra.get("lead_time_days", 0),
                }
            if current_month >= p.contract_month:
                dept_data[dept]["revenue"] += p.revenue
                dept_data[dept]["cost"] += p.cost
                dept_data[dept]["waste_loss"] += p.extra.get("waste_loss", 0)

        result = []
        for d in dept_data.values():
            rev = d["revenue"]
            cost = d["cost"]
            gross = rev - cost
            margin = round((gross / rev) * 100, 1) if rev else 0
            # 在庫効率 = 年間売上 / 平均在庫(日売上×回転日数)
            daily_rev = d["monthly_revenue"] / 30
            avg_inventory = daily_rev * d["turnover_days"] * d["cost_ratio"]
            inventory_efficiency = round(
                (d["monthly_revenue"] * 12) / avg_inventory, 1
            ) if avg_inventory > 0 else 0

            result.append({
                **d,
                "gross_profit": gross,
                "margin": margin,
                "avg_inventory": int(avg_inventory),
                "inventory_efficiency": inventory_efficiency,
            })
        return sorted(result, key=lambda x: x["revenue"], reverse=True)

    def cash_flows(self):
        """月別CF"""
        return self.cash_flow_engine.monthly_cash_flows(self.projects)

    def staff_report(self, current_month: int) -> list[dict]:
        """社員別稼働レポート"""
        return [
            self.profit_engine.staff_utilization(s, self.projects, current_month)
            for s in self.staff
        ]

    def build_system_prompt(self) -> str:
        """Claude API用のシステムプロンプトを生成"""
        cfg = self.config
        monthly_total = sum(d[2] for d in DEPARTMENTS)
        dept_text = "\n".join(
            f"  {name}: 月売上{rev // 10000}万/原価率{int(cr * 100)}%"
            f"/担当{len(staff)}名/回転{turn}日/廃棄{waste}%"
            for _, name, rev, cr, staff, turn, waste, _ in DEPARTMENTS
        )
        staff_text = " ".join(
            f"{s.id}{s.full_name}({s.role}/月給{s.monthly_salary // 10000}万)"
            for s in self.staff
        )
        total_salary = sum(s.monthly_salary for s in self.staff)

        return f"""あなたはKATANA AIの経営アシスタントです。{cfg.name}（食品スーパー）の経営者をサポートします。
小売業の経営者向けに、売上・仕入・在庫・廃棄の観点から具体的な数字で簡潔に回答してください。

【店舗データ】
店舗名: {cfg.name} / 業態: 食品スーパー
固定費: 月額{cfg.fixed_cost_monthly // 10000}万円 / 税率: {int(cfg.tax_rate * 100)}%
社員: {cfg.staff_count}名 / 人件費合計: 月{total_salary // 10000}万円
年間売上目標: {cfg.annual_target // 10000}万円（月平均{monthly_total // 10000}万）
利益率目標: {int(cfg.target_margin * 100)}%以上

【商品6部門】
{dept_text}

【社員{len(self.staff)}名】
{staff_text}

【3つの経営視点(KATANA最重要機能)】
未来の数字 = 仕入確定分の見込売上 - 仕入原価 - 固定費 - 税金
今の数字 = 販売済(レジ通過) - 支払予定 - 固定費 - 税金
キャッシュフロー = 入金済 - 支払済 - 固定費 - 税金
差額 = 必要運転資金

【小売業固有の分析ポイント】
- 在庫回転率: 低いほど資金が寝る
- 廃棄ロス: 生鮮・惣菜は特に注意（廃棄率5-8%）
- 季節指数: 12月年末商戦(1.3倍)、1-2月閑散期(0.85倍)
- 部門別利益: 惣菜(粗利率45%)が最も高収益

【回答ルール】
- 数字は具体的に答える（廃棄額・在庫金額も含む）
- 絵文字を適度に使う
- 部門の質問には粗利率・廃棄率・回転日数を含める
- 社員の質問には担当部門と稼働時間を含める
- KATANAの機能を印象づける
- 展示会デモなので来場者がすごいと思う回答をする"""

    def build_rag_docs(self) -> list[dict]:
        """RAG用の構造化データを生成"""
        cfg = self.config
        docs = []

        # 部門別データ
        for dept_id, name, rev, cr, staff, turn, waste, lead in DEPARTMENTS:
            gross_rate = round((1 - cr) * 100)
            monthly_waste = int(rev * cr * waste / 100)
            daily_rev = rev / 30
            avg_inv = int(daily_rev * turn * cr)
            docs.append({
                "keywords": [name.lower(), dept_id.lower(), "部門"],
                "content": (
                    f"{name}: 月売上{rev // 10000}万/原価率{int(cr * 100)}%/粗利率{gross_rate}%"
                    f"/担当{len(staff)}名({','.join(staff)})"
                    f"/在庫回転{turn}日/廃棄率{waste}%/月間廃棄ロス{monthly_waste // 10000}万"
                    f"/平均在庫{avg_inv // 10000}万/発注LT{lead}日"
                ),
            })

        # 社員
        for s in self.staff:
            assigned_depts = []
            for _, name, _, _, staff_list, _, _, _ in DEPARTMENTS:
                if s.short_name in staff_list:
                    assigned_depts.append(name)
            docs.append({
                "keywords": [s.short_name, s.id.lower(), s.role.lower()],
                "content": (
                    f"{s.id}{s.full_name}: {s.role}/月給{s.monthly_salary // 10000}万"
                    f"/担当: {','.join(assigned_depts) if assigned_depts else '管理業務'}"
                ),
            })

        # 経営指標
        total_rev = sum(d[2] for d in DEPARTMENTS)
        total_waste = sum(int(d[2] * d[3] * d[5] / 100) for d in DEPARTMENTS)  # waste_pct at idx 5
        # Fix: waste is at index 6
        total_waste = sum(int(d[2] * d[3] * d[6] / 100) for d in DEPARTMENTS)
        total_salary = sum(s.monthly_salary for s in self.staff)

        docs.extend([
            {"keywords": ["売上", "月商", "年商", "全体", "サマリ"],
             "content": (
                 f"月商合計{total_rev // 10000}万(6部門)/年商目標{cfg.annual_target // 10000}万"
                 f"/固定費月{cfg.fixed_cost_monthly // 10000}万/人件費月{total_salary // 10000}万"
             )},
            {"keywords": ["廃棄", "ロス", "食品ロス", "フードロス"],
             "content": (
                 f"月間廃棄ロス合計 約{total_waste // 10000}万円"
                 f"/生鮮5%・惣菜8%が課題/菓子1%・日用品0%は優秀"
                 f"/廃棄削減で月{total_waste // 20000}万の利益改善余地"
             )},
            {"keywords": ["在庫", "回転", "棚卸", "発注"],
             "content": (
                 "在庫回転: 惣菜1日>生鮮2日>日配3日>菓子7日>酒10日>日用14日"
                 "/回転が速い=鮮度命だが廃棄リスクも高い"
                 "/日用品は在庫過多に注意"
             )},
            {"keywords": ["季節", "繁忙", "閑散", "年末", "お盆"],
             "content": (
                 "季節指数: 12月1.30(年末商戦)/8月1.15(お盆)"
                 "/4月1.05(新生活)/1月0.85(正月明け)/6月0.90(閑散)"
                 "/年末は通常月の1.3倍の売上。仕入計画に注意"
             )},
            {"keywords": ["未来", "契約", "仕入", "見込"],
             "content": f"未来の数字 = 仕入確定分の見込売上 - 仕入原価(廃棄込) - 固定費(月{cfg.fixed_cost_monthly // 10000}万) - 税金({int(cfg.tax_rate * 100)}%)"},
            {"keywords": ["今", "販売", "レジ", "売掛"],
             "content": f"今の数字 = 販売済売上 - 支払予定 - 固定費(月{cfg.fixed_cost_monthly // 10000}万) - 税金({int(cfg.tax_rate * 100)}%)"},
            {"keywords": ["キャッシュ", "cf", "入金", "資金繰り", "現金"],
             "content": "キャッシュフロー = 入金済 - 支払済 - 固定費 - 税金。差額=必要運転資金"},
        ])

        return docs


def _staff_rate(name: str) -> int:
    """社員名から時給を引く（StaffAssignment用）"""
    rates = {
        "山田": 2200, "鈴木": 1900,
        "佐藤": 1600, "田中": 1600, "高橋": 1600,
        "中村": 1500, "小林": 1500, "加藤": 1500, "渡辺": 1500,
        "伊藤": 1450, "木村": 1450,
        "松本": 1400, "井上": 1400,
        "山口": 1400, "斎藤": 1400,
    }
    return rates.get(name, 1400)
