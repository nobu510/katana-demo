// ===== TYPES =====
export type StaffAssignment = {
  name: string;
  hrs: number;
  rate: number;
};

export type InvItem = {
  item: string;
  qty: number;
  cost: number;
};

export type Client = {
  id: string;
  nm: string;
  fl: string;
  pj: string;
  amt: number;
  cst: number;
  cm: number; // contract month index
  im: number; // invoice month index
  pm: number; // payment month index
  ct: string; // contact person
  staff: StaffAssignment[];
  progress: number;
  inv: InvItem[];
};

export type Staff = {
  id: string;
  name: string;
  full: string;
  role: string;
  rate: number;
  salary: number;
};

export type FixedAsset = {
  nm: string;
  val: number;
  dep: number;
};

// 日本の勘定科目に準拠した固定費内訳
export type FixedCostBreakdown = {
  personnel: number;       // 人件費（給与・賞与・法定福利費・福利厚生費）
  rent: number;            // 地代家賃
  utilities: number;       // 水道光熱費
  communication: number;   // 通信費
  lease: number;           // リース料
  insurance: number;       // 保険料
  depreciation: number;    // 減価償却費
  interest: number;        // 支払利息
  other: number;           // その他固定費
};

export const FIXED_COST_LABELS: Record<keyof FixedCostBreakdown, string> = {
  personnel: "人件費",
  rent: "地代家賃",
  utilities: "水道光熱費",
  communication: "通信費",
  lease: "リース料",
  insurance: "保険料",
  depreciation: "減価償却費",
  interest: "支払利息",
  other: "その他固定費",
};

export type ViewData = {
  rev: number;
  cost: number;
  fixed: number;
  tax: number;
  profit: number;
  cnt: number;
};

export type CalcResult = {
  future: ViewData;
  now: ViewData;
  cash: ViewData;
};

export type ExpenseEntry = {
  dt: string;
  cat: string;
  item: string;
  amt: number;
  by: string;
};

export type ReceiptSample = {
  store: string;
  date: string;
  items: { n: string; p: number }[];
  total: number;
  cat: string;
};

export type TrendCategory = {
  cat: string;
  icon: string;
  items: TrendItem[];
};

export type TrendItem = {
  t: string;
  s: string;
  tag: string;
  tc: string;
};

export type RagDoc = {
  t: string;
  tg: string;
  c: string;
  tx: string;
};

// ===== CONSTANTS =====
export const MO = ["4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月", "1月", "2月", "3月"];
// デフォルト固定費内訳（IT企業想定）
export const DEFAULT_FIXED_COSTS: FixedCostBreakdown = {
  personnel: 1_600_000,    // 人件費
  rent: 400_000,           // 地代家賃
  utilities: 50_000,       // 水道光熱費
  communication: 120_000,  // 通信費
  lease: 80_000,           // リース料
  insurance: 50_000,       // 保険料
  depreciation: 300_000,   // 減価償却費
  interest: 0,             // 支払利息
  other: 200_000,          // その他固定費
};

export function fixedCostTotal(fc: FixedCostBreakdown): number {
  return Object.values(fc).reduce((s, v) => s + v, 0);
}

export const FX = fixedCostTotal(DEFAULT_FIXED_COSTS); // 2,800,000
export const TX = 0.3;
export const TGT = 104000000;

// ===== DATA =====
export const initialClients: Client[] = [
  { id: "A", nm: "A社", fl: "株式会社アルファ", pj: "クラウド導入", amt: 4800000, cst: 1920000, cm: 0, im: 1, pm: 3, ct: "田中太郎", staff: [{ name: "田中", hrs: 80, rate: 3000 }, { name: "佐藤", hrs: 40, rate: 2800 }], progress: 100, inv: [] },
  { id: "B", nm: "B社", fl: "株式会社ベータ", pj: "AI研修", amt: 3200000, cst: 960000, cm: 1, im: 2, pm: 4, ct: "佐藤花子", staff: [{ name: "鈴木", hrs: 60, rate: 3200 }, { name: "高橋", hrs: 30, rate: 2500 }], progress: 85, inv: [] },
  { id: "C", nm: "C社", fl: "株式会社ガンマ", pj: "SaaS開発", amt: 12000000, cst: 4800000, cm: 2, im: 4, pm: 6, ct: "鈴木一郎", staff: [{ name: "田中", hrs: 200, rate: 3000 }, { name: "山本", hrs: 160, rate: 3500 }, { name: "中村", hrs: 120, rate: 2800 }], progress: 70, inv: [{ item: "サーバー", qty: 2, cost: 300000 }] },
  { id: "D", nm: "D社", fl: "株式会社デルタ", pj: "DX支援", amt: 6500000, cst: 2600000, cm: 3, im: 5, pm: 7, ct: "高橋次郎", staff: [{ name: "佐藤", hrs: 100, rate: 2800 }, { name: "高橋", hrs: 80, rate: 2500 }], progress: 55, inv: [] },
  { id: "E", nm: "E社", fl: "株式会社イプシロン", pj: "セキュリティ", amt: 8000000, cst: 3200000, cm: 4, im: 6, pm: 8, ct: "渡辺三郎", staff: [{ name: "鈴木", hrs: 120, rate: 3200 }, { name: "渡辺", hrs: 90, rate: 3000 }], progress: 40, inv: [{ item: "FW機器", qty: 3, cost: 150000 }] },
  { id: "F", nm: "F社", fl: "株式会社ゼータ", pj: "データ分析", amt: 5500000, cst: 2200000, cm: 5, im: 7, pm: 9, ct: "伊藤四郎", staff: [{ name: "山本", hrs: 80, rate: 3500 }, { name: "加藤", hrs: 60, rate: 2600 }], progress: 30, inv: [] },
  { id: "G", nm: "G社", fl: "株式会社エータ", pj: "AI Agent開発", amt: 25000000, cst: 10000000, cm: 6, im: 8, pm: 10, ct: "山本五郎", staff: [{ name: "田中", hrs: 300, rate: 3000 }, { name: "鈴木", hrs: 250, rate: 3200 }, { name: "山本", hrs: 200, rate: 3500 }, { name: "渡辺", hrs: 150, rate: 3000 }], progress: 20, inv: [{ item: "GPU", qty: 4, cost: 500000 }] },
  { id: "H", nm: "H社", fl: "株式会社シータ", pj: "研修20名", amt: 4000000, cst: 1200000, cm: 7, im: 8, pm: 10, ct: "中村六郎", staff: [{ name: "高橋", hrs: 60, rate: 2500 }, { name: "加藤", hrs: 40, rate: 2600 }], progress: 15, inv: [] },
  { id: "I", nm: "I社", fl: "株式会社イオタ", pj: "基幹連携", amt: 9000000, cst: 3600000, cm: 8, im: 9, pm: 11, ct: "小林七郎", staff: [{ name: "佐藤", hrs: 150, rate: 2800 }, { name: "中村", hrs: 100, rate: 2800 }], progress: 10, inv: [{ item: "ライセンス", qty: 5, cost: 200000 }] },
  { id: "J", nm: "J社", fl: "株式会社カッパ", pj: "IoT開発", amt: 7200000, cst: 2880000, cm: 9, im: 10, pm: 11, ct: "加藤八郎", staff: [{ name: "渡辺", hrs: 120, rate: 3000 }, { name: "加藤", hrs: 100, rate: 2600 }], progress: 5, inv: [{ item: "センサー", qty: 20, cost: 50000 }] },
  { id: "K", nm: "K社", fl: "株式会社ラムダ", pj: "AI監査", amt: 3800000, cst: 1520000, cm: 10, im: 11, pm: 11, ct: "吉田九郎", staff: [{ name: "鈴木", hrs: 60, rate: 3200 }], progress: 0, inv: [] },
  { id: "L", nm: "L社", fl: "株式会社ミュー", pj: "全社DX", amt: 15000000, cst: 6000000, cm: 11, im: 11, pm: 11, ct: "佐々木十郎", staff: [{ name: "田中", hrs: 200, rate: 3000 }, { name: "山本", hrs: 180, rate: 3500 }], progress: 0, inv: [] },
];

export const initialStaff: Staff[] = [
  { id: "S001", name: "田中", full: "田中太郎", role: "シニアエンジニア", rate: 3000, salary: 450000 },
  { id: "S002", name: "佐藤", full: "佐藤花子", role: "プロジェクトマネージャー", rate: 2800, salary: 420000 },
  { id: "S003", name: "鈴木", full: "鈴木一郎", role: "AIエンジニア", rate: 3200, salary: 480000 },
  { id: "S004", name: "高橋", full: "高橋次郎", role: "ジュニアエンジニア", rate: 2500, salary: 350000 },
  { id: "S005", name: "山本", full: "山本五郎", role: "リードエンジニア", rate: 3500, salary: 520000 },
  { id: "S006", name: "渡辺", full: "渡辺三郎", role: "インフラエンジニア", rate: 3000, salary: 450000 },
  { id: "S007", name: "中村", full: "中村六郎", role: "デザイナー", rate: 2800, salary: 400000 },
  { id: "S008", name: "加藤", full: "加藤八郎", role: "テスター", rate: 2600, salary: 380000 },
];

export const FASSETS: FixedAsset[] = [
  { nm: "サーバー設備", val: 3200000, dep: 800000 },
  { nm: "開発用PC(8台)", val: 2400000, dep: 600000 },
  { nm: "ソフトウェアライセンス", val: 1800000, dep: 900000 },
  { nm: "オフィス内装", val: 1500000, dep: 300000 },
];

export const RCP: ReceiptSample[] = [
  { store: "ヨドバシカメラ 梅田", date: "2026/04/15", items: [{ n: "USBケーブル", p: 1280 }, { n: "マウスパッド", p: 980 }], total: 2260, cat: "消耗品費" },
  { store: "タクシー（大阪→梅田）", date: "2026/04/15", items: [{ n: "タクシー運賃", p: 2340 }], total: 2340, cat: "交通費" },
  { store: "スターバックス 本町店", date: "2026/04/16", items: [{ n: "コーヒー×2", p: 780 }, { n: "サンドイッチ", p: 520 }], total: 1300, cat: "会議費" },
];

export const RAG: RagDoc[] = [
  { t: "売上管理マニュアル v2.3", tg: "営業", c: "#7c3aed", tx: "売上の計上基準は納品完了時点。前受金の扱いは経理部確認の上、月次処理。" },
  { t: "経費精算規定", tg: "経理", c: "#3b82f6", tx: "交通費は実費精算。タクシーは事前承認必要。5,000円以上は領収書必須。" },
  { t: "月次決算チェックリスト", tg: "会計", c: "#f97316", tx: "1.仕訳整合性 2.前月比異常値 3.消費税区分 4.修正仕訳" },
  { t: "AI Agent要件定義", tg: "開発", c: "#7c3aed", tx: "G社向け: 自律タスク実行、マルチモーダル、社内データ連携。" },
  { t: "2026年度予算", tg: "予算", c: "#ef4444", tx: "売上目標:1億400万円。固定費月280万円。利益率35%以上。" },
  { t: "見積ガイドライン", tg: "営業", c: "#7c3aed", tx: "有効期限30日。値引は上長承認で最大15%。" },
];

export const TRENDS: TrendCategory[] = [
  {
    cat: "AI・DX", icon: "🤖", items: [
      { t: "生成AI市場が急拡大", s: "2026年国内市場規模1.2兆円突破見込み。企業導入率45%に到達。", tag: "注目", tc: "#7c3aed" },
      { t: "AI Agent活用が本格化", s: "自律型AIが業務プロセスを自動化。人件費30%削減の事例が続出。", tag: "急上昇", tc: "#ef4444" },
      { t: "RAG技術で社内DX加速", s: "社内文書×AIで知識検索が革命的に。導入企業の生産性25%向上。", tag: "トレンド", tc: "#3b82f6" },
      { t: "ノーコードAI開発ツール", s: "プログラミング不要でAIアプリ構築。中小企業のAI導入障壁が低下。", tag: "新着", tc: "#059669" },
    ],
  },
  {
    cat: "会計・経営", icon: "📊", items: [
      { t: "インボイス制度対応の自動化", s: "AI-OCRで請求書処理を95%自動化。経理工数が月40時間削減。", tag: "必須", tc: "#d97706" },
      { t: "リアルタイム経営ダッシュボード", s: "月次決算から日次経営へ。KATANAのような3視点分析が標準に。", tag: "注目", tc: "#7c3aed" },
      { t: "キャッシュフロー予測AI", s: "入金予測精度90%超。資金繰り不安を解消する中小企業が増加。", tag: "トレンド", tc: "#3b82f6" },
    ],
  },
  {
    cat: "補助金・制度", icon: "💰", items: [
      { t: "IT導入補助金2026", s: "AI・クラウド導入に最大450万円。申請締切は6月30日。", tag: "締切注意", tc: "#ef4444" },
      { t: "事業再構築補助金", s: "DX投資に最大1億円。従業員50名以下の中小企業が対象拡大。", tag: "新着", tc: "#059669" },
      { t: "電子帳簿保存法の完全義務化", s: "2026年1月より全事業者対象。KATANA対応済みで安心。", tag: "必須", tc: "#d97706" },
    ],
  },
];

export const expenseDemo: ExpenseEntry[] = [
  { dt: "2026/04/05", cat: "交通費", item: "タクシー（A社訪問）", amt: 3200, by: "田中太郎" },
  { dt: "2026/04/08", cat: "会議費", item: "クライアント昼食会", amt: 5400, by: "佐藤花子" },
  { dt: "2026/04/10", cat: "消耗品費", item: "プリンター用紙・トナー", amt: 8900, by: "高橋次郎" },
  { dt: "2026/04/12", cat: "通信費", item: "AWS利用料（4月分）", amt: 48000, by: "鈴木一郎" },
  { dt: "2026/04/15", cat: "交通費", item: "新幹線（D社出張）", amt: 27800, by: "佐藤花子" },
  { dt: "2026/04/18", cat: "接待交際費", item: "B社との懇親会", amt: 32000, by: "田中太郎" },
  { dt: "2026/04/20", cat: "研修費", item: "AI研修セミナー参加", amt: 15000, by: "高橋次郎" },
];

// ===== FUNCTIONS =====
export function fF(n: number): string {
  return "¥" + Math.abs(n).toLocaleString();
}

export function fmt(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e8) return (n / 1e8).toFixed(1) + "億";
  if (a >= 1e4) return Math.round(n / 1e4).toLocaleString() + "万";
  return n.toLocaleString();
}

export function gSt(c: Client, m: number): "pd" | "iv" | "ct" | "pn" {
  if (m >= c.pm) return "pd";
  if (m >= c.im) return "iv";
  if (m >= c.cm) return "ct";
  return "pn";
}

export function gSL(s: "pd" | "iv" | "ct" | "pn"): string {
  return { pd: "入金済", iv: "請求済", ct: "契約済", pn: "未契約" }[s];
}

export function gSC(s: "pd" | "iv" | "ct" | "pn"): string {
  return { pd: "b-pd", iv: "b-iv", ct: "b-ct", pn: "b-pn" }[s];
}

export function calc(clients: Client[], m: number, ocrAmount: number = 0, fixedCosts?: FixedCostBreakdown): CalcResult {
  const fu = { r: 0, c: 0, n: 0 };
  const nw = { r: 0, c: 0, n: 0 };
  const cf = { r: 0, c: 0, n: 0 };

  clients.forEach((c) => {
    if (m >= c.cm) { fu.r += c.amt; fu.c += c.cst; fu.n++; }
    if (m >= c.im) { nw.r += c.amt; nw.c += c.cst; nw.n++; }
    if (m >= c.pm) { cf.r += c.amt; cf.c += c.cst; cf.n++; }
  });

  function fin(d: { r: number; c: number; n: number }, mo: number): ViewData {
    const r = d.r + ocrAmount;
    const co = d.c;
    const fx = fixedCosts ? fixedCostTotal(fixedCosts) : FX;
    const f = fx * mo;
    const g = r - co - f;
    const t = Math.max(0, g * TX);
    return { rev: r, cost: co, fixed: f, tax: t, profit: g - t, cnt: d.n };
  }

  return {
    future: fin(fu, m + 1),
    now: fin(nw, m + 1),
    cash: fin(cf, Math.max(1, m)),
  };
}
