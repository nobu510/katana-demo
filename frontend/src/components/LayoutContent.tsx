"use client";

import { useApp } from "@/lib/store";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ChatSidebar from "@/components/ChatSidebar";
import RegistrationChat from "@/components/RegistrationChat";

export default function LayoutContent({ children }: { children: React.ReactNode }) {
  const { state } = useApp();

  if (!state.registered) {
    return <RegistrationChat />;
  }

  return (
    <>
      <Sidebar />
      <div className="ml-56 min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 p-6">{children}</main>
        <footer className="border-t border-border px-6 py-3 text-[10px] text-gray-400 flex justify-between">
          <span>&copy; 2026 AI精算アシスタント All rights reserved.</span>
          <div className="flex gap-4">
            <span>よくある質問</span>
            <span>利用規約</span>
            <span>プライバシーポリシー</span>
          </div>
        </footer>
      </div>
      <ChatSidebar />
    </>
  );
}
