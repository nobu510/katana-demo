"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useApp } from "@/lib/store";

type MenuItem = {
  icon: string;
  label: string;
  href?: string;
  children?: MenuItem[];
};

const MENU: MenuItem[] = [
  { icon: "🏠", label: "ホーム", href: "/" },
  { icon: "🤖", label: "AI精算アシスタント", href: "/expense" },
  { icon: "📷", label: "レシートスキャン", href: "/ocr" },
  { icon: "📈", label: "AIトレンド検索", href: "/trend" },
  {
    icon: "📄", label: "書類", children: [
      { icon: "📋", label: "ファイル確認" },
      { icon: "📝", label: "見積書", href: "/quote" },
      { icon: "📄", label: "見積依頼フォーム" },
      { icon: "📦", label: "発注・納品書" },
      { icon: "📄", label: "請求書" },
      { icon: "📑", label: "契約書" },
      { icon: "🧾", label: "領収書" },
    ],
  },
  { icon: "💳", label: "経費精算" },
  { icon: "📊", label: "営業管理" },
  { icon: "📒", label: "会計帳簿" },
  { icon: "📋", label: "決算" },
  { icon: "📋", label: "電子申請", href: "/e-filing" },
  { icon: "⚙️", label: "会計各種設定" },
  { icon: "📦", label: "在庫管理" },
  { icon: "💬", label: "社内チャット", href: "/chat" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { state } = useApp();
  const [openSubs, setOpenSubs] = useState<Record<string, boolean>>({ "書類": true });

  const toggleSub = (label: string) => {
    setOpenSubs((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const renderItem = (item: MenuItem, depth = 0) => {
    const isActive = item.href === pathname;
    const hasChildren = item.children && item.children.length > 0;
    const isOpen = openSubs[item.label];

    if (hasChildren) {
      return (
        <div key={item.label}>
          <button
            onClick={() => toggleSub(item.label)}
            className="w-full flex items-center gap-2.5 py-2.5 px-4 text-[13px] text-[#8888a0] hover:bg-white/5 hover:text-[#c0c0d0] transition-all border-l-[3px] border-transparent"
          >
            <span className="w-[18px] text-center text-sm">{item.icon}</span>
            <span>{item.label}</span>
            <span className="ml-auto text-[10px] text-[#555]">{isOpen ? "∨" : "›"}</span>
          </button>
          <div className={`overflow-hidden transition-all duration-300 ${isOpen ? "max-h-[400px]" : "max-h-0"}`}>
            {item.children!.map((child) => renderItem(child, depth + 1))}
          </div>
        </div>
      );
    }

    const content = (
      <>
        <span className="w-[18px] text-center text-sm">{item.icon}</span>
        <span>{item.label}</span>
      </>
    );

    const className = `flex items-center gap-2.5 py-2.5 text-[13px] transition-all border-l-[3px] ${
      depth > 0 ? "pl-11 text-xs" : "px-4"
    } ${
      isActive
        ? "bg-[rgba(99,102,241,0.15)] text-white border-l-[#6366f1]"
        : "text-[#8888a0] hover:bg-white/5 hover:text-[#c0c0d0] border-transparent"
    }`;

    if (item.href) {
      return (
        <Link key={item.label + item.href} href={item.href} className={className}>
          {content}
        </Link>
      );
    }

    return (
      <div key={item.label + (depth > 0 ? "sub" : "")} className={`${className} cursor-pointer`}>
        {content}
      </div>
    );
  };

  return (
    <nav className="w-[200px] bg-[#1e1e2e] shrink-0 h-screen flex flex-col relative overflow-hidden">
      {/* Logo */}
      <div className="px-3.5 py-3.5 flex items-center gap-2.5 border-b border-[#2a2a44] relative z-[1]">
        <div className="w-[34px] h-[34px] rounded-full bg-white flex items-center justify-center">
          <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
            <path d="M8 4c0 0 2 1 4 1s4-1 4-1v3c0 1-1.5 2-4 2s-4-1-4-2V4z" fill="#4fb5c9" />
            <rect x="11" y="9" width="2" height="11" rx="1" fill="#4fb5c9" />
            <path d="M8 20h8" stroke="#4fb5c9" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div className="text-white text-sm font-bold tracking-wider">KATANA AI</div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-2 relative z-[1]">
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2.5 py-2 px-4 text-[#6366f1] text-base cursor-pointer w-full text-left"
        >
          ‹
        </button>
        {MENU.map((item) => renderItem(item))}
      </div>

      {/* Footer */}
      <div className="border-t border-[#2a2a44] px-4 py-3 relative z-[1]">
        <div className="text-[#8888a0] text-xs cursor-pointer">↗ 人事労務管理へ</div>
      </div>

      {/* User */}
      <div className="px-4 py-3 border-t border-[#2a2a44] flex items-center gap-2.5 relative z-[1]">
        <div className="w-8 h-8 rounded-full bg-[#6366f1] flex items-center justify-center text-white text-[13px] font-bold">
          {(state.companyName || "G").charAt(0)}
        </div>
        <div>
          <div className="text-white text-xs font-semibold">{state.companyName || "GOTO"}</div>
          <div className="text-[#6b7280] text-[10px]">オーナー</div>
        </div>
      </div>
    </nav>
  );
}
