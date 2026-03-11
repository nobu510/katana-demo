"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useApp } from "@/lib/store";
import { apiPost } from "@/lib/api";
import StreamingText from "@/components/StreamingText";

type CompanyData = {
  industry: string | null;
  name: string | null;
  staff_count: number | null;
  fixed_cost_monthly: number | null;
};

type RegisterResponse = {
  reply: string;
  extracted_data: CompanyData | null;
  confirmed: boolean;
  error?: string;
};

const EMPTY_DATA: CompanyData = {
  industry: null,
  name: null,
  staff_count: null,
  fixed_cost_monthly: null,
};

export default function OnboardingChat() {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState("");
  const [collected, setCollected] = useState<CompanyData>({ ...EMPTY_DATA });
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const msgsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [state.messages, state.typing]);

  // 抽出データをマージ（nullでない値だけ上書き）
  const mergeCollected = useCallback((newData: CompanyData | null): CompanyData => {
    if (!newData) return collected;
    return {
      industry: newData.industry ?? collected.industry,
      name: newData.name ?? collected.name,
      staff_count: newData.staff_count ?? collected.staff_count,
      fixed_cost_monthly: newData.fixed_cost_monthly ?? collected.fixed_cost_monthly,
    };
  }, [collected]);

  const sendMessage = useCallback(async () => {
    const q = input.trim();
    if (!q || state.typing) return;
    setInput("");

    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: q } });
    dispatch({ type: "SET_TYPING", typing: true });

    const newHistory = [...history, { role: "user", content: q }];

    try {
      const res = await apiPost<RegisterResponse>("/api/chat/register", {
        message: q,
        history: newHistory,
        collected,
      });

      if (res.error) {
        dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: `⚠️ ${res.error}` } });
        dispatch({ type: "SET_TYPING", typing: false });
        return;
      }

      const reply = res.reply || "すみません、もう一度お願いできますか？";
      const merged = mergeCollected(res.extracted_data);
      setCollected(merged);
      setHistory([...newHistory, { role: "assistant", content: reply }]);

      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: reply } });
      dispatch({ type: "SET_TYPING", typing: false });

      // 登録確認された場合 → ダッシュボードへ遷移
      if (res.confirmed) {
        setTimeout(() => {
          dispatch({ type: "REGISTER_COMPANY" });
        }, 1500);
      }
    } catch (e) {
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({
        type: "ADD_MESSAGE",
        message: { ai: true, text: "⚠️ 通信エラーが発生しました。もう一度お試しください。" },
      });
    }
  }, [input, state.typing, history, collected, mergeCollected, dispatch]);

  // 取得済み項目のインジケーター
  const items = [
    { key: "industry", label: "業種", done: !!collected.industry },
    { key: "name", label: "会社名", done: !!collected.name },
    { key: "staff_count", label: "社員数", done: collected.staff_count != null },
    { key: "fixed_cost_monthly", label: "固定費", done: collected.fixed_cost_monthly != null },
  ];
  const doneCount = items.filter((i) => i.done).length;

  return (
    <div className="flex h-screen bg-[#0a0a14]">
      {/* Background gradient */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at 30% 20%, rgba(99,102,241,0.08) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(124,58,237,0.06) 0%, transparent 50%)",
        }}
      />

      {/* Center chat area */}
      <div className="relative z-10 flex flex-col w-full max-w-[700px] mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#6366f1] to-[#7c3aed] flex items-center justify-center shadow-[0_2px_12px_rgba(99,102,241,0.4)]">
            <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
              <path d="M8 4c0 0 2 1 4 1s4-1 4-1v3c0 1-1.5 2-4 2s-4-1-4-2V4z" fill="#fff" />
              <rect x="11" y="9" width="2" height="11" rx="1" fill="#fff" />
              <path d="M8 20h8" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-bold text-white">KATANA AI</div>
            <div className="text-[10px] text-[#10b981] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] inline-block" />
              企業登録
            </div>
          </div>

          {/* Progress indicator */}
          <div className="ml-auto flex items-center gap-1.5">
            {items.map((item) => (
              <div
                key={item.key}
                title={item.label}
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all ${
                  item.done
                    ? "bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30"
                    : "bg-white/5 text-[#555] border border-white/10"
                }`}
              >
                {item.done ? "✓" : item.label[0]}
              </div>
            ))}
            <span className="text-[10px] text-[#9ca3af] ml-1">{doneCount}/4</span>
          </div>
        </div>

        {/* Messages */}
        <div ref={msgsRef} className="flex-1 overflow-y-auto px-6 py-4">
          {state.messages.map((m, i) => {
            const isLastAi = m.ai && i === state.messages.length - 1;
            return (
              <div key={i} className={`mb-4 flex ${m.ai ? "justify-start" : "justify-end"}`}>
                {m.ai && (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#7c3aed] flex items-center justify-center mr-3 mt-1 shrink-0">
                    <span className="text-white text-xs">AI</span>
                  </div>
                )}
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                    m.ai
                      ? "bg-[#1a1a2e] border border-white/10 text-[#e5e7eb] rounded-bl-[4px]"
                      : "bg-[#6366f1] text-white rounded-br-[4px]"
                  }`}
                >
                  {m.ai && isLastAi ? (
                    <StreamingText text={m.text} isStreaming={state.typing} />
                  ) : (
                    m.text
                  )}
                </div>
              </div>
            );
          })}
          {state.typing && (
            <div className="mb-4 flex justify-start">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#7c3aed] flex items-center justify-center mr-3 mt-1 shrink-0">
                <span className="text-white text-xs">AI</span>
              </div>
              <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-6 py-4">
          <div className="flex gap-3 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              rows={2}
              placeholder="メッセージを入力..."
              className="flex-1 px-4 py-3 bg-[#1a1a2e] border border-white/10 rounded-xl text-sm text-white placeholder-[#555] outline-none resize-none leading-normal focus:border-[#6366f1] transition-colors"
            />
            <button
              onClick={sendMessage}
              className={`w-10 h-10 rounded-xl flex items-center justify-center text-white text-lg transition-all ${
                input.trim()
                  ? "bg-gradient-to-r from-[#6366f1] to-[#7c3aed] shadow-[0_2px_12px_rgba(99,102,241,0.4)]"
                  : "bg-[#1a1a2e] border border-white/10"
              }`}
            >
              ↑
            </button>
          </div>
          <p className="text-center text-[10px] text-[#555] mt-3">
            &copy; 2026 J.NOVA Inc. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}
