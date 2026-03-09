export type NavItem = {
  id: string;
  label: string;
  icon: string;
  href?: string;
  children?: NavItem[];
};

export const navigation: NavItem[] = [
  { id: "home", label: "ホーム", icon: "🏠", href: "/" },
  { id: "ai", label: "AI精算アシスタント", icon: "🤖", href: "/expense" },
  { id: "ocr", label: "レシートスキャン", icon: "📷", href: "/ocr" },
  { id: "trend", label: "AIトレンド検索", icon: "📈", href: "/trend" },
  {
    id: "docs",
    label: "書類",
    icon: "📄",
    children: [
      { id: "files", label: "ファイル確認", icon: "📋" },
      { id: "quote", label: "見積書", icon: "📝", href: "/quote" },
      { id: "qreq", label: "見積依頼フォーム", icon: "📄" },
      { id: "order", label: "発注・納品書", icon: "📦" },
      { id: "invoice", label: "請求書", icon: "📄" },
      { id: "contract", label: "契約書", icon: "📑" },
      { id: "receipt", label: "領収書", icon: "🧾" },
    ],
  },
  {
    id: "expenseMgmt",
    label: "経費精算",
    icon: "💳",
    children: [],
  },
  {
    id: "sales",
    label: "営業管理",
    icon: "📊",
    children: [],
  },
  {
    id: "acct",
    label: "会計帳簿",
    icon: "📒",
    children: [],
  },
  {
    id: "settle",
    label: "決算",
    icon: "📋",
    children: [],
  },
  {
    id: "setting",
    label: "会計各種設定",
    icon: "⚙️",
    children: [],
  },
  {
    id: "inv",
    label: "在庫管理",
    icon: "📦",
    children: [],
  },
  { id: "chat2", label: "社内チャット", icon: "💬", href: "/chat" },
];
