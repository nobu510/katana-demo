"""
全エンジン動作テスト
pytest -v backend/tests/test_engines.py
"""
import pytest
from datetime import date, time, timedelta


# =====================================================================
# 1. numbering_engine — 採番の生成と紐づけ確認
# =====================================================================

class TestNumberingEngine:
    """採番ルールエンジンのテスト"""

    def test_company_id_sequential(self):
        """企業IDが連番で生成される"""
        from backend.engines.numbering_engine import NumberingState, generate_company_id
        s = NumberingState()
        c1, s = generate_company_id(s)
        c2, s = generate_company_id(s)
        c3, s = generate_company_id(s)
        assert c1.id == "C001"
        assert c2.id == "C002"
        assert c3.id == "C003"

    def test_project_id_linked_to_company(self):
        """案件IDが企業IDに紐づく"""
        from backend.engines.numbering_engine import (
            NumberingState, generate_company_id, generate_project_id,
        )
        s = NumberingState()
        c, s = generate_company_id(s)
        p1, s = generate_project_id(s, c.id)
        p2, s = generate_project_id(s, c.id)
        assert p1.id == "P001-C001"
        assert p2.id == "P002-C001"
        assert p1.parent_id == "C001"

    def test_all_entity_types(self):
        """全10種類のエンティティが正しく採番される"""
        from backend.engines.numbering_engine import (
            NumberingState,
            generate_company_id, generate_project_id, generate_staff_id,
            generate_transaction_id, generate_journal_id, generate_expense_id,
            generate_sales_id, generate_estimate_id, generate_invoice_id,
            generate_attendance_id,
        )
        s = NumberingState()
        c, s = generate_company_id(s)
        p, s = generate_project_id(s, c.id)
        st, s = generate_staff_id(s, c.id)
        t, s = generate_transaction_id(s, p.id)
        j, s = generate_journal_id(s, c.id)
        e, s = generate_expense_id(s, c.id)
        sl, s = generate_sales_id(s, c.id)
        q, s = generate_estimate_id(s, c.id)
        iv, s = generate_invoice_id(s, c.id)
        at, s = generate_attendance_id(s, st.id)

        assert c.id == "C001"
        assert p.id == "P001-C001"
        assert st.id == "S001-C001"
        assert t.id == "T001-P001-C001"
        assert j.id == "J001-C001"
        assert e.id == "E001-C001"
        assert sl.id == "SL001-C001"
        assert q.id == "Q001-C001"
        assert iv.id == "IV001-C001"
        assert at.id == "AT001-S001-C001"

    def test_parse_id(self):
        """IDパースが正しく動作する"""
        from backend.engines.numbering_engine import parse_id
        parsed = parse_id("AT003-S001-C002")
        assert parsed.prefix == "AT"
        assert parsed.seq == 3
        assert parsed.parent_id == "S001-C002"
        assert parsed.parent_prefix == "S"

    def test_trace_to_root(self):
        """IDから企業ルートまで辿れる"""
        from backend.engines.numbering_engine import trace_to_root
        path = trace_to_root("T001-P001-C001")
        assert path == ["T001-P001-C001", "P001-C001", "C001"]

    def test_rebuild_state(self):
        """既存IDからカウンタを復元できる"""
        from backend.engines.numbering_engine import (
            rebuild_state, generate_company_id,
        )
        existing = ["C001", "C002", "C005", "P001-C001", "P003-C001"]
        state = rebuild_state(existing)
        c, state = generate_company_id(state)
        assert c.id == "C006"  # 5の次は6

    def test_parent_validation_rejects_wrong_parent(self):
        """親IDが不正な場合エラーになる"""
        from backend.engines.numbering_engine import (
            NumberingState, generate_project_id, NumberingError,
        )
        s = NumberingState()
        with pytest.raises(NumberingError):
            generate_project_id(s, "S001-C001")  # 案件の親は企業(C)でなければならない

    def test_batch_generation(self):
        """一括採番が正しく動作する"""
        from backend.engines.numbering_engine import (
            NumberingState, generate_project_id, generate_batch,
        )
        s = NumberingState()
        ids, s = generate_batch(s, generate_project_id, "C001", 5)
        assert len(ids) == 5
        assert ids[0].id == "P001-C001"
        assert ids[4].id == "P005-C001"


# =====================================================================
# 2. journal_engine — チャットから自動仕訳
# =====================================================================

class TestJournalEngine:
    """自動仕訳エンジンのテスト"""

    def test_sales_journal_from_chat(self):
        """「売上300万」で売上仕訳が生成される"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("A社から売上300万円", entry_date=date(2025, 6, 1))
        assert result["success"] is True
        assert result["template_name"] == "売上計上"
        assert result["amount"] == 3_000_000
        entry = result["entry"]
        assert entry.is_balanced
        assert entry.numbering_id == "J001-C001"

    def test_expense_journal_balanced(self):
        """経費仕訳が貸借一致する"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("家賃20万円", entry_date=date(2025, 6, 15))
        assert result["success"]
        assert result["entry"].is_balanced
        assert result["entry"].total_debit == result["entry"].total_credit

    def test_asset_purchase_tax_handling(self):
        """資産購入で仮払消費税が正しく計上される"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("PC購入 200000円", entry_date=date(2025, 6, 1))
        assert result["success"]
        entry = result["entry"]
        assert entry.is_balanced
        # 仮払消費税の行があるか
        tax_lines = [ln for ln in entry.lines if "消費税" in ln.account.name]
        assert len(tax_lines) == 1
        assert tax_lines[0].debit > 0  # 仮払消費税は借方

    def test_small_amount_extraction(self):
        """500円などの小額が正しく抽出される"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("タクシー500円", entry_date=date(2025, 6, 1))
        assert result["success"]
        assert result["amount"] == 500

    def test_date_extraction(self):
        """日本語テキストから日付が抽出される"""
        from backend.engines.journal_engine import JournalEngine
        result = JournalEngine._extract_date("6月15日に交通費")
        assert result == date(date.today().year, 6, 15)

    def test_salary_not_taxed(self):
        """給与は不課税で処理される"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("給与30万円", entry_date=date(2025, 6, 25))
        assert result["success"]
        entry = result["entry"]
        assert entry.is_balanced
        # 消費税行がないはず
        tax_lines = [ln for ln in entry.lines if "消費税" in ln.account.name]
        assert len(tax_lines) == 0

    def test_cash_payment(self):
        """現金支払で現金勘定が使われる"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("文房具 現金で 800円", entry_date=date(2025, 6, 1))
        assert result["success"]
        assert result["payment_method"] == "cash"
        has_cash = any(ln.account.name == "現金" for ln in result["entry"].lines)
        assert has_cash

    def test_confidence_score(self):
        """テンプレートマッチに信頼度が付く"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        result = engine.process_chat("売上500万円", entry_date=date(2025, 6, 1))
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_pl_and_bs_generated(self):
        """複数仕訳からP/L・B/Sが生成される"""
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        engine.process_chat("売上500万円", entry_date=date(2025, 6, 1))
        engine.process_chat("外注費100万円", entry_date=date(2025, 6, 10))
        engine.process_chat("家賃30万円", entry_date=date(2025, 6, 15))

        pl = engine.get_pl()
        assert pl["売上高"]["total"] > 0
        assert pl["営業利益"] > 0

        bs = engine.get_bs()
        assert bs["資産の部"]["total"] == bs["負債・純資産合計"]


# =====================================================================
# 3. profit_engine — 3視点利益計算
# =====================================================================

class TestProfitEngine:
    """利益計算エンジンのテスト"""

    @pytest.fixture
    def setup(self):
        from backend.engines.profit_engine import (
            ProfitEngine, CompanyConfig, Project, Staff, StaffAssignment,
        )
        config = CompanyConfig("テスト社", 500_000, 0.30, 50_000_000, 0.30)
        engine = ProfitEngine(config)
        projects = [
            Project("P001-C001", "A社", "A社", "Webサイト制作",
                    3_000_000, 1_000_000, 0, 2, 4,
                    category="Web",
                    staff=[StaffAssignment("S001-C001", "田中", 80, 3000)]),
            Project("P002-C001", "B社", "B社", "アプリ開発",
                    5_000_000, 2_000_000, 1, 3, 5,
                    category="App"),
        ]
        staff = [Staff("S001-C001", "田中", "田中太郎", "Eng", 3000, 350_000)]
        return engine, projects, staff

    def test_three_views_at_month_3(self, setup):
        """月度3で3視点が正しく計算される"""
        engine, projects, _ = setup
        tv = engine.calc_three_views(projects, 3)
        # 月度3: 両案件とも契約済 → 未来=全売上
        assert tv.future.revenue == 8_000_000
        assert tv.future.cost == 3_000_000
        # 月度3: A社は請求済(invoice_month=2), B社は請求済(invoice_month=3)
        assert tv.now.revenue == 8_000_000
        # 月度3: 未入金(A社は4月, B社は5月)
        assert tv.cash.revenue == 0

    def test_three_views_future_gt_cash(self, setup):
        """未来の利益 ≥ CFの利益"""
        engine, projects, _ = setup
        tv = engine.calc_three_views(projects, 3)
        assert tv.future.profit >= tv.cash.profit

    def test_project_profits(self, setup):
        """案件別利益が正しく計算される"""
        engine, projects, _ = setup
        pp = engine.calc_project_profits(projects, 3)
        assert len(pp) == 2
        assert pp[0].gross_profit == 2_000_000  # 3M - 1M
        assert pp[1].gross_profit == 3_000_000  # 5M - 2M
        assert 0 < pp[0].gross_margin < 1

    def test_staff_profit(self, setup):
        """社員別利益が正しく計算される"""
        engine, projects, staff = setup
        sp = engine.calc_all_staff_profits(staff, projects, 3)
        assert sp[0].total_hours == 80
        assert sp[0].total_labor_cost == 240_000  # 80h * 3000

    def test_category_profits(self, setup):
        """カテゴリ別利益が正しく計算される"""
        engine, projects, _ = setup
        cp = engine.calc_category_profits(projects)
        assert len(cp) == 2
        names = [c.category for c in cp]
        assert "Web" in names
        assert "App" in names

    def test_breakeven(self, setup):
        """損益分岐点が正の値"""
        engine, _, _ = setup
        be = engine.breakeven_revenue()
        assert be > 0
        # 固定費 500K * 12 = 6M, 目標利益率30% → BE = 6M / 0.3 = 20M
        assert be == 20_000_000

    def test_monthly_profit_12_months(self, setup):
        """月別利益が12ヶ月分返る"""
        engine, projects, _ = setup
        mp = engine.calc_monthly_profit(projects)
        assert len(mp) == 12


# =====================================================================
# 4. tax_engine — 法人税・消費税計算
# =====================================================================

class TestTaxEngine:
    """税金計算エンジンのテスト"""

    def test_consumption_tax_inclusive_10pct(self):
        """税込11,000円 → 税抜10,000円 + 消費税1,000円"""
        from backend.engines.tax_engine import calc_consumption_tax_inclusive, TaxRate
        r = calc_consumption_tax_inclusive(11_000)
        assert r.tax_exclusive == 10_000
        assert r.tax_amount == 1_000
        assert r.rate == TaxRate.STANDARD

    def test_consumption_tax_exclusive_10pct(self):
        """税抜10,000円 → 税込11,000円"""
        from backend.engines.tax_engine import calc_consumption_tax_exclusive
        r = calc_consumption_tax_exclusive(10_000)
        assert r.tax_inclusive == 11_000
        assert r.tax_amount == 1_000

    def test_reduced_tax_rate_8pct(self):
        """軽減税率8%: 税込10,800円 → 税抜10,000円"""
        from backend.engines.tax_engine import calc_consumption_tax_inclusive, TaxRate
        r = calc_consumption_tax_inclusive(10_800, TaxRate.REDUCED)
        assert r.tax_exclusive == 10_000
        assert r.tax_amount == 800

    def test_national_local_tax_breakdown(self):
        """消費税が国税+地方消費税に分解される"""
        from backend.engines.tax_engine import calc_consumption_tax_inclusive
        r = calc_consumption_tax_inclusive(11_000)
        assert r.national_tax + r.local_tax == r.tax_amount
        assert r.national_tax > r.local_tax  # 国税7.8% > 地方2.2%

    def test_invoice_tax_per_rate(self):
        """インボイス制度: 税率ごとに合算してから消費税計算"""
        from backend.engines.tax_engine import calc_invoice_tax, InvoiceLineItem, TaxRate
        items = [
            InvoiceLineItem("商品A", 10_000, TaxRate.STANDARD),
            InvoiceLineItem("商品B", 5_000, TaxRate.STANDARD),
            InvoiceLineItem("食品C", 8_000, TaxRate.REDUCED),
        ]
        summaries = calc_invoice_tax(items)
        assert len(summaries) == 2
        # 標準: 15,000 * 10% = 1,500
        std = [s for s in summaries if s.rate == TaxRate.STANDARD][0]
        assert std.taxable_amount == 15_000
        assert std.tax_amount == 1_500

    def test_corporate_tax_sme(self):
        """中小法人: 800万以下15%、超過23.2%"""
        from backend.engines.tax_engine import calc_corporate_tax
        r = calc_corporate_tax(10_000_000, is_sme=True)
        # 800万 * 15% = 120万, 200万 * 23.2% = 46.4万 → 合計166.4万
        assert r.corp_tax == 1_200_000 + 464_000
        assert 0.15 < r.effective_rate < 0.232

    def test_corporate_tax_zero_income(self):
        """赤字の場合は法人税ゼロ"""
        from backend.engines.tax_engine import calc_corporate_tax
        r = calc_corporate_tax(-1_000_000)
        assert r.corp_tax == 0

    def test_local_tax_calculation(self):
        """地方税（住民税+事業税+特別事業税）が計算される"""
        from backend.engines.tax_engine import calc_local_tax
        r = calc_local_tax(1_664_000, 10_000_000)
        assert r.inhabitant_tax > 0       # 住民税
        assert r.enterprise_tax > 0       # 事業税
        assert r.special_enterprise_tax > 0  # 特別事業税
        assert r.total == r.inhabitant_tax + r.enterprise_tax + r.special_enterprise_tax

    def test_total_tax_effective_rate(self):
        """実効税率が20-40%の範囲"""
        from backend.engines.tax_engine import calc_total_tax
        r = calc_total_tax(10_000_000)
        assert 0.20 < r.effective_rate < 0.40

    def test_withholding_professional(self):
        """報酬の源泉徴収: 100万以下10.21%"""
        from backend.engines.tax_engine import calc_withholding_professional
        r = calc_withholding_professional(500_000)
        assert r.withholding_tax == int(500_000 * 0.1021)
        assert r.net_amount == 500_000 - r.withholding_tax

    def test_withholding_professional_over_1m(self):
        """報酬の源泉徴収: 100万超部分20.42%"""
        from backend.engines.tax_engine import calc_withholding_professional
        r = calc_withholding_professional(1_500_000)
        expected = int(1_000_000 * 0.1021) + int(500_000 * 0.2042)
        assert r.withholding_tax == expected

    def test_withholding_salary(self):
        """給与の源泉徴収が計算される"""
        from backend.engines.tax_engine import calc_withholding_salary
        r = calc_withholding_salary(300_000)
        assert r.withholding_tax >= 0
        assert r.net_amount == 300_000 - r.withholding_tax


# =====================================================================
# 5. settlement_engine — 決算書類
# =====================================================================

class TestSettlementEngine:
    """決算エンジンのテスト"""

    @pytest.fixture
    def journal_entries(self):
        from backend.engines.journal_engine import JournalEngine
        engine = JournalEngine("C001")
        engine.process_chat("売上500万円", entry_date=date(2025, 6, 1))
        engine.process_chat("外注費100万円", entry_date=date(2025, 6, 10))
        engine.process_chat("家賃30万円", entry_date=date(2025, 6, 15))
        engine.process_chat("給与35万円", entry_date=date(2025, 6, 25))
        return engine.ledger.entries

    def test_trial_balance_is_balanced(self, journal_entries):
        """試算表の借方合計=貸方合計"""
        from backend.engines.settlement_engine import calc_trial_balance
        tb = calc_trial_balance(journal_entries)
        assert tb.is_balanced
        assert tb.total_debit == tb.total_credit
        assert tb.total_debit > 0

    def test_profit_and_loss(self, journal_entries):
        """P/Lが生成され売上>0"""
        from backend.engines.settlement_engine import calc_profit_and_loss
        pl = calc_profit_and_loss(journal_entries)
        assert pl.sales_total > 0
        assert pl.gross_profit > 0
        assert pl.operating_profit > 0

    def test_balance_sheet_balanced(self, journal_entries):
        """B/Sの資産=負債+純資産"""
        from backend.engines.settlement_engine import calc_balance_sheet
        bs = calc_balance_sheet(journal_entries)
        assert bs.is_balanced
        assert bs.total_assets == bs.total_liabilities_and_equity

    def test_cash_flow_statement(self, journal_entries):
        """CF計算書が生成される"""
        from backend.engines.settlement_engine import calc_cash_flow_statement
        cf = calc_cash_flow_statement(journal_entries, beginning_cash=1_000_000)
        assert cf.beginning_cash == 1_000_000
        assert cf.ending_cash == cf.beginning_cash + cf.net_change

    def test_full_settlement(self, journal_entries):
        """決算書類一式が生成される"""
        from backend.engines.settlement_engine import generate_settlement
        result = generate_settlement(journal_entries, date(2025, 4, 1), date(2026, 3, 31))
        assert result.entry_count == 4
        assert result.trial_balance.is_balanced
        assert result.balance_sheet.is_balanced
        assert result.profit_and_loss.sales_total > 0

    def test_empty_settlement(self):
        """仕訳なしでも決算が生成される"""
        from backend.engines.settlement_engine import generate_settlement
        result = generate_settlement([], date(2025, 4, 1), date(2026, 3, 31))
        assert result.entry_count == 0
        assert result.profit_and_loss.net_income == 0


# =====================================================================
# 6. sales_engine — 売上集計
# =====================================================================

class TestSalesEngine:
    """売上管理エンジンのテスト"""

    @pytest.fixture
    def records(self):
        from backend.engines.sales_engine import SalesEngine
        engine = SalesEngine("C001")
        s1 = engine.create_sales_record("A社", "Webサイト", 3_000_000,
                                         date(2025, 4, 15), category="Web", cost=1_000_000)
        s2 = engine.create_sales_record("B社", "アプリ", 5_000_000,
                                         date(2025, 4, 20), category="App", cost=2_000_000)
        s3 = engine.create_sales_record("A社", "保守", 500_000,
                                         date(2025, 5, 10), category="保守")
        return [s1, s2, s3]

    def test_numbering(self, records):
        """売上IDが連番で採番される"""
        assert records[0].id == "SL001-C001"
        assert records[1].id == "SL002-C001"
        assert records[2].id == "SL003-C001"

    def test_summarize(self, records):
        """売上集計が正しい"""
        from backend.engines.sales_engine import SalesEngine
        summary = SalesEngine.summarize(records)
        assert summary.total_amount == 8_500_000
        assert summary.total_cost == 3_000_000
        assert summary.gross_profit == 5_500_000
        assert summary.count == 3

    def test_filter_by_month(self, records):
        """月別フィルタが正しい"""
        from backend.engines.sales_engine import SalesEngine
        apr = SalesEngine.filter_by_month(records, 2025, 4)
        assert len(apr) == 2
        may = SalesEngine.filter_by_month(records, 2025, 5)
        assert len(may) == 1

    def test_monthly_summary(self, records):
        """月次集計が12ヶ月分返る"""
        from backend.engines.sales_engine import SalesEngine
        monthly = SalesEngine.monthly_summary(records, 2025)
        assert len(monthly) == 12
        assert monthly[3]["amount"] == 8_000_000  # 4月(index=3)
        assert monthly[4]["amount"] == 500_000    # 5月(index=4)

    def test_ranking_by_client(self, records):
        """取引先別ランキングが金額降順"""
        from backend.engines.sales_engine import SalesEngine
        ranking = SalesEngine.ranking_by_client(records)
        assert ranking[0].key == "B社"      # 5M
        assert ranking[1].key == "A社"      # 3.5M
        assert ranking[0].amount > ranking[1].amount

    def test_target_achievement(self, records):
        """目標達成率の計算"""
        from backend.engines.sales_engine import SalesEngine, SalesTarget
        targets = [SalesTarget(2025, 4, 10_000_000)]
        ach = SalesEngine.calc_target_achievement(records, targets, 2025, 4)
        assert len(ach) == 1
        assert ach[0].actual == 8_000_000
        assert ach[0].achievement_rate == 0.8
        assert ach[0].gap == 2_000_000

    def test_year_over_year(self, records):
        """前年同月比"""
        from backend.engines.sales_engine import SalesEngine
        yoy = SalesEngine.year_over_year(records, 2025, 4)
        assert yoy["current"] == 8_000_000
        assert yoy["previous"] == 0  # 前年データなし


# =====================================================================
# 7. estimate_invoice_engine — 見積→請求→入金フロー
# =====================================================================

class TestEstimateInvoiceEngine:
    """見積・請求エンジンのテスト"""

    def test_full_flow(self):
        """見積→受注→請求→入金の全フローが動作する"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem, EstimateStatus, InvoiceStatus,
        )
        engine = EstimateInvoiceEngine("C001", "T1234567890123")

        # 見積作成
        est = engine.create_estimate("A社", "Web制作", [
            LineItem("デザイン", 1, "式", 500_000),
            LineItem("開発", 2, "人月", 400_000),
        ])
        assert est.id == "Q001-C001"
        assert est.subtotal == 1_300_000
        assert est.tax_total > 0
        assert est.status == EstimateStatus.DRAFT

        # 受注
        engine.accept_estimate(est)
        assert est.status == EstimateStatus.ACCEPTED

        # 請求書発行
        inv = engine.estimate_to_invoice(est, payment_terms_days=30)
        assert inv.id == "IV001-C001"
        assert inv.estimate_id == "Q001-C001"
        assert inv.total == est.total
        assert inv.status == InvoiceStatus.ISSUED
        assert inv.invoice_registration_number == "T1234567890123"

        # 一部入金
        EstimateInvoiceEngine.record_payment(inv, 500_000)
        assert inv.status == InvoiceStatus.PARTIAL_PAID
        assert inv.paid_amount == 500_000

        # 残額入金
        remaining = inv.total - inv.paid_amount
        EstimateInvoiceEngine.record_payment(inv, remaining)
        assert inv.status == InvoiceStatus.PAID

    def test_invoice_tax_summary(self):
        """税率別集計がインボイスに含まれる"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem,
        )
        from backend.engines.tax_engine import TaxRate
        engine = EstimateInvoiceEngine("C001", "T9999999999999")
        inv = engine.create_invoice("B社", "食品＋備品", [
            LineItem("備品", 1, "式", 100_000, tax_rate=TaxRate.STANDARD),
            LineItem("食品", 1, "式", 50_000, tax_rate=TaxRate.REDUCED),
        ])
        assert len(inv.tax_summary) == 2

    def test_overdue_check(self):
        """延滞チェックが正しく動作する"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem, InvoiceStatus,
        )
        engine = EstimateInvoiceEngine("C001")
        inv = engine.create_invoice("X社", "テスト", [
            LineItem("サービス", 1, "式", 100_000),
        ], issue_date=date(2025, 1, 1), payment_terms_days=30)
        # 期限後にチェック
        is_overdue = EstimateInvoiceEngine.check_overdue(inv, as_of=date(2025, 3, 1))
        assert is_overdue
        assert inv.status == InvoiceStatus.OVERDUE

    def test_aging_report(self):
        """エイジング分析が正しく集計される"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem,
        )
        engine = EstimateInvoiceEngine("C001")
        inv1 = engine.create_invoice("A社", "X", [LineItem("a", 1, "式", 100_000)],
                                      issue_date=date(2025, 1, 1), payment_terms_days=30)
        inv2 = engine.create_invoice("B社", "Y", [LineItem("b", 1, "式", 200_000)],
                                      issue_date=date(2025, 4, 1), payment_terms_days=30)
        aging = EstimateInvoiceEngine.aging_report([inv1, inv2], as_of=date(2025, 5, 1))
        assert aging["current"] > 0 or aging["30days"] > 0

    def test_trace(self):
        """見積→請求→入金の追跡ができる"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem,
        )
        engine = EstimateInvoiceEngine("C001")
        est = engine.create_estimate("A社", "テスト", [LineItem("X", 1, "式", 100_000)])
        engine.accept_estimate(est)
        inv = engine.estimate_to_invoice(est)
        trace = EstimateInvoiceEngine.trace_estimate_to_payment(est, [inv])
        assert trace["estimate_id"] == est.id
        assert trace["invoice_id"] == inv.id
        assert trace["remaining"] == inv.total


# =====================================================================
# 8. project_engine — 案件ステータス遷移
# =====================================================================

class TestProjectEngine:
    """案件進捗エンジンのテスト"""

    @pytest.fixture
    def project(self):
        from backend.engines.project_engine import (
            ProjectData, ProjectStatus, TaskItem,
        )
        return ProjectData(
            id="P001-C001", company_id="C001", name="Webサイト",
            status=ProjectStatus.IN_PROGRESS,
            start_date=date(2025, 4, 1), deadline=date(2025, 6, 30),
            budget_revenue=3_000_000, budget_cost=1_500_000,
            actual_cost=500_000,
            tasks=[
                TaskItem("T1", "デザイン", planned_hours=40, actual_hours=40,
                         completed=True, progress=100),
                TaskItem("T2", "実装", planned_hours=80, actual_hours=20,
                         progress=25,
                         start_date=date(2025, 4, 15),
                         end_date=date(2025, 6, 15)),
            ],
        )

    def test_valid_transition(self, project):
        """許可されたステータス遷移ができる"""
        from backend.engines.project_engine import ProjectEngine, ProjectStatus
        ok, _ = ProjectEngine.transition(project, ProjectStatus.INVOICED)
        assert ok
        assert project.status == ProjectStatus.INVOICED

    def test_invalid_transition(self, project):
        """許可されていないステータス遷移は拒否される"""
        from backend.engines.project_engine import ProjectEngine, ProjectStatus
        ok, msg = ProjectEngine.transition(project, ProjectStatus.PROSPECT)
        assert not ok
        assert "許可されていません" in msg

    def test_progress_calculation(self, project):
        """進捗率が正しく計算される"""
        from backend.engines.project_engine import ProjectEngine
        prog = ProjectEngine.calc_progress(project, date(2025, 5, 15))
        assert prog.task_progress == 0.5   # 1/2タスク完了
        assert prog.days_until_deadline == 46
        assert not prog.is_overdue

    def test_overdue_detection(self, project):
        """期限超過が検出される"""
        from backend.engines.project_engine import ProjectEngine
        prog = ProjectEngine.calc_progress(project, date(2025, 7, 15))
        assert prog.is_overdue
        assert prog.days_until_deadline < 0

    def test_work_log(self, project):
        """工数記録が正しく追加される"""
        from backend.engines.project_engine import ProjectEngine
        log = ProjectEngine.add_work_log(project, "S001-C001", "田中", 6.0,
                                          date(2025, 5, 15), task_id="T2")
        assert len(project.work_logs) == 1
        assert project.tasks[1].actual_hours == 26.0  # 20 + 6

    def test_budget_vs_actual(self, project):
        """予算vs実績の差異が正しい"""
        from backend.engines.project_engine import ProjectEngine
        bva = ProjectEngine.budget_vs_actual(project)
        assert bva.cost_variance == 500_000 - 1_500_000  # -1M

    def test_gantt_data(self, project):
        """ガントチャートデータが生成される"""
        from backend.engines.project_engine import ProjectEngine
        gantt = ProjectEngine.gantt_data([project])
        assert len(gantt) == 2
        assert gantt[0].task_name == "デザイン"


# =====================================================================
# 9. hr_engine — 給与計算・社会保険
# =====================================================================

class TestHREngine:
    """人事労務エンジンのテスト"""

    @pytest.fixture
    def employee(self):
        from backend.engines.hr_engine import HREngine
        engine = HREngine("C001")
        return engine.create_employee(
            "田中太郎", 350_000,
            hire_date=date(2022, 4, 1),
            department="開発",
            dependents=1,
            commute_allowance=15_000,
        )

    def test_employee_creation(self, employee):
        """社員が採番付きで登録される"""
        assert employee.id == "S001-C001"
        assert employee.hourly_rate == 350_000 // 160
        assert employee.department == "開発"

    def test_social_insurance(self):
        """社会保険料が労使で計算される"""
        from backend.engines.hr_engine import HREngine
        si = HREngine.calc_social_insurance(350_000, include_employer=True)
        # 健康保険 + 厚生年金 + 雇用保険
        assert si["health_insurance"] > 0
        assert si["pension"] > 0
        assert si["employment_insurance"] > 0
        assert si["employee_total"] == (
            si["health_insurance"] + si["pension"] + si["employment_insurance"]
        )
        # 事業主負担
        assert si["employer_total"] > si["employee_total"]  # 事業主は労災分多い

    def test_payslip_calculation(self, employee):
        """給与明細が正しく計算される"""
        from backend.engines.hr_engine import HREngine, OvertimeDetail
        ot = OvertimeDetail(over_hours=20)
        slip = HREngine.calc_payslip(employee, 2025, 5, overtime=ot)

        assert slip.base_salary == 350_000
        assert slip.overtime_pay > 0              # 残業代あり
        assert slip.gross_pay > slip.base_salary  # 支給総額 > 基本給
        assert slip.social_insurance_total > 0    # 社保控除あり
        assert slip.net_pay < slip.gross_pay      # 差引 < 総額
        assert slip.net_pay > 0                   # マイナスにはならない

    def test_overtime_rate_60h(self):
        """月60時間超の残業は1.5倍で計算される"""
        from backend.engines.hr_engine import HREngine, Employee, OvertimeDetail
        emp = Employee("S001-C001", "C001", "テスト", base_salary=320_000)
        emp.hourly_rate = 2000
        ot_normal = OvertimeDetail(over_hours=40)
        ot_over60 = OvertimeDetail(over_hours=70)
        slip_normal = HREngine.calc_payslip(emp, 2025, 5, overtime=ot_normal)
        slip_over60 = HREngine.calc_payslip(emp, 2025, 5, overtime=ot_over60)
        # 60h超部分は1.5倍 → 差が1.25倍より大きい
        assert slip_over60.overtime_pay > slip_normal.overtime_pay

    def test_year_end_adjustment(self, employee):
        """年末調整で過不足が計算される"""
        from backend.engines.hr_engine import HREngine
        slips = [HREngine.calc_payslip(employee, 2025, m) for m in range(1, 13)]
        yea = HREngine.year_end_adjustment(slips)
        assert yea["annual_gross"] > 0
        assert yea["taxable_income"] >= 0
        assert yea["annual_tax"] >= 0
        assert yea["refund"] >= 0 or yea["additional"] >= 0

    def test_paid_leave_grant(self):
        """有給休暇付与日数が勤続年数で正しい"""
        from backend.engines.hr_engine import HREngine
        # 入社6ヶ月超: 10日 (365.25日計算のため余裕を持たせる)
        assert HREngine.calc_paid_leave_grant(date(2025, 1, 1), date(2025, 7, 5)) == 10
        # 入社1.5年超: 11日
        assert HREngine.calc_paid_leave_grant(date(2024, 1, 1), date(2025, 7, 5)) == 11
        # 入社6.5年以上: 20日
        assert HREngine.calc_paid_leave_grant(date(2018, 1, 1), date(2025, 7, 5)) == 20

    def test_paid_leave_usage(self, employee):
        """有給消化と残日数管理"""
        from backend.engines.hr_engine import HREngine
        employee.paid_leave_days = 15
        ok, _ = HREngine.use_paid_leave(employee, 3)
        assert ok
        assert employee.paid_leave_days == 12
        ok, msg = HREngine.use_paid_leave(employee, 20)
        assert not ok
        assert "残日数不足" in msg

    def test_overtime_limit_36_agreement(self):
        """36協定: 月45時間超で警告"""
        from backend.engines.hr_engine import HREngine, OvertimeDetail
        ot = OvertimeDetail(over_hours=50, late_night_hours=5, holiday_hours=8)
        warnings = HREngine.check_overtime_limit(ot)
        assert any("45" in w for w in warnings)

    def test_overtime_limit_100h(self):
        """36協定: 月100時間以上で違法警告"""
        from backend.engines.hr_engine import HREngine, OvertimeDetail
        ot = OvertimeDetail(over_hours=90, holiday_hours=15)
        warnings = HREngine.check_overtime_limit(ot)
        assert any("100" in w for w in warnings)


# =====================================================================
# 10. attendance_engine — 勤怠・残業計算
# =====================================================================

class TestAttendanceEngine:
    """勤怠管理エンジンのテスト"""

    def test_clock_in_out(self):
        """出退勤の打刻と労働時間計算"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        assert rec.id == "AT001-S001-C001"
        assert rec.clock_in == time(9, 0)

        AttendanceEngine.clock_out(rec, time(20, 30))
        assert rec.clock_out == time(20, 30)
        # 9:00-20:30 = 11.5h - 1h休憩 = 10.5h
        assert rec.actual_hours == 10.5
        # 残業 = 10.5 - 8 = 2.5h
        assert rec.overtime_hours == 2.5

    def test_standard_8h_no_overtime(self):
        """定時(9:00-18:00)は残業ゼロ"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.clock_out(rec, time(18, 0))
        assert rec.actual_hours == 8.0
        assert rec.overtime_hours == 0.0

    def test_late_night_hours(self):
        """深夜時間(22:00-5:00)が計算される"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.clock_out(rec, time(23, 0))
        # 22:00-23:00 = 1h深夜
        assert rec.late_night_hours == 1.0

    def test_project_hours(self):
        """案件別工数が記録される"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.add_project_hours(rec, "P001-C001", "Web", 5.0, "フロントエンド")
        AttendanceEngine.add_project_hours(rec, "P002-C001", "App", 3.0, "API開発")
        assert len(rec.project_hours) == 2
        assert rec.project_hours[0].hours == 5.0

    def test_monthly_summary(self):
        """月次集計が正しい"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        records = []
        for day in range(1, 6):  # 5日間
            rec = engine.clock_in("S001-C001", date(2025, 5, day), time(9, 0))
            AttendanceEngine.clock_out(rec, time(19, 0))  # 1h残業
            records.append(rec)

        summary = AttendanceEngine.monthly_summary(records, 2025, 5)
        assert summary["work_days"] == 5
        assert summary["total_hours"] == 45.0   # 9h * 5
        assert summary["total_overtime"] == 5.0  # 1h * 5

    def test_to_overtime_detail(self):
        """勤怠→給与計算用の残業データに変換"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.clock_out(rec, time(20, 0))
        ot = AttendanceEngine.to_overtime_detail([rec], 2025, 5)
        assert ot.over_hours == 2.0  # 11h - 1h休憩 - 8h = 2h

    def test_project_hours_summary(self):
        """案件別工数集計"""
        from backend.engines.attendance_engine import AttendanceEngine
        engine = AttendanceEngine("C001")
        rec = engine.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.add_project_hours(rec, "P001-C001", "Web", 5.0)
        AttendanceEngine.add_project_hours(rec, "P002-C001", "App", 3.0)
        summary = AttendanceEngine.project_hours_summary([rec])
        assert len(summary) == 2
        assert summary[0]["total_hours"] == 5.0

    def test_parse_work_report(self):
        """業務報告テキストのパース"""
        from backend.engines.attendance_engine import AttendanceEngine
        parsed = AttendanceEngine.parse_work_report("Webサイト5時間 アプリ3.5時間")
        assert len(parsed) == 2
        assert parsed[0]["hours"] == 5.0
        assert parsed[1]["hours"] == 3.5


# =====================================================================
# 11. chat_engine — メッセージ送受信
# =====================================================================

class TestChatEngine:
    """社内チャットエンジンのテスト"""

    def test_create_room(self):
        """チャットルームの作成"""
        from backend.engines.chat_engine import ChatEngine, ChatType
        room = ChatEngine.create_room("開発チーム", ["S001", "S002", "S003"])
        assert room.name == "開発チーム"
        assert room.chat_type == ChatType.GROUP
        assert len(room.members) == 3

    def test_create_direct(self):
        """1:1チャットの作成"""
        from backend.engines.chat_engine import ChatEngine, ChatType
        room = ChatEngine.create_direct("S001", "S002")
        assert room.chat_type == ChatType.DIRECT
        assert len(room.members) == 2

    def test_send_text_message(self):
        """テキストメッセージの送信"""
        from backend.engines.chat_engine import ChatEngine, MessageType
        room = ChatEngine.create_room("team", ["S001", "S002"])
        msg = ChatEngine.send_message(room, "S001", "田中", "了解です")
        assert msg.message_type == MessageType.TEXT
        assert msg.content == "了解です"
        assert len(room.messages) == 1

    def test_work_report_detection(self):
        """業務報告の自動検出"""
        from backend.engines.chat_engine import ChatEngine, MessageType
        room = ChatEngine.create_room("team", ["S001", "S002"])
        msg = ChatEngine.send_message(room, "S001", "田中", "Web5時間 API3時間")
        assert msg.message_type == MessageType.WORK_REPORT
        assert len(msg.detected_work) == 2
        assert msg.detected_work[0]["hours"] == 5.0

    def test_attendance_detection(self):
        """出勤・退勤の自動検出"""
        from backend.engines.chat_engine import ChatEngine, parse_chat_message
        p1 = parse_chat_message("おはようございます。出勤します")
        assert p1.attendance == "出勤"
        p2 = parse_chat_message("お疲れ様です。退勤します")
        assert p2.attendance == "退勤"

    def test_expense_detection(self):
        """経費の自動検出"""
        from backend.engines.chat_engine import parse_chat_message
        p = parse_chat_message("タクシー2500円")
        assert p.expense is not None
        assert p.expense["category"] == "旅費交通費"
        assert p.expense["amount"] == 2500

    def test_stamp_send(self):
        """スタンプの送信"""
        from backend.engines.chat_engine import ChatEngine, MessageType
        room = ChatEngine.create_room("team", ["S001", "S002"])
        msg = ChatEngine.send_stamp(room, "S001", "田中", "ok")
        assert msg.message_type == MessageType.STAMP
        assert msg.content == "了解"

    def test_image_send(self):
        """画像の送信"""
        from backend.engines.chat_engine import ChatEngine, MessageType
        room = ChatEngine.create_room("team", ["S001", "S002"])
        msg = ChatEngine.send_image(room, "S001", "田中", "/tmp/photo.jpg")
        assert msg.message_type == MessageType.IMAGE
        assert msg.file_name == "photo.jpg"

    def test_read_management(self):
        """既読管理"""
        from backend.engines.chat_engine import ChatEngine
        room = ChatEngine.create_room("team", ["S001", "S002", "S003"])
        ChatEngine.send_message(room, "S001", "田中", "お知らせ")
        ChatEngine.send_message(room, "S001", "田中", "もう一つ")

        assert ChatEngine.unread_count(room, "S002") == 2
        assert ChatEngine.unread_count(room, "S001") == 0  # 送信者は既読

        ChatEngine.mark_room_as_read(room, "S002")
        assert ChatEngine.unread_count(room, "S002") == 0

    def test_message_search(self):
        """メッセージ検索"""
        from backend.engines.chat_engine import ChatEngine
        room = ChatEngine.create_room("team", ["S001", "S002"])
        ChatEngine.send_message(room, "S001", "田中", "明日の会議について")
        ChatEngine.send_message(room, "S002", "鈴木", "了解です")
        ChatEngine.send_message(room, "S001", "田中", "会議資料を共有します")

        results = ChatEngine.search_messages(room, "会議")
        assert len(results) == 2

    def test_aggregate_daily_hours(self):
        """日別工数集約"""
        from backend.engines.chat_engine import ChatEngine
        room = ChatEngine.create_room("team", ["S001"])
        ChatEngine.send_message(room, "S001", "田中", "Web5時間")
        ChatEngine.send_message(room, "S001", "田中", "API3時間")
        hours = ChatEngine.aggregate_daily_hours(room.messages)
        assert len(hours) == 2
        total = sum(h["hours"] for h in hours)
        assert total == 8.0

    def test_aggregate_expenses(self):
        """経費集約"""
        from backend.engines.chat_engine import ChatEngine
        room = ChatEngine.create_room("team", ["S001"])
        ChatEngine.send_message(room, "S001", "田中", "タクシー2000円")
        ChatEngine.send_message(room, "S001", "田中", "文房具500円")
        expenses = ChatEngine.aggregate_expenses(room.messages)
        assert len(expenses) >= 1
        assert any(e["category"] == "旅費交通費" for e in expenses)


# =====================================================================
# 12. 統合テスト — エンジン間連携
# =====================================================================

class TestIntegration:
    """エンジン間の自動連携テスト"""

    def test_chat_to_attendance_to_payroll(self):
        """チャット→勤怠→給与の連携"""
        from backend.engines.chat_engine import ChatEngine
        from backend.engines.attendance_engine import AttendanceEngine
        from backend.engines.hr_engine import HREngine

        # チャットで業務報告
        room = ChatEngine.create_room("team", ["S001-C001"])
        msg = ChatEngine.send_message(room, "S001-C001", "田中", "Web5時間 API3時間")
        assert len(msg.detected_work) == 2

        # 勤怠に連携
        att = AttendanceEngine("C001")
        rec = att.clock_in("S001-C001", date(2025, 5, 15), time(9, 0))
        AttendanceEngine.clock_out(rec, time(20, 0))

        daily = ChatEngine.aggregate_daily_hours(room.messages)
        for h in daily:
            AttendanceEngine.add_project_hours(rec, "P001-C001", h["project_name"], h["hours"])
        assert len(rec.project_hours) == 2

        # 給与に連携
        ot = AttendanceEngine.to_overtime_detail([rec], 2025, 5)
        hr = HREngine("C001")
        emp = hr.create_employee("田中太郎", 350_000)
        slip = HREngine.calc_payslip(emp, 2025, 5, overtime=ot)
        assert slip.overtime_pay > 0
        assert slip.net_pay > 0

    def test_estimate_to_journal(self):
        """見積→請求→仕訳の連携"""
        from backend.engines.estimate_invoice_engine import (
            EstimateInvoiceEngine, LineItem,
        )
        from backend.engines.journal_engine import JournalEngine

        # 見積→請求
        ei = EstimateInvoiceEngine("C001", "T1234567890123")
        est = ei.create_estimate("A社", "Web制作", [
            LineItem("開発", 1, "式", 1_000_000),
        ])
        ei.accept_estimate(est)
        inv = ei.estimate_to_invoice(est)

        # 請求額を仕訳に計上
        je = JournalEngine("C001")
        result = je.process_chat(
            f"A社 売上{inv.subtotal}円",
            entry_date=date(2025, 6, 1),
        )
        assert result["success"]
        assert result["entry"].is_balanced

    def test_full_accounting_cycle(self):
        """売上→経費→決算→税金の完全サイクル"""
        from backend.engines.journal_engine import JournalEngine
        from backend.engines.settlement_engine import generate_settlement
        from backend.engines.tax_engine import calc_total_tax

        je = JournalEngine("C001")
        je.process_chat("売上1000万円", entry_date=date(2025, 6, 1))
        je.process_chat("外注費300万円", entry_date=date(2025, 6, 5))
        je.process_chat("家賃50万円", entry_date=date(2025, 6, 10))
        je.process_chat("給与80万円", entry_date=date(2025, 6, 25))

        # 決算
        settlement = generate_settlement(
            je.ledger.entries, date(2025, 4, 1), date(2026, 3, 31)
        )
        assert settlement.trial_balance.is_balanced
        assert settlement.balance_sheet.is_balanced
        assert settlement.profit_and_loss.net_income > 0

        # 税金
        tax = calc_total_tax(settlement.profit_and_loss.net_income)
        assert tax.total_tax > 0
        assert 0.20 < tax.effective_rate < 0.40
