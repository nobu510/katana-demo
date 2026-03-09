"use client";

import { useApp } from "@/lib/store";

const COMPANY_NAMES: Record<string, string> = {
  it_company: "株式会社J.NOVA",
  retail: "株式会社マルシェ",
};

export default function Header() {
  const { state, dispatch } = useApp();

  const displayName = state.companyName || COMPANY_NAMES[state.template] || "KATANA AI";

  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-foreground">
          {displayName}
        </h1>
        <span className="text-xs text-gray-400">📅 2026年度</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-[11px] text-green-600 bg-green-50 px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          Claude AI 接続中
        </div>
        <button
          onClick={() => dispatch({ type: "TOGGLE_CHAT" })}
          className={`w-8 h-8 rounded-lg text-white flex items-center justify-center text-sm transition-colors ${
            state.chatOpen ? "bg-primary-hover" : "bg-primary hover:bg-primary-hover"
          }`}
        >
          💬
        </button>
      </div>
    </header>
  );
}
