"""全エンジン検証スクリプト"""
import sys

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "OK", ""))
    except Exception as e:
        results.append((name, "NG", str(e)))

# === 1. numbering_engine ===
def test_numbering():
    from backend.engines.numbering_engine import (
        NumberingState, generate_company_id, generate_project_id,
        generate_staff_id, generate_transaction_id, generate_journal_id,
        generate_expense_id, generate_sales_id, generate_estimate_id,
        generate_invoice_id, generate_attendance_id,
        parse_id, extract_company_id, extract_project_id, extract_staff_id,
        filter_by_company, group_by_parent, generate_batch,
    )
    s = NumberingState()
    c1, s = generate_company_id(s)
    c2, s = generate_company_id(s)
    assert c1.id == "C001" and c2.id == "C002"
    p1, s = generate_project_id(s, "C001")
    assert p1.id == "P001-C001"
    s1, s = generate_staff_id(s, "C001")
    assert s1.id == "S001-C001"
    t1, s = generate_transaction_id(s, "P001-C001")
    assert t1.id == "T001-P001-C001"
    j1, s = generate_journal_id(s, "C001")
    assert j1.id == "J001-C001"
    e1, s = generate_expense_id(s, "C001")
    assert e1.id == "E001-C001"
    sl1, s = generate_sales_id(s, "C001")
    assert sl1.id == "SL001-C001"
    q1, s = generate_estimate_id(s, "C001")
    assert q1.id == "Q001-C001"
    iv1, s = generate_invoice_id(s, "C001")
    assert iv1.id == "IV001-C001"
    at1, s = generate_attendance_id(s, "S001-C001")
    assert at1.id == "AT001-S001-C001"
    parsed = parse_id("AT001-S001-C001")
    assert parsed.prefix == "AT" and parsed.seq == 1 and parsed.parent_id == "S001-C001"
    assert extract_company_id("AT001-S001-C001") == "C001"
    assert extract_project_id("T001-P001-C001") == "P001-C001"
    assert extract_staff_id("AT001-S001-C001") == "S001-C001"
    ids, s = generate_batch(s, generate_project_id, "C001", 3)
    assert len(ids) == 3 and ids[0].id == "P002-C001"
    all_ids = [c1.id, p1.id, sl1.id, "P001-C002"]
    assert len(filter_by_company(all_ids, "C001")) == 3

test("1. numbering_engine", test_numbering)

# === 2. journal_engine ===
def test_journal():
    from backend.engines.journal_engine import (
        JournalEngine, JournalEntry, JournalLine,
        ACCOUNTS, find_template, get_account, find_account_by_name, accounts_by_category,
        AccountCategory,
    )
    from datetime import date
    assert len(ACCOUNTS) > 50
    assert get_account("1100").name == "現金"
    assert find_account_by_name("売掛金").code == "1130"
    assets = accounts_by_category(AccountCategory.ASSET)
    assert len(assets) > 10
    tmpl = find_template("売上300万")
    assert tmpl and tmpl.name == "売上計上"
    engine = JournalEngine(company_id="C001")
    r = engine.process_chat("A社から売上300万円", entry_date=date(2025,6,1))
    assert r["success"]
    assert r["entry"].numbering_id == "J001-C001"
    assert r["entry"].is_balanced
    r2 = engine.process_chat("家賃20万円", entry_date=date(2025,6,15), project_id="P001-C001")
    assert r2["entry"].project_id == "P001-C001"
    pl = engine.get_pl()
    assert pl["売上高"]["total"] > 0
    bs = engine.get_bs()
    assert bs["負債・純資産合計"] == bs["資産の部"]["total"]

test("2. journal_engine", test_journal)

# === 3. profit_engine ===
def test_profit():
    from backend.engines.profit_engine import (
        ProfitEngine, CompanyConfig, Project, Staff, StaffAssignment,
    )
    cfg = CompanyConfig("test", 500000, 0.3, 50000000, 0.3)
    engine = ProfitEngine(cfg)
    projects = [
        Project("P001-C001", "A", "A社", "Web", 3000000, 1000000, 0, 2, 4, category="Web",
                staff=[StaffAssignment("S001-C001", "田中", 80, 3000)]),
        Project("P002-C001", "B", "B社", "App", 5000000, 2000000, 1, 3, 5, category="App"),
    ]
    tv = engine.calc_three_views(projects, 3)
    assert tv.future.revenue == 8000000
    pp = engine.calc_project_profits(projects, 3)
    assert len(pp) == 2
    staff = [Staff("S001-C001", "田中", "田中太郎", "Eng", 3000, 350000)]
    sp = engine.calc_all_staff_profits(staff, projects, 3)
    assert sp[0].total_hours == 80
    cp = engine.calc_category_profits(projects)
    assert len(cp) == 2
    mp = engine.calc_monthly_profit(projects)
    assert len(mp) == 12
    assert engine.breakeven_revenue() > 0

test("3. profit_engine", test_profit)

# === 4. tax_engine ===
def test_tax():
    from backend.engines.tax_engine import (
        calc_consumption_tax_inclusive, calc_consumption_tax_exclusive,
        calc_invoice_tax, InvoiceLineItem, TaxRate,
        calc_corporate_tax, calc_local_tax, calc_total_tax,
        calc_withholding_salary, calc_withholding_professional,
    )
    r = calc_consumption_tax_inclusive(11000)
    assert r.tax_exclusive == 10000 and r.tax_amount == 1000
    r2 = calc_consumption_tax_exclusive(10000)
    assert r2.tax_inclusive == 11000
    r3 = calc_consumption_tax_inclusive(10800, TaxRate.REDUCED)
    assert r3.tax_exclusive == 10000
    items = [
        InvoiceLineItem("A", 10000, TaxRate.STANDARD),
        InvoiceLineItem("B", 5000, TaxRate.REDUCED),
    ]
    summaries = calc_invoice_tax(items)
    assert len(summaries) == 2
    ct = calc_corporate_tax(10000000, is_sme=True)
    assert ct.corp_tax > 0
    lt = calc_local_tax(ct.corp_tax, 10000000)
    assert lt.total > 0
    tt = calc_total_tax(10000000)
    assert 0.2 < tt.effective_rate < 0.4
    wp = calc_withholding_professional(500000)
    assert wp.withholding_tax == int(500000 * 0.1021)

test("4. tax_engine", test_tax)

# === 5. settlement_engine ===
def test_settlement():
    from backend.engines.settlement_engine import generate_settlement, calc_trial_balance
    from backend.engines.journal_engine import JournalEngine
    from datetime import date
    engine = JournalEngine("C001")
    engine.process_chat("売上500万円", entry_date=date(2025,6,1))
    engine.process_chat("外注費100万円", entry_date=date(2025,6,10))
    engine.process_chat("家賃30万円", entry_date=date(2025,6,15))
    entries = engine.ledger.entries
    tb = calc_trial_balance(entries)
    assert tb.is_balanced
    result = generate_settlement(entries, date(2025,4,1), date(2026,3,31))
    assert result.entry_count == 3
    assert result.profit_and_loss.net_income > 0
    assert result.balance_sheet.is_balanced

test("5. settlement_engine", test_settlement)

# === 6. sales_engine ===
def test_sales():
    from backend.engines.sales_engine import SalesEngine, SalesTarget
    from datetime import date
    engine = SalesEngine(company_id="C001")
    s1 = engine.create_sales_record("A社", "Web", 3000000, date(2025,4,15), category="Web", cost=1000000)
    s2 = engine.create_sales_record("B社", "App", 5000000, date(2025,4,20), category="App", cost=2000000)
    s3 = engine.create_sales_record("A社", "保守", 500000, date(2025,5,10), category="保守")
    assert s1.id == "SL001-C001"
    summary = SalesEngine.summarize([s1, s2, s3])
    assert summary.total_amount == 8500000
    apr = SalesEngine.filter_by_month([s1, s2, s3], 2025, 4)
    assert len(apr) == 2
    by_client = SalesEngine.ranking_by_client([s1, s2, s3])
    assert by_client[0].key == "B社"
    monthly = SalesEngine.monthly_summary([s1, s2, s3], 2025)
    assert monthly[3]["amount"] == 8000000
    targets = [SalesTarget(2025, 4, 10000000)]
    ach = SalesEngine.calc_target_achievement([s1, s2, s3], targets, 2025, 4)
    assert ach[0].achievement_rate == 0.8
    yoy = SalesEngine.year_over_year([s1, s2, s3], 2025, 4)
    assert yoy["current"] == 8000000

test("6. sales_engine", test_sales)

# === 7. estimate_invoice_engine ===
def test_estimate_invoice():
    from backend.engines.estimate_invoice_engine import (
        EstimateInvoiceEngine, LineItem, EstimateStatus, InvoiceStatus,
    )
    from backend.engines.tax_engine import TaxRate
    from datetime import date
    engine = EstimateInvoiceEngine("C001", "T1234567890123")
    est = engine.create_estimate("A社", "Web制作", [
        LineItem("デザイン", 1, "式", 500000),
        LineItem("食品写真", 1, "式", 200000, tax_rate=TaxRate.REDUCED),
    ])
    assert est.id == "Q001-C001" and est.subtotal == 700000
    engine.accept_estimate(est)
    assert est.status == EstimateStatus.ACCEPTED
    inv = engine.estimate_to_invoice(est, payment_terms_days=30)
    assert inv.id == "IV001-C001" and inv.estimate_id == "Q001-C001"
    assert inv.invoice_registration_number == "T1234567890123"
    assert len(inv.tax_summary) == 2
    EstimateInvoiceEngine.record_payment(inv, 400000, date(2025,5,20))
    assert inv.status == InvoiceStatus.PARTIAL_PAID
    EstimateInvoiceEngine.record_payment(inv, inv.total - inv.paid_amount)
    assert inv.status == InvoiceStatus.PAID
    trace = EstimateInvoiceEngine.trace_estimate_to_payment(est, [inv])
    assert trace["remaining"] == 0

test("7. estimate_invoice_engine", test_estimate_invoice)

# === 8. project_engine ===
def test_project():
    from backend.engines.project_engine import (
        ProjectEngine, ProjectData, ProjectStatus, TaskItem,
    )
    from datetime import date
    p = ProjectData(
        id="P001-C001", company_id="C001", name="Webサイト",
        status=ProjectStatus.IN_PROGRESS, start_date=date(2025,4,1),
        deadline=date(2025,6,30), budget_revenue=3000000, budget_cost=1500000,
        actual_cost=500000,
        tasks=[
            TaskItem("T1", "デザイン", planned_hours=40, actual_hours=35, completed=True, progress=100),
            TaskItem("T2", "実装", planned_hours=80, actual_hours=20, progress=25,
                     start_date=date(2025,4,15), end_date=date(2025,6,15)),
        ],
    )
    prog = ProjectEngine.calc_progress(p, date(2025,5,15))
    assert prog.task_progress == 0.5
    assert prog.days_until_deadline == 46
    log = ProjectEngine.add_work_log(p, "S001-C001", "田中", 6.0, date(2025,5,15), task_id="T2")
    assert len(p.work_logs) == 1
    ok, _ = ProjectEngine.transition(p, ProjectStatus.INVOICED)
    assert ok
    bad, _ = ProjectEngine.transition(p, ProjectStatus.PROSPECT)
    assert not bad
    bva = ProjectEngine.budget_vs_actual(p)
    assert bva.cost_variance == -1000000
    gantt = ProjectEngine.gantt_data([p])
    assert len(gantt) == 2

test("8. project_engine", test_project)

# === 9. hr_engine ===
def test_hr():
    from backend.engines.hr_engine import HREngine, OvertimeDetail
    from datetime import date
    engine = HREngine("C001")
    emp = engine.create_employee("田中太郎", 350000, hire_date=date(2022,4,1), department="開発")
    assert emp.id == "S001-C001" and emp.hourly_rate > 0
    si = HREngine.calc_social_insurance(350000, include_employer=True)
    assert si["employee_total"] > 0 and si["employer_total"] > 0
    slip = HREngine.calc_payslip(emp, 2025, 5, overtime=OvertimeDetail(over_hours=20))
    assert slip.gross_pay > slip.base_salary
    assert slip.net_pay < slip.gross_pay
    assert slip.overtime_pay > 0
    days = HREngine.calc_paid_leave_grant(date(2022,4,1), date(2025,5,1))
    assert days == 12
    emp.paid_leave_days = 12
    ok, _ = HREngine.use_paid_leave(emp, 3)
    assert ok and emp.paid_leave_days == 9
    ot = OvertimeDetail(over_hours=50, late_night_hours=5, holiday_hours=8)
    warns = HREngine.check_overtime_limit(ot)
    assert any("45" in w for w in warns)
    slips = [HREngine.calc_payslip(emp, 2025, m) for m in range(1, 13)]
    yea = HREngine.year_end_adjustment(slips)
    assert yea["annual_gross"] > 0
    HREngine.retire_employee(emp, date(2025,12,31))
    assert emp.status.value == "退職"

test("9. hr_engine", test_hr)

# === 10. attendance_engine ===
def test_attendance():
    from backend.engines.attendance_engine import AttendanceEngine
    from datetime import date, time
    engine = AttendanceEngine("C001")
    rec = engine.clock_in("S001-C001", date(2025,5,15), time(9,0))
    assert rec.id == "AT001-S001-C001"
    AttendanceEngine.clock_out(rec, time(20,30))
    assert rec.actual_hours == 10.5 and rec.overtime_hours == 2.5
    AttendanceEngine.add_project_hours(rec, "P001-C001", "Web", 5.0)
    AttendanceEngine.add_project_hours(rec, "P002-C001", "App", 3.5)
    assert len(rec.project_hours) == 2
    parsed = AttendanceEngine.parse_work_report("Webサイト5時間 アプリ3.5時間")
    assert len(parsed) == 2
    summary = AttendanceEngine.monthly_summary([rec], 2025, 5)
    assert summary["work_days"] == 1 and summary["total_overtime"] == 2.5
    ot = AttendanceEngine.to_overtime_detail([rec], 2025, 5)
    assert ot.over_hours == 2.5
    ph = AttendanceEngine.project_hours_summary([rec])
    assert len(ph) == 2
    schedule = AttendanceEngine.generate_shift_schedule(["S001"], date(2025,5,12), 7)
    assert len(schedule) == 7

test("10. attendance_engine", test_attendance)

# === 11. chat_engine ===
def test_chat():
    from backend.engines.chat_engine import (
        ChatEngine, MessageType, ChatType, parse_chat_message, STAMPS,
    )
    p1 = parse_chat_message("おはようございます。出勤します")
    assert p1.attendance == "出勤"
    p2 = parse_chat_message("お疲れ様です。退勤します")
    assert p2.attendance == "退勤"
    p3 = parse_chat_message("Webサイト5時間 アプリ3時間")
    assert len(p3.project_entries) == 2
    p4 = parse_chat_message("タクシー2500円")
    assert p4.expense and p4.expense["amount"] == 2500
    room = ChatEngine.create_room("team", ["S001", "S002", "S003"])
    assert room.chat_type == ChatType.GROUP
    msg1 = ChatEngine.send_message(room, "S001", "田中", "出勤します")
    assert msg1.message_type == MessageType.WORK_REPORT
    msg2 = ChatEngine.send_message(room, "S001", "田中", "Web5時間")
    assert msg2.detected_work[0]["hours"] == 5.0
    msg3 = ChatEngine.send_message(room, "S002", "鈴木", "了解です")
    assert msg3.message_type == MessageType.TEXT
    img = ChatEngine.send_image(room, "S001", "田中", "/tmp/photo.jpg")
    assert img.message_type == MessageType.IMAGE
    stmp = ChatEngine.send_stamp(room, "S003", "佐藤", "ok")
    assert stmp.content == "了解"
    assert ChatEngine.unread_count(room, "S003") > 0
    ChatEngine.mark_room_as_read(room, "S003")
    assert ChatEngine.unread_count(room, "S003") == 0
    reports = ChatEngine.extract_work_reports(room)
    assert len(reports) >= 2
    hours = ChatEngine.aggregate_daily_hours(room.messages)
    assert any(h["hours"] == 5.0 for h in hours)
    assert len(STAMPS) >= 10

test("11. chat_engine", test_chat)

# === 12. asset_engine ===
def test_asset():
    from backend.engines.asset_engine import (
        AssetEngine, FixedAsset, AccountsReceivable,
        DepreciationMethod, AssetStatus,
    )
    from backend.engines.profit_engine import CompanyConfig, Project
    cfg = CompanyConfig("test", 500000, 0.3, 50000000, 0.3)
    engine = AssetEngine(cfg)
    projects = [
        Project("P001-C001", "A", "A社", "Web", 3000000, 1000000, 0, 2, 4),
        Project("P002-C001", "B", "B社", "App", 5000000, 2000000, 1, 3, 5),
    ]
    # 売掛金一覧
    ar = engine.accounts_receivable(projects, 3)
    assert len(ar) == 2
    assert ar[0].status == "請求済"
    # 未回収合計
    total = engine.total_receivable(projects, 3)
    assert total == 8000000  # 両方とも請求済・未入金
    # 固定資産取得 (定額法)
    pc = AssetEngine.acquire_asset("PC", 300000, "工具器具備品")
    assert pc.useful_life == 5
    assert pc.annual_depreciation == 59999  # (300000 - 1) / 5
    assert pc.book_value == 300000
    # 1年分の償却を実行
    dep = AssetEngine.process_annual_depreciation(pc)
    assert dep == 59999
    assert pc.book_value == 300000 - 59999
    # 定率法
    server = AssetEngine.acquire_asset("サーバー", 500000, "工具器具備品",
                                        method=DepreciationMethod.DECLINING_BALANCE)
    assert server.annual_depreciation > 0
    # 償却スケジュール
    schedule = AssetEngine.depreciation_schedule(pc)
    assert len(schedule) == 5
    assert schedule[-1].ending_value == 1  # 残存価額 (備忘価額)
    # 少額資産判定
    assert AssetEngine.classify_asset(50000) == "消耗品費"
    assert AssetEngine.classify_asset(150000) == "一括償却"
    assert AssetEngine.classify_asset(250000) == "即時償却"
    assert AssetEngine.classify_asset(500000) == "通常償却"
    # 売却
    result = AssetEngine.sell_asset(pc, 200000)
    assert result["gain"] > 0 or result["loss"] >= 0
    assert pc.status == AssetStatus.SOLD
    # サマリ (server is still active)
    summary = AssetEngine.asset_summary([pc, server])
    assert summary["total_count"] == 1  # pcは売却済

test("12. asset_engine", test_asset)

# === 13. cash_flow_engine ===
def test_cash_flow():
    from backend.engines.cash_flow_engine import CashFlowEngine, MonthlyCashFlow, FinancingItem
    from backend.engines.profit_engine import CompanyConfig, Project
    cfg = CompanyConfig("test", 500000, 0.3, 50000000, 0.3)
    engine = CashFlowEngine(cfg)
    projects = [
        Project("P001-C001", "A", "A社", "Web", 3000000, 1000000, 0, 2, 4),
        Project("P002-C001", "B", "B社", "App", 5000000, 2000000, 1, 3, 6),
    ]
    # 12ヶ月CF
    flows = engine.monthly_cash_flows(projects)
    assert len(flows) == 12
    # 4月(index=0): 原価1M + 固定500K = outflow 1.5M, inflow 0
    assert flows[0].outflow == 1500000
    # 入金月(index=4): A社の3M入金
    assert flows[4].inflow == 3000000
    # 最悪月
    worst = engine.worst_month(projects)
    assert isinstance(worst, MonthlyCashFlow)
    # 黒字転換
    pos = engine.months_until_positive(projects)
    # pos は None or int
    # 予測
    forecast = engine.forecast(projects, beginning_cash=1000000)
    assert forecast.total_inflow == 8000000
    assert forecast.worst_month is not None
    # 運転資金分析
    wc = engine.working_capital_analysis(projects, 3)
    assert wc.accounts_receivable >= 0
    # バーンレート
    br = engine.burn_rate(projects)
    assert br > 0
    # ランウェイ
    rw = engine.runway_months(projects, 3000000)
    assert rw > 0
    # 財務CF付き
    financing = [FinancingItem(0, 5000000, "銀行借入")]
    flows2 = engine.monthly_cash_flows(projects, financing=financing)
    assert flows2[0].financing == 5000000

test("13. cash_flow_engine", test_cash_flow)

# === 結果出力 ===
print("=" * 70)
print(f"{'#':<3} {'Engine':<35} {'Result':<6} {'Error'}")
print("=" * 70)
all_ok = True
for name, status, err in results:
    mark = "PASS" if status == "OK" else "FAIL"
    print(f"    {name:<33} {mark:<6} {err[:50] if err else ''}")
    if status != "OK":
        all_ok = False
print("=" * 70)
ok_count = sum(1 for _, s, _ in results if s == "OK")
ng_count = sum(1 for _, s, _ in results if s != "OK")
print(f"    Total: {len(results)} engines, {ok_count} passed, {ng_count} failed")
print("=" * 70)
if not all_ok:
    sys.exit(1)
