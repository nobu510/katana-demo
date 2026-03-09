"""
IT企業テンプレート（案件・工数ベース）
株式会社J.NOVAのデータを初期値として持つ
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


class ITCompanyTemplate:
    """IT企業向け経営管理テンプレート"""

    industry = "IT"
    label = "IT企業（案件・工数ベース）"

    def __init__(self):
        self.config = CompanyConfig(
            name="株式会社J.NOVA",
            fixed_cost_monthly=2_800_000,
            tax_rate=0.30,
            annual_target=104_000_000,
            target_margin=0.35,
            staff_count=8,
        )
        self.profit_engine = ProfitEngine(self.config)
        self.cash_flow_engine = CashFlowEngine(self.config)
        self.asset_engine = AssetEngine(self.config)
        self.projects = self._default_projects()
        self.staff = self._default_staff()
        self.fixed_assets = self._default_assets()

    # ===== デフォルトデータ (J.NOVA) =====

    @staticmethod
    def _default_projects() -> list[Project]:
        return [
            Project(
                id="A", name="A社", full_name="株式会社アルファ",
                project_name="クラウド導入", revenue=4_800_000, cost=1_920_000,
                contract_month=0, invoice_month=1, payment_month=3,
                contact="田中太郎",
                staff=[
                    StaffAssignment("田中", 80, 3000),
                    StaffAssignment("佐藤", 40, 2800),
                ],
                progress=100,
            ),
            Project(
                id="B", name="B社", full_name="株式会社ベータ",
                project_name="AI研修", revenue=3_200_000, cost=960_000,
                contract_month=1, invoice_month=2, payment_month=4,
                contact="佐藤花子",
                staff=[
                    StaffAssignment("鈴木", 60, 3200),
                    StaffAssignment("高橋", 30, 2500),
                ],
                progress=85,
            ),
            Project(
                id="C", name="C社", full_name="株式会社ガンマ",
                project_name="SaaS開発", revenue=12_000_000, cost=4_800_000,
                contract_month=2, invoice_month=4, payment_month=6,
                contact="鈴木一郎",
                staff=[
                    StaffAssignment("田中", 200, 3000),
                    StaffAssignment("山本", 160, 3500),
                    StaffAssignment("中村", 120, 2800),
                ],
                progress=70,
            ),
            Project(
                id="D", name="D社", full_name="株式会社デルタ",
                project_name="DX支援", revenue=6_500_000, cost=2_600_000,
                contract_month=3, invoice_month=5, payment_month=7,
                contact="高橋次郎",
                staff=[
                    StaffAssignment("佐藤", 100, 2800),
                    StaffAssignment("高橋", 80, 2500),
                ],
                progress=55,
            ),
            Project(
                id="E", name="E社", full_name="株式会社イプシロン",
                project_name="セキュリティ", revenue=8_000_000, cost=3_200_000,
                contract_month=4, invoice_month=6, payment_month=8,
                contact="渡辺三郎",
                staff=[
                    StaffAssignment("鈴木", 120, 3200),
                    StaffAssignment("渡辺", 90, 3000),
                ],
                progress=40,
            ),
            Project(
                id="F", name="F社", full_name="株式会社ゼータ",
                project_name="データ分析", revenue=5_500_000, cost=2_200_000,
                contract_month=5, invoice_month=7, payment_month=9,
                contact="伊藤四郎",
                staff=[
                    StaffAssignment("山本", 80, 3500),
                    StaffAssignment("加藤", 60, 2600),
                ],
                progress=30,
            ),
            Project(
                id="G", name="G社", full_name="株式会社エータ",
                project_name="AI Agent開発", revenue=25_000_000, cost=10_000_000,
                contract_month=6, invoice_month=8, payment_month=10,
                contact="山本五郎",
                staff=[
                    StaffAssignment("田中", 300, 3000),
                    StaffAssignment("鈴木", 250, 3200),
                    StaffAssignment("山本", 200, 3500),
                    StaffAssignment("渡辺", 150, 3000),
                ],
                progress=20,
            ),
            Project(
                id="H", name="H社", full_name="株式会社シータ",
                project_name="研修20名", revenue=4_000_000, cost=1_200_000,
                contract_month=7, invoice_month=8, payment_month=10,
                contact="中村六郎",
                staff=[
                    StaffAssignment("高橋", 60, 2500),
                    StaffAssignment("加藤", 40, 2600),
                ],
                progress=15,
            ),
            Project(
                id="I", name="I社", full_name="株式会社イオタ",
                project_name="基幹連携", revenue=9_000_000, cost=3_600_000,
                contract_month=8, invoice_month=9, payment_month=11,
                contact="小林七郎",
                staff=[
                    StaffAssignment("佐藤", 150, 2800),
                    StaffAssignment("中村", 100, 2800),
                ],
                progress=10,
            ),
            Project(
                id="J", name="J社", full_name="株式会社カッパ",
                project_name="IoT開発", revenue=7_200_000, cost=2_880_000,
                contract_month=9, invoice_month=10, payment_month=11,
                contact="加藤八郎",
                staff=[
                    StaffAssignment("渡辺", 120, 3000),
                    StaffAssignment("加藤", 100, 2600),
                ],
                progress=5,
            ),
            Project(
                id="K", name="K社", full_name="株式会社ラムダ",
                project_name="AI監査", revenue=3_800_000, cost=1_520_000,
                contract_month=10, invoice_month=11, payment_month=11,
                contact="吉田九郎",
                staff=[
                    StaffAssignment("鈴木", 60, 3200),
                ],
                progress=0,
            ),
            Project(
                id="L", name="L社", full_name="株式会社ミュー",
                project_name="全社DX", revenue=15_000_000, cost=6_000_000,
                contract_month=11, invoice_month=11, payment_month=11,
                contact="佐々木十郎",
                staff=[
                    StaffAssignment("田中", 200, 3000),
                    StaffAssignment("山本", 180, 3500),
                ],
                progress=0,
            ),
        ]

    @staticmethod
    def _default_staff() -> list[Staff]:
        return [
            Staff("S001", "田中", "田中太郎", "シニアエンジニア", 3000, 450_000),
            Staff("S002", "佐藤", "佐藤花子", "プロジェクトマネージャー", 2800, 420_000),
            Staff("S003", "鈴木", "鈴木一郎", "AIエンジニア", 3200, 480_000),
            Staff("S004", "高橋", "高橋次郎", "ジュニアエンジニア", 2500, 350_000),
            Staff("S005", "山本", "山本五郎", "リードエンジニア", 3500, 520_000),
            Staff("S006", "渡辺", "渡辺三郎", "インフラエンジニア", 3000, 450_000),
            Staff("S007", "中村", "中村六郎", "デザイナー", 2800, 400_000),
            Staff("S008", "加藤", "加藤八郎", "テスター", 2600, 380_000),
        ]

    @staticmethod
    def _default_assets() -> list[FixedAsset]:
        return [
            FixedAsset("サーバー設備", 3_200_000, 800_000),
            FixedAsset("開発用PC(8台)", 2_400_000, 600_000),
            FixedAsset("ソフトウェアライセンス", 1_800_000, 900_000),
            FixedAsset("オフィス内装", 1_500_000, 300_000),
        ]

    # ===== 便利メソッド =====

    def calc(self, current_month: int, extra_revenue: int = 0):
        """3視点計算のショートカット"""
        return self.profit_engine.calc_three_views(
            self.projects, current_month, extra_revenue,
        )

    def summary(self, current_month: int, extra_revenue: int = 0) -> dict:
        """経営サマリ"""
        return self.profit_engine.summary(
            self.projects, current_month, extra_revenue,
        )

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
        projects_text = "\n".join(
            f"{p.name}({p.project_name}{p.revenue // 10000}万/原価{p.cost // 10000}万"
            f"/担当:{'+'.join(f'{s.name}{s.hours}h' for s in p.staff)}"
            f"/契約{cfg.fiscal_months[p.contract_month]}/請求{cfg.fiscal_months[p.invoice_month]}/入金{cfg.fiscal_months[p.payment_month]})"
            for p in self.projects
        )
        staff_text = " ".join(
            f"{s.id}{s.full_name}({s.role}/時給{s.hourly_rate}円/月給{s.monthly_salary // 10000}万)"
            for s in self.staff
        )

        return f"""あなたはKATANA AIの経営アシスタントです。{cfg.name}の経営者GOTOさんをサポートします。
会計知識がない経営者でも分かるように、具体的な数字で簡潔に回答してください。

【会社データ】
会社名: {cfg.name} / 固定費: 月額{cfg.fixed_cost_monthly // 10000}万円 / 税率: {int(cfg.tax_rate * 100)}% / 社員: {cfg.staff_count}名
年間売上目標: {cfg.annual_target // 10000}万円 / 利益率目標: {int(cfg.target_margin * 100)}%以上

【取引先{len(self.projects)}社】
{projects_text}

【社員{len(self.staff)}名(採番管理)】
{staff_text}

【3つの経営視点(KATANA最重要機能)】
未来の数字 = 契約済売上(請求前含む) - 原価 - 固定費 - 税金
今の数字 = 請求済売上 - 支払予定 - 日割固定費 - 税金
キャッシュフロー = 入金額 - 支払額 - 日割固定費 - 税金
差額 = 必要運転資金

【回答ルール】
- 数字は具体的に答える
- 絵文字を適度に使う
- 案件の質問には利益率と進捗と担当者を含める
- 社員の質問には稼働時間と時間利益と担当案件を含める
- 曖昧な質問にも3視点で答える
- KATANAの機能を印象づける
- 展示会デモなので来場者がすごいと思う回答をする"""

    def build_rag_docs(self) -> list[dict]:
        """RAG用の構造化データを生成"""
        cfg = self.config
        docs = []

        # 取引先
        for p in self.projects:
            margin = round((p.revenue - p.cost) / p.revenue * 100)
            staff_str = "+".join(f"{s.name}{s.hours}h" for s in p.staff)
            docs.append({
                "keywords": [
                    p.name.lower(), p.project_name.lower(),
                    *[s.name for s in p.staff],
                ],
                "content": (
                    f"{p.name}: {p.project_name}/売上{p.revenue // 10000}万"
                    f"/原価{p.cost // 10000}万/粗利{(p.revenue - p.cost) // 10000}万"
                    f"(利益率{margin}%)/担当:{staff_str}"
                    f"/契約{cfg.fiscal_months[p.contract_month]}"
                    f"/請求{cfg.fiscal_months[p.invoice_month]}"
                    f"/入金{cfg.fiscal_months[p.payment_month]}"
                ),
            })

        # 社員
        for s in self.staff:
            total_hrs = 0
            project_names = []
            for p in self.projects:
                for sa in p.staff:
                    if sa.name == s.short_name:
                        total_hrs += sa.hours
                        project_names.append(f"{p.name}{sa.hours}h")
            docs.append({
                "keywords": [s.short_name, s.id.lower(), s.role.lower()],
                "content": (
                    f"{s.id}{s.full_name}: {s.role}/時給{s.hourly_rate}円"
                    f"/月給{s.monthly_salary // 10000}万"
                    f"/担当: {','.join(project_names)}(計{total_hrs}h)"
                ),
            })

        # 経営視点
        docs.extend([
            {"keywords": ["未来", "契約", "受注", "見込", "予測"],
             "content": f"未来の数字 = 契約済売上(請求前含む全案件) - 原価 - 固定費(月{cfg.fixed_cost_monthly // 10000}万) - 税金({int(cfg.tax_rate * 100)}%)"},
            {"keywords": ["今", "請求", "売掛", "現在"],
             "content": f"今の数字 = 請求済売上 - 支払予定 - 日割固定費(月{cfg.fixed_cost_monthly // 10000}万) - 税金({int(cfg.tax_rate * 100)}%)"},
            {"keywords": ["キャッシュ", "cf", "入金", "資金繰り", "現金"],
             "content": "キャッシュフロー = 入金済額 - 支払済額 - 日割固定費 - 税金。差額=必要運転資金"},
            {"keywords": ["固定費", "経費", "コスト", "人件費", "給料", "給与"],
             "content": (
                 f"固定費: 月額{cfg.fixed_cost_monthly // 10000}万円(年間{cfg.fixed_cost_monthly * 12 // 10000}万)"
                 f"/人件費合計{sum(s.monthly_salary for s in self.staff) // 10000}万"
             )},
            {"keywords": ["利益率", "目標", "達成率"],
             "content": (
                 f"年間売上目標: {cfg.annual_target // 10000}万円/利益率目標: {int(cfg.target_margin * 100)}%以上"
                 f"/総売上: {sum(p.revenue for p in self.projects) // 10000}万"
                 f"/総原価: {sum(p.cost for p in self.projects) // 10000}万"
             )},
            {"keywords": ["全体", "サマリ", "まとめ", "概要", "全案件", "一覧"],
             "content": (
                 f"全{len(self.projects)}案件合計: "
                 f"売上{sum(p.revenue for p in self.projects) // 10000}万"
                 f"/原価{sum(p.cost for p in self.projects) // 10000}万"
             )},
        ])

        return docs
