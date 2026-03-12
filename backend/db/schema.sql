-- =============================================================
-- katana-demo: Supabase マルチテナント DB スキーマ
-- 70,000社対応 / 全テーブル company_id + RLS
-- =============================================================

-- 拡張機能
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================
-- 1. companies (企業マスタ)
-- =============================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_number  TEXT NOT NULL UNIQUE,                    -- C001 形式
    name            TEXT NOT NULL,
    name_kana       TEXT,
    postal_code     TEXT,
    address         TEXT,
    phone           TEXT,
    email           TEXT,
    representative  TEXT,                                    -- 代表者名
    capital         BIGINT DEFAULT 0,                        -- 資本金
    fiscal_start_month INT DEFAULT 4,                        -- 決算開始月
    employee_count  INT DEFAULT 0,
    industry        TEXT,
    invoice_number  TEXT,                                    -- インボイス登録番号 T+13桁
    is_sme          BOOLEAN DEFAULT TRUE,                    -- 中小企業フラグ
    plan            TEXT DEFAULT 'free',                     -- サブスクプラン
    status          TEXT DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_number ON companies (company_number);
CREATE INDEX idx_companies_status ON companies (status);

-- =============================================================
-- 2. users (ユーザー / Supabase Auth連携)
-- =============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    display_name    TEXT,
    role            TEXT DEFAULT 'member',                   -- owner | admin | member | viewer
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_company ON users (company_id);
CREATE INDEX idx_users_email ON users (email);

-- =============================================================
-- 3. account_master (勘定科目マスタ)
-- =============================================================
CREATE TABLE account_master (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,                           -- 1100, 5200 等
    name            TEXT NOT NULL,                           -- 現金, 給与手当 等
    category        TEXT NOT NULL,                           -- 資産/負債/純資産/収益/費用
    normal_balance  TEXT NOT NULL,                           -- debit / credit
    sub_category    TEXT DEFAULT '',                         -- 流動資産, 販管費 等
    tax_category    TEXT DEFAULT '',                         -- 課税/非課税/不課税
    description     TEXT DEFAULT '',
    is_active       BOOLEAN DEFAULT TRUE,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, code)
);

CREATE INDEX idx_account_master_company ON account_master (company_id);
CREATE INDEX idx_account_master_category ON account_master (company_id, category);

-- =============================================================
-- 4. journals (仕訳ヘッダ)
-- =============================================================
CREATE TABLE journals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    journal_number  TEXT NOT NULL,                           -- J001-C001 形式
    journal_date    DATE NOT NULL,
    description     TEXT DEFAULT '',
    category        TEXT DEFAULT '',                         -- 売上/仕入/経費/給与/資産/税金/その他
    source          TEXT DEFAULT 'manual',                   -- manual/chat/auto
    source_id       UUID,                                   -- 元データのID (チャット等)
    status          TEXT DEFAULT 'draft',                    -- draft/confirmed/posted
    fiscal_year     INT,
    fiscal_month    INT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, journal_number)
);

CREATE INDEX idx_journals_company ON journals (company_id);
CREATE INDEX idx_journals_date ON journals (company_id, journal_date);
CREATE INDEX idx_journals_fiscal ON journals (company_id, fiscal_year, fiscal_month);
CREATE INDEX idx_journals_status ON journals (company_id, status);
CREATE INDEX idx_journals_category ON journals (company_id, category);

-- =============================================================
-- 5. journal_entries (仕訳明細 / 借方・貸方)
-- =============================================================
CREATE TABLE journal_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    journal_id      UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    line_no         INT NOT NULL,
    side            TEXT NOT NULL CHECK (side IN ('debit', 'credit')),
    account_code    TEXT NOT NULL,
    account_name    TEXT NOT NULL,
    amount          BIGINT NOT NULL CHECK (amount >= 0),
    tax_rate        NUMERIC(5,3) DEFAULT 0,                 -- 0.10, 0.08, 0
    tax_amount      BIGINT DEFAULT 0,
    description     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_journal_entries_company ON journal_entries (company_id);
CREATE INDEX idx_journal_entries_journal ON journal_entries (journal_id);
CREATE INDEX idx_journal_entries_account ON journal_entries (company_id, account_code);

-- =============================================================
-- 6. employees (従業員マスタ)
-- =============================================================
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    employee_number TEXT NOT NULL,                           -- S001-C001 形式
    user_id         UUID REFERENCES users(id),              -- Supabase auth連携 (nullable)
    name            TEXT NOT NULL,
    name_kana       TEXT,
    email           TEXT,
    department      TEXT DEFAULT '',
    position        TEXT DEFAULT '',
    employment_type TEXT DEFAULT '正社員',                    -- 正社員/契約/パート/役員
    hire_date       DATE,
    birth_date      DATE,
    -- 給与情報
    base_salary     BIGINT DEFAULT 0,                       -- 基本給 (月額)
    hourly_rate     BIGINT DEFAULT 0,                       -- 時給 (パート用)
    commute_allow   BIGINT DEFAULT 0,                       -- 通勤手当
    -- 社会保険
    health_ins_grade INT,                                   -- 健康保険等級
    pension_grade    INT,                                   -- 厚生年金等級
    employment_ins   BOOLEAN DEFAULT TRUE,                  -- 雇用保険加入
    -- 有給
    paid_leave_balance NUMERIC(4,1) DEFAULT 0,              -- 有給残日数
    paid_leave_granted_date DATE,
    -- ステータス
    is_active       BOOLEAN DEFAULT TRUE,
    resigned_date   DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, employee_number)
);

CREATE INDEX idx_employees_company ON employees (company_id);
CREATE INDEX idx_employees_active ON employees (company_id, is_active);
CREATE INDEX idx_employees_department ON employees (company_id, department);

-- =============================================================
-- 7. projects (案件マスタ)
-- =============================================================
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    project_number  TEXT NOT NULL,                           -- P001-C001 形式
    project_name    TEXT NOT NULL,
    client_name     TEXT DEFAULT '',
    -- 金額
    revenue         BIGINT DEFAULT 0,                       -- 売上額
    cost            BIGINT DEFAULT 0,                       -- 原価
    budget          BIGINT DEFAULT 0,                       -- 予算
    -- タイミング (月インデックス 0-11)
    contract_month  INT,
    start_month     INT,
    delivery_month  INT,
    invoice_month   INT,
    payment_month   INT,
    -- ステータス
    status          TEXT DEFAULT '受注前',                    -- 受注前/契約済/進行中/納品済/検収済/請求済/入金済/完了/中止
    progress        NUMERIC(5,2) DEFAULT 0,                 -- 進捗率 0-100
    -- 担当
    manager_id      UUID REFERENCES employees(id),
    department      TEXT DEFAULT '',
    -- メモ
    description     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, project_number)
);

CREATE INDEX idx_projects_company ON projects (company_id);
CREATE INDEX idx_projects_status ON projects (company_id, status);
CREATE INDEX idx_projects_client ON projects (company_id, client_name);
CREATE INDEX idx_projects_payment ON projects (company_id, payment_month);

-- =============================================================
-- 8. estimates (見積書)
-- =============================================================
CREATE TABLE estimates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    estimate_number TEXT NOT NULL,                           -- Q001-C001 形式
    project_id      UUID REFERENCES projects(id),
    client_name     TEXT NOT NULL,
    title           TEXT DEFAULT '',
    -- 金額
    subtotal        BIGINT DEFAULT 0,                       -- 税抜合計
    tax_amount      BIGINT DEFAULT 0,                       -- 消費税額
    total           BIGINT DEFAULT 0,                       -- 税込合計
    -- 日付
    issue_date      DATE,
    valid_until     DATE,
    -- ステータス
    status          TEXT DEFAULT '作成中',                    -- 作成中/送付済/承認/却下/失効
    -- 明細 (JSONB)
    line_items      JSONB DEFAULT '[]'::jsonb,
    notes           TEXT DEFAULT '',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, estimate_number)
);

CREATE INDEX idx_estimates_company ON estimates (company_id);
CREATE INDEX idx_estimates_project ON estimates (company_id, project_id);
CREATE INDEX idx_estimates_status ON estimates (company_id, status);

-- =============================================================
-- 9. invoices (請求書)
-- =============================================================
CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    invoice_number  TEXT NOT NULL,                           -- IV001-C001 形式
    project_id      UUID REFERENCES projects(id),
    estimate_id     UUID REFERENCES estimates(id),
    client_name     TEXT NOT NULL,
    title           TEXT DEFAULT '',
    -- 金額
    subtotal        BIGINT DEFAULT 0,
    tax_amount      BIGINT DEFAULT 0,
    total           BIGINT DEFAULT 0,
    -- 日付
    issue_date      DATE,
    due_date        DATE,
    payment_date    DATE,                                   -- 実際の入金日
    -- インボイス制度
    invoice_reg_number TEXT,                                 -- T+13桁
    -- ステータス
    status          TEXT DEFAULT '作成中',                    -- 作成中/送付済/入金済/一部入金/期限超過
    -- 明細 (JSONB)
    line_items      JSONB DEFAULT '[]'::jsonb,
    -- 税率別内訳 (JSONB)
    tax_summary     JSONB DEFAULT '[]'::jsonb,
    notes           TEXT DEFAULT '',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, invoice_number)
);

CREATE INDEX idx_invoices_company ON invoices (company_id);
CREATE INDEX idx_invoices_project ON invoices (company_id, project_id);
CREATE INDEX idx_invoices_status ON invoices (company_id, status);
CREATE INDEX idx_invoices_due ON invoices (company_id, due_date);
CREATE INDEX idx_invoices_payment ON invoices (company_id, payment_date);

-- =============================================================
-- 10. payments (入出金記録)
-- =============================================================
CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    payment_date    DATE NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('inflow', 'outflow')),
    amount          BIGINT NOT NULL CHECK (amount >= 0),
    method          TEXT DEFAULT '銀行振込',                  -- 銀行振込/現金/クレジットカード/口座振替
    -- 関連
    invoice_id      UUID REFERENCES invoices(id),
    project_id      UUID REFERENCES projects(id),
    journal_id      UUID REFERENCES journals(id),
    counterparty    TEXT DEFAULT '',                         -- 取引先
    description     TEXT DEFAULT '',
    -- ステータス
    status          TEXT DEFAULT 'confirmed',                -- pending/confirmed/cancelled
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_company ON payments (company_id);
CREATE INDEX idx_payments_date ON payments (company_id, payment_date);
CREATE INDEX idx_payments_direction ON payments (company_id, direction);
CREATE INDEX idx_payments_invoice ON payments (company_id, invoice_id);

-- =============================================================
-- 11. expenses (経費)
-- =============================================================
CREATE TABLE expenses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    expense_number  TEXT NOT NULL,                           -- E001-C001 形式
    employee_id     UUID REFERENCES employees(id),
    expense_date    DATE NOT NULL,
    account_code    TEXT NOT NULL,                           -- 勘定科目コード
    account_name    TEXT NOT NULL,
    amount          BIGINT NOT NULL CHECK (amount >= 0),
    tax_rate        NUMERIC(5,3) DEFAULT 0.10,
    tax_amount      BIGINT DEFAULT 0,
    -- 詳細
    description     TEXT DEFAULT '',
    vendor          TEXT DEFAULT '',                         -- 支払先
    payment_method  TEXT DEFAULT '現金',
    receipt_url     TEXT,                                    -- レシート画像URL
    -- 承認
    status          TEXT DEFAULT '申請中',                    -- 申請中/承認済/却下/精算済
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    -- 関連
    project_id      UUID REFERENCES projects(id),
    journal_id      UUID REFERENCES journals(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, expense_number)
);

CREATE INDEX idx_expenses_company ON expenses (company_id);
CREATE INDEX idx_expenses_employee ON expenses (company_id, employee_id);
CREATE INDEX idx_expenses_date ON expenses (company_id, expense_date);
CREATE INDEX idx_expenses_status ON expenses (company_id, status);
CREATE INDEX idx_expenses_account ON expenses (company_id, account_code);

-- =============================================================
-- 12. attendance (勤怠)
-- =============================================================
CREATE TABLE attendance (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    work_date       DATE NOT NULL,
    -- 打刻
    clock_in        TIMESTAMPTZ,
    clock_out       TIMESTAMPTZ,
    -- 時間 (分単位)
    work_minutes    INT DEFAULT 0,
    break_minutes   INT DEFAULT 0,
    overtime_minutes INT DEFAULT 0,
    late_night_minutes INT DEFAULT 0,                       -- 深夜 (22:00-5:00)
    holiday_minutes INT DEFAULT 0,
    -- 種別
    attendance_type TEXT DEFAULT '出勤',                      -- 出勤/有給/欠勤/半休/振休/特別休暇
    -- 案件別工数 (JSONB)
    project_hours   JSONB DEFAULT '[]'::jsonb,              -- [{project_id, hours, description}]
    -- メモ
    memo            TEXT DEFAULT '',
    source          TEXT DEFAULT 'manual',                   -- manual/chat/system
    source_id       UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, employee_id, work_date)
);

CREATE INDEX idx_attendance_company ON attendance (company_id);
CREATE INDEX idx_attendance_employee ON attendance (company_id, employee_id);
CREATE INDEX idx_attendance_date ON attendance (company_id, work_date);
CREATE INDEX idx_attendance_type ON attendance (company_id, attendance_type);

-- =============================================================
-- 13. inventory (在庫 / 固定資産)
-- =============================================================
CREATE TABLE inventory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    asset_number    TEXT NOT NULL,                           -- AT001-S001-C001 形式
    name            TEXT NOT NULL,
    -- 区分
    asset_class     TEXT DEFAULT 'fixed_asset',             -- fixed_asset / inventory / consumable
    asset_type      TEXT DEFAULT '工具器具備品',
    -- 金額
    acquisition_value BIGINT DEFAULT 0,                     -- 取得価額
    book_value      BIGINT DEFAULT 0,                       -- 帳簿価額
    accumulated_depreciation BIGINT DEFAULT 0,              -- 減価償却累計額
    residual_value  BIGINT DEFAULT 1,                       -- 残存価額
    -- 償却
    depreciation_method TEXT DEFAULT '定額法',               -- 定額法/定率法
    useful_life     INT DEFAULT 5,                          -- 耐用年数
    annual_depreciation BIGINT DEFAULT 0,
    -- 日付
    acquisition_date DATE,
    disposal_date    DATE,
    -- ステータス
    status          TEXT DEFAULT '使用中',                    -- 使用中/除却済/売却済
    location        TEXT DEFAULT '',
    memo            TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, asset_number)
);

CREATE INDEX idx_inventory_company ON inventory (company_id);
CREATE INDEX idx_inventory_class ON inventory (company_id, asset_class);
CREATE INDEX idx_inventory_status ON inventory (company_id, status);
CREATE INDEX idx_inventory_type ON inventory (company_id, asset_type);

-- =============================================================
-- 14. chat_channels (チャットチャネル)
-- =============================================================
CREATE TABLE chat_channels (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    channel_type    TEXT DEFAULT 'room',                     -- room / direct / bot
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    members         UUID[] DEFAULT '{}',                     -- user_id配列
    is_archived     BOOLEAN DEFAULT FALSE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_channels_company ON chat_channels (company_id);
CREATE INDEX idx_chat_channels_type ON chat_channels (company_id, channel_type);

-- =============================================================
-- 15. chat_messages (チャットメッセージ)
-- =============================================================
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES users(id),
    -- メッセージ
    message_type    TEXT DEFAULT 'text',                     -- text/stamp/image/file/system
    content         TEXT DEFAULT '',
    -- メタデータ
    metadata        JSONB DEFAULT '{}'::jsonb,              -- 画像URL, ファイル情報等
    -- 自動検出結果
    detected_type   TEXT,                                   -- work_report/attendance/expense/none
    detected_data   JSONB,                                  -- 検出されたデータ
    -- 既読
    read_by         UUID[] DEFAULT '{}',
    -- 関連
    reply_to        UUID REFERENCES chat_messages(id),
    -- ステータス
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_company ON chat_messages (company_id);
CREATE INDEX idx_chat_messages_channel ON chat_messages (channel_id, created_at);
CREATE INDEX idx_chat_messages_sender ON chat_messages (company_id, sender_id);
CREATE INDEX idx_chat_messages_detected ON chat_messages (company_id, detected_type);
CREATE INDEX idx_chat_messages_created ON chat_messages (company_id, created_at);

-- =============================================================
-- 16. subscriptions (サブスクリプション / 課金)
-- =============================================================
CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    plan            TEXT NOT NULL DEFAULT 'free',            -- free/starter/business/enterprise
    status          TEXT DEFAULT 'active',                   -- active/cancelled/past_due/trialing
    -- 期間
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    trial_end       TIMESTAMPTZ,
    -- Stripe連携
    stripe_customer_id    TEXT,
    stripe_subscription_id TEXT,
    -- 制限
    max_users       INT DEFAULT 3,
    max_projects    INT DEFAULT 10,
    max_storage_mb  INT DEFAULT 100,
    -- 金額
    monthly_price   INT DEFAULT 0,                          -- 月額 (円)
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_company ON subscriptions (company_id);
CREATE INDEX idx_subscriptions_status ON subscriptions (status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions (stripe_customer_id);

-- =============================================================
-- 17. numbering_sequences (採番シーケンス)
-- =============================================================
CREATE TABLE numbering_sequences (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    entity_type     TEXT NOT NULL,                           -- company/project/staff/journal/expense/sales/estimate/invoice/attendance
    prefix          TEXT NOT NULL,                           -- C/P/S/J/E/SL/Q/IV/AT
    current_number  INT DEFAULT 0,                          -- 現在の最大番号
    parent_id       TEXT,                                   -- 親エンティティID (P001-C001のC001部分)
    format_pattern  TEXT DEFAULT '{prefix}{number:03d}',    -- フォーマットパターン
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, entity_type, COALESCE(parent_id, ''))
);

CREATE INDEX idx_numbering_company ON numbering_sequences (company_id);
CREATE INDEX idx_numbering_entity ON numbering_sequences (company_id, entity_type);


-- =============================================================
-- Row Level Security (RLS) ポリシー
-- =============================================================

-- ヘルパー関数: 現在のユーザーのcompany_idを取得
CREATE OR REPLACE FUNCTION get_user_company_id()
RETURNS UUID AS $$
    SELECT company_id FROM users WHERE id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ----- companies -----
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "companies_select" ON companies
    FOR SELECT USING (id = get_user_company_id());

CREATE POLICY "companies_update" ON companies
    FOR UPDATE USING (id = get_user_company_id());

-- ----- users -----
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select" ON users
    FOR SELECT USING (company_id = get_user_company_id());

CREATE POLICY "users_insert" ON users
    FOR INSERT WITH CHECK (company_id = get_user_company_id());

CREATE POLICY "users_update" ON users
    FOR UPDATE USING (company_id = get_user_company_id());

-- ----- 共通テンプレート: company_id ベースの全CRUD -----
-- マクロ的に各テーブルに適用

-- account_master
ALTER TABLE account_master ENABLE ROW LEVEL SECURITY;
CREATE POLICY "account_master_select" ON account_master FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "account_master_insert" ON account_master FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "account_master_update" ON account_master FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "account_master_delete" ON account_master FOR DELETE USING (company_id = get_user_company_id());

-- journals
ALTER TABLE journals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "journals_select" ON journals FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "journals_insert" ON journals FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "journals_update" ON journals FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "journals_delete" ON journals FOR DELETE USING (company_id = get_user_company_id());

-- journal_entries
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "journal_entries_select" ON journal_entries FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "journal_entries_insert" ON journal_entries FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "journal_entries_update" ON journal_entries FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "journal_entries_delete" ON journal_entries FOR DELETE USING (company_id = get_user_company_id());

-- employees
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
CREATE POLICY "employees_select" ON employees FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "employees_insert" ON employees FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "employees_update" ON employees FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "employees_delete" ON employees FOR DELETE USING (company_id = get_user_company_id());

-- projects
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "projects_select" ON projects FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "projects_insert" ON projects FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "projects_update" ON projects FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "projects_delete" ON projects FOR DELETE USING (company_id = get_user_company_id());

-- estimates
ALTER TABLE estimates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "estimates_select" ON estimates FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "estimates_insert" ON estimates FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "estimates_update" ON estimates FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "estimates_delete" ON estimates FOR DELETE USING (company_id = get_user_company_id());

-- invoices
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "invoices_select" ON invoices FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "invoices_insert" ON invoices FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "invoices_update" ON invoices FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "invoices_delete" ON invoices FOR DELETE USING (company_id = get_user_company_id());

-- payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "payments_select" ON payments FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "payments_insert" ON payments FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "payments_update" ON payments FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "payments_delete" ON payments FOR DELETE USING (company_id = get_user_company_id());

-- expenses
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "expenses_select" ON expenses FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "expenses_insert" ON expenses FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "expenses_update" ON expenses FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "expenses_delete" ON expenses FOR DELETE USING (company_id = get_user_company_id());

-- attendance
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "attendance_select" ON attendance FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "attendance_insert" ON attendance FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "attendance_update" ON attendance FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "attendance_delete" ON attendance FOR DELETE USING (company_id = get_user_company_id());

-- inventory
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "inventory_select" ON inventory FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "inventory_insert" ON inventory FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "inventory_update" ON inventory FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "inventory_delete" ON inventory FOR DELETE USING (company_id = get_user_company_id());

-- chat_channels
ALTER TABLE chat_channels ENABLE ROW LEVEL SECURITY;
CREATE POLICY "chat_channels_select" ON chat_channels FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "chat_channels_insert" ON chat_channels FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "chat_channels_update" ON chat_channels FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "chat_channels_delete" ON chat_channels FOR DELETE USING (company_id = get_user_company_id());

-- chat_messages
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "chat_messages_select" ON chat_messages FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "chat_messages_insert" ON chat_messages FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "chat_messages_update" ON chat_messages FOR UPDATE USING (company_id = get_user_company_id());
CREATE POLICY "chat_messages_delete" ON chat_messages FOR DELETE USING (company_id = get_user_company_id());

-- subscriptions
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "subscriptions_select" ON subscriptions FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "subscriptions_insert" ON subscriptions FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "subscriptions_update" ON subscriptions FOR UPDATE USING (company_id = get_user_company_id());

-- numbering_sequences
ALTER TABLE numbering_sequences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "numbering_sequences_select" ON numbering_sequences FOR SELECT USING (company_id = get_user_company_id());
CREATE POLICY "numbering_sequences_insert" ON numbering_sequences FOR INSERT WITH CHECK (company_id = get_user_company_id());
CREATE POLICY "numbering_sequences_update" ON numbering_sequences FOR UPDATE USING (company_id = get_user_company_id());


-- =============================================================
-- updated_at 自動更新トリガー
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_at を持つ全テーブルにトリガー適用
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'companies', 'users', 'journals', 'employees', 'projects',
            'estimates', 'invoices', 'expenses', 'attendance', 'inventory',
            'chat_channels', 'subscriptions', 'numbering_sequences'
        ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- =============================================================
-- 勘定科目マスタ: デフォルトデータ挿入関数
-- (企業登録時に呼び出す)
-- =============================================================
CREATE OR REPLACE FUNCTION insert_default_accounts(p_company_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO account_master (company_id, code, name, category, normal_balance, sub_category, tax_category, sort_order) VALUES
    -- 資産 (1xxx) - 流動資産
    (p_company_id, '1100', '現金',             '資産', 'debit', '流動資産', '不課税', 100),
    (p_company_id, '1110', '普通預金',          '資産', 'debit', '流動資産', '不課税', 110),
    (p_company_id, '1120', '当座預金',          '資産', 'debit', '流動資産', '不課税', 120),
    (p_company_id, '1130', '売掛金',            '資産', 'debit', '流動資産', '不課税', 130),
    (p_company_id, '1140', '受取手形',          '資産', 'debit', '流動資産', '不課税', 140),
    (p_company_id, '1150', '商品',             '資産', 'debit', '流動資産', '不課税', 150),
    (p_company_id, '1160', '仕掛品',            '資産', 'debit', '流動資産', '不課税', 160),
    (p_company_id, '1170', '貯蔵品',            '資産', 'debit', '流動資産', '不課税', 170),
    (p_company_id, '1180', '前払費用',          '資産', 'debit', '流動資産', '不課税', 180),
    (p_company_id, '1190', '前払金',            '資産', 'debit', '流動資産', '不課税', 190),
    (p_company_id, '1200', '未収入金',          '資産', 'debit', '流動資産', '不課税', 200),
    (p_company_id, '1210', '仮払消費税',         '資産', 'debit', '流動資産', '不課税', 210),
    -- 資産 - 有形固定資産
    (p_company_id, '1300', '建物',             '資産', 'debit', '有形固定資産', '不課税', 300),
    (p_company_id, '1310', '機械装置',          '資産', 'debit', '有形固定資産', '不課税', 310),
    (p_company_id, '1320', '車両運搬具',         '資産', 'debit', '有形固定資産', '不課税', 320),
    (p_company_id, '1330', '工具器具備品',       '資産', 'debit', '有形固定資産', '不課税', 330),
    (p_company_id, '1340', '土地',             '資産', 'debit', '有形固定資産', '不課税', 340),
    (p_company_id, '1350', '建設仮勘定',         '資産', 'debit', '有形固定資産', '不課税', 350),
    (p_company_id, '1390', '建物減価償却累計額',    '資産', 'credit', '有形固定資産', '不課税', 390),
    (p_company_id, '1391', '機械装置減価償却累計額',  '資産', 'credit', '有形固定資産', '不課税', 391),
    (p_company_id, '1392', '車両運搬具減価償却累計額', '資産', 'credit', '有形固定資産', '不課税', 392),
    (p_company_id, '1393', '工具器具備品減価償却累計額', '資産', 'credit', '有形固定資産', '不課税', 393),
    -- 資産 - 無形固定資産
    (p_company_id, '1400', 'ソフトウェア',       '資産', 'debit', '無形固定資産', '不課税', 400),
    (p_company_id, '1410', 'のれん',            '資産', 'debit', '無形固定資産', '不課税', 410),
    -- 資産 - 投資その他
    (p_company_id, '1500', '投資有価証券',       '資産', 'debit', '投資その他', '不課税', 500),
    (p_company_id, '1510', '長期貸付金',         '資産', 'debit', '投資その他', '不課税', 510),
    (p_company_id, '1520', '差入保証金',         '資産', 'debit', '投資その他', '不課税', 520),

    -- 負債 (2xxx) - 流動負債
    (p_company_id, '2100', '買掛金',            '負債', 'credit', '流動負債', '不課税', 600),
    (p_company_id, '2110', '支払手形',          '負債', 'credit', '流動負債', '不課税', 610),
    (p_company_id, '2120', '短期借入金',         '負債', 'credit', '流動負債', '不課税', 620),
    (p_company_id, '2130', '前受金',            '負債', 'credit', '流動負債', '不課税', 630),
    (p_company_id, '2140', '未払費用',          '負債', 'credit', '流動負債', '不課税', 640),
    (p_company_id, '2150', '未払法人税等',       '負債', 'credit', '流動負債', '不課税', 650),
    (p_company_id, '2160', '未払消費税',         '負債', 'credit', '流動負債', '不課税', 660),
    (p_company_id, '2170', '仮受消費税',         '負債', 'credit', '流動負債', '不課税', 670),
    (p_company_id, '2180', '預り金',            '負債', 'credit', '流動負債', '不課税', 680),
    (p_company_id, '2190', '源泉所得税預り金',    '負債', 'credit', '流動負債', '不課税', 690),
    (p_company_id, '2200', '社会保険料預り金',    '負債', 'credit', '流動負債', '不課税', 700),
    -- 負債 - 固定負債
    (p_company_id, '2300', '長期借入金',         '負債', 'credit', '固定負債', '不課税', 710),
    (p_company_id, '2310', '退職給付引当金',      '負債', 'credit', '固定負債', '不課税', 720),

    -- 純資産 (3xxx)
    (p_company_id, '3100', '資本金',            '純資産', 'credit', '株主資本', '', 800),
    (p_company_id, '3110', '資本準備金',         '純資産', 'credit', '株主資本', '', 810),
    (p_company_id, '3200', '繰越利益剰余金',     '純資産', 'credit', '株主資本', '', 820),
    (p_company_id, '3210', '利益準備金',         '純資産', 'credit', '株主資本', '', 830),

    -- 収益 (4xxx)
    (p_company_id, '4100', '売上高',            '収益', 'credit', '売上高', '課税', 900),
    (p_company_id, '4110', '役務収益',          '収益', 'credit', '売上高', '課税', 910),
    (p_company_id, '4200', '受取利息',          '収益', 'credit', '営業外収益', '非課税', 920),
    (p_company_id, '4210', '受取配当金',         '収益', 'credit', '営業外収益', '不課税', 930),
    (p_company_id, '4300', '固定資産売却益',      '収益', 'credit', '特別利益', '課税', 940),
    (p_company_id, '4900', '雑収入',            '収益', 'credit', '営業外収益', '課税', 950),

    -- 費用 (5xxx) - 売上原価
    (p_company_id, '5100', '売上原価',          '費用', 'debit', '売上原価', '課税', 1000),
    (p_company_id, '5110', '仕入高',            '費用', 'debit', '売上原価', '課税', 1010),
    (p_company_id, '5120', '外注費',            '費用', 'debit', '売上原価', '課税', 1020),
    (p_company_id, '5130', '材料費',            '費用', 'debit', '売上原価', '課税', 1030),
    -- 費用 - 販管費(人件費)
    (p_company_id, '5200', '給与手当',          '費用', 'debit', '販管費', '不課税', 1100),
    (p_company_id, '5210', '賞与',             '費用', 'debit', '販管費', '不課税', 1110),
    (p_company_id, '5220', '法定福利費',         '費用', 'debit', '販管費', '不課税', 1120),
    (p_company_id, '5230', '福利厚生費',         '費用', 'debit', '販管費', '課税', 1130),
    (p_company_id, '5240', '退職給付費用',       '費用', 'debit', '販管費', '不課税', 1140),
    (p_company_id, '5250', '役員報酬',          '費用', 'debit', '販管費', '不課税', 1150),
    -- 費用 - 販管費(経費)
    (p_company_id, '5300', '地代家賃',          '費用', 'debit', '販管費', '課税', 1200),
    (p_company_id, '5310', '水道光熱費',         '費用', 'debit', '販管費', '課税', 1210),
    (p_company_id, '5320', '通信費',            '費用', 'debit', '販管費', '課税', 1220),
    (p_company_id, '5330', '旅費交通費',         '費用', 'debit', '販管費', '課税', 1230),
    (p_company_id, '5340', '接待交際費',         '費用', 'debit', '販管費', '課税', 1240),
    (p_company_id, '5350', '広告宣伝費',         '費用', 'debit', '販管費', '課税', 1250),
    (p_company_id, '5360', '消耗品費',          '費用', 'debit', '販管費', '課税', 1260),
    (p_company_id, '5370', '保険料',            '費用', 'debit', '販管費', '非課税', 1270),
    (p_company_id, '5380', '修繕費',            '費用', 'debit', '販管費', '課税', 1280),
    (p_company_id, '5390', '減価償却費',         '費用', 'debit', '販管費', '不課税', 1290),
    (p_company_id, '5400', 'リース料',          '費用', 'debit', '販管費', '課税', 1300),
    (p_company_id, '5410', '租税公課',          '費用', 'debit', '販管費', '不課税', 1310),
    (p_company_id, '5420', '支払報酬',          '費用', 'debit', '販管費', '課税', 1320),
    (p_company_id, '5430', '研修費',            '費用', 'debit', '販管費', '課税', 1330),
    (p_company_id, '5440', '会議費',            '費用', 'debit', '販管費', '課税', 1340),
    (p_company_id, '5450', '荷造運賃',          '費用', 'debit', '販管費', '課税', 1350),
    (p_company_id, '5460', '新聞図書費',         '費用', 'debit', '販管費', '課税', 1360),
    (p_company_id, '5470', '支払手数料',         '費用', 'debit', '販管費', '課税', 1370),
    (p_company_id, '5900', '雑費',             '費用', 'debit', '販管費', '課税', 1380),
    -- 費用 - 営業外費用
    (p_company_id, '5600', '支払利息',          '費用', 'debit', '営業外費用', '非課税', 1400),
    -- 費用 - 特別損失
    (p_company_id, '5700', '固定資産売却損',      '費用', 'debit', '特別損失', '不課税', 1500),
    -- 費用 - 法人税等
    (p_company_id, '5800', '法人税等',          '費用', 'debit', '法人税等', '不課税', 1600);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================
-- 企業登録時の初期化トリガー
-- (企業作成 → デフォルト勘定科目 + 採番シーケンス自動作成)
-- =============================================================
CREATE OR REPLACE FUNCTION on_company_created()
RETURNS TRIGGER AS $$
BEGIN
    -- デフォルト勘定科目を挿入
    PERFORM insert_default_accounts(NEW.id);

    -- 採番シーケンスを初期化
    INSERT INTO numbering_sequences (company_id, entity_type, prefix, current_number) VALUES
        (NEW.id, 'project',    'P',  0),
        (NEW.id, 'staff',      'S',  0),
        (NEW.id, 'journal',    'J',  0),
        (NEW.id, 'expense',    'E',  0),
        (NEW.id, 'sales',      'SL', 0),
        (NEW.id, 'estimate',   'Q',  0),
        (NEW.id, 'invoice',    'IV', 0),
        (NEW.id, 'attendance', 'AT', 0);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_company_init
    AFTER INSERT ON companies
    FOR EACH ROW
    EXECUTE FUNCTION on_company_created();


-- =============================================================
-- 採番関数 (アトミック)
-- =============================================================
CREATE OR REPLACE FUNCTION next_number(
    p_company_id UUID,
    p_entity_type TEXT,
    p_parent_id TEXT DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    v_prefix TEXT;
    v_next INT;
    v_company_number TEXT;
    v_result TEXT;
BEGIN
    -- アトミックにインクリメント
    UPDATE numbering_sequences
    SET current_number = current_number + 1,
        updated_at = NOW()
    WHERE company_id = p_company_id
      AND entity_type = p_entity_type
      AND COALESCE(parent_id, '') = COALESCE(p_parent_id, '')
    RETURNING prefix, current_number INTO v_prefix, v_next;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Numbering sequence not found for entity_type=%, parent=%', p_entity_type, p_parent_id;
    END IF;

    -- 企業番号を取得
    SELECT company_number INTO v_company_number FROM companies WHERE id = p_company_id;

    -- フォーマット: P001-C001
    IF p_parent_id IS NOT NULL THEN
        v_result := v_prefix || LPAD(v_next::TEXT, 3, '0') || '-' || p_parent_id;
    ELSE
        v_result := v_prefix || LPAD(v_next::TEXT, 3, '0') || '-' || v_company_number;
    END IF;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================
-- パフォーマンス: 70,000社対応の追加インデックス
-- =============================================================

-- 複合インデックス (頻出クエリ用)
CREATE INDEX idx_journals_company_date_status ON journals (company_id, journal_date, status);
CREATE INDEX idx_attendance_employee_month ON attendance (company_id, employee_id, work_date);
CREATE INDEX idx_projects_company_status_payment ON projects (company_id, status, payment_month);
CREATE INDEX idx_invoices_company_status_due ON invoices (company_id, status, due_date);
CREATE INDEX idx_expenses_company_employee_date ON expenses (company_id, employee_id, expense_date);
CREATE INDEX idx_chat_messages_channel_created ON chat_messages (channel_id, created_at DESC);

-- BRIN インデックス (時系列データ用 - 大量データで効率的)
CREATE INDEX idx_journals_date_brin ON journals USING brin (journal_date);
CREATE INDEX idx_attendance_date_brin ON attendance USING brin (work_date);
CREATE INDEX idx_chat_messages_created_brin ON chat_messages USING brin (created_at);
CREATE INDEX idx_payments_date_brin ON payments USING brin (payment_date);


-- =============================================================
-- 完了
-- =============================================================
-- 使い方:
-- 1. Supabase SQL Editor でこのファイルを実行
-- 2. 企業登録: INSERT INTO companies (company_number, name) VALUES ('C001', '株式会社テスト');
--    → 自動で勘定科目80件 + 採番シーケンス8件が作成される
-- 3. ユーザー登録: INSERT INTO users (id, company_id, email, role) VALUES (auth.uid(), <company_id>, 'user@example.com', 'owner');
-- 4. 以降、RLSにより自社データのみアクセス可能
