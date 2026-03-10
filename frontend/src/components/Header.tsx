"use client";

import { usePathname } from "next/navigation";

const PAGE_TITLES: Record<string, [string, string]> = {
  "/": ["ホーム", "予実管理ダッシュボード"],
  "/ocr": ["レシートスキャン", "AI OCR 自動読取"],
  "/quote": ["見積書", "作成・管理"],
  "/trend": ["AIトレンド検索", "業界動向・競合分析"],
  "/expense": ["AI精算アシスタント", "経費・仕訳・税務をAIがサポート"],
  "/chat": ["社内チャット", "メッセージ"],
};

export default function Header() {
  const pathname = usePathname();
  const [title, subtitle] = PAGE_TITLES[pathname] || ["KATANA", ""];

  return (
    <header className="px-6 py-3 bg-white border-b border-[#e5e7eb] flex justify-between items-center text-[#1a1a2e] shrink-0">
      <div>
        <div className="text-base font-bold">{title}</div>
        <div className="text-[11px] text-[#9ca3af] mt-0.5">{subtitle}</div>
      </div>
      <div className="flex items-center gap-4 text-xs text-[#9ca3af]">
        <span>📅 2026年度</span>
        <span className="cursor-pointer">🔔</span>
        <span className="cursor-pointer">⚙️</span>
      </div>
    </header>
  );
}
