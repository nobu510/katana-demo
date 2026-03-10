"use client";

import { useApp } from "@/lib/store";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ChatSidebar from "@/components/ChatSidebar";
import LoginScreen from "@/components/LoginScreen";

export default function LayoutContent({ children }: { children: React.ReactNode }) {
  const { state } = useApp();

  if (!state.authenticated) {
    return <LoginScreen />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto p-5 bg-[#f5f5f8] text-[#1a1a2e]">{children}</main>
        <footer className="px-6 py-2 bg-white border-t border-[#eee] flex justify-between text-[10px] text-[#9ca3af]">
          <span>&copy; 2026 AI精算アシスタント All rights reserved.</span>
          <div>
            <a href="#" className="text-[#6366f1] no-underline ml-4">よくある質問</a>
            <a href="#" className="text-[#6366f1] no-underline ml-4">利用規約</a>
            <a href="#" className="text-[#6366f1] no-underline ml-4">プライバシーポリシー</a>
          </div>
        </footer>
      </div>
      <ChatSidebar />
    </div>
  );
}
