"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useApp } from "@/lib/store";
import { apiPost } from "@/lib/api";

type RegMessage = {
  ai: boolean;
  text: string;
};

type ExtractedData = {
  industry: string | null;
  name: string | null;
  staff_count: number | null;
  fixed_cost_monthly: number | null;
};

type RegisterResponse = {
  reply: string;
  extracted_data: ExtractedData | null;
  confirmed: boolean;
};

const INDUSTRY_TEMPLATE_MAP: Record<string, string> = {
  it: "it_company",
  retail: "retail",
};

const INDUSTRY_LABELS: Record<string, string> = {
  it: "IT企業",
  retail: "小売業",
  restaurant: "飲食業",
  construction: "建設業",
  manufacturing: "製造業",
  service: "サービス業",
};

const INDUSTRY_ICONS: Record<string, string> = {
  it: "💻",
  retail: "🏪",
  restaurant: "🍽️",
  construction: "🏗️",
  manufacturing: "🏭",
  service: "🤝",
};

function fF(n: number): string {
  if (n >= 10000) return `¥${(n / 10000).toFixed(0)}万`;
  return `¥${n.toLocaleString()}`;
}

export default function RegistrationChat() {
  const { dispatch } = useApp();
  const [messages, setMessages] = useState<RegMessage[]>([
    {
      ai: true,
      text: "こんにちは！KATANA AIです。御社の経営を一刀両断します⚔️\n\nまず、どんなお仕事をされていますか？",
    },
  ]);
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const msgsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [messages, typing]);

  const doRegister = useCallback(
    async (data: ExtractedData) => {
      const templateKey = INDUSTRY_TEMPLATE_MAP[data.industry!] || data.industry!;
      try {
        await apiPost("/api/companies", {
          name: data.name,
          industry: data.industry,
          fixed_cost_monthly: data.fixed_cost_monthly,
          staff_count: data.staff_count,
          tax_rate: 0.3,
          categories: [],
        });

        // Switch to registered state
        dispatch({
          type: "SET_REGISTERED",
          registered: true,
          companyName: data.name || "",
          template: templateKey,
        });
        dispatch({ type: "SET_CHAT_OPEN", open: false });
        dispatch({
          type: "ADD_MESSAGE",
          message: {
            ai: true,
            text: `🎉 ${data.name}を登録しました！\n\n${INDUSTRY_ICONS[data.industry!] || "🏢"} ${INDUSTRY_LABELS[data.industry!] || data.industry}のテンプレートを適用しました。\nダッシュボードにデモデータが表示されています。\n\n💡 「今月の売上は？」「利益率は？」など、何でも聞いてください！`,
          },
        });
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          { ai: true, text: "⚠️ 登録に失敗しました: " + (e instanceof Error ? e.message : "エラー") },
        ]);
      }
    },
    [dispatch],
  );

  const sendMessage = useCallback(async () => {
    const q = input.trim();
    if (!q || typing) return;
    setInput("");

    setMessages((prev) => [...prev, { ai: false, text: q }]);
    setTyping(true);

    const newHistory = [...history, { role: "user", content: q }];

    try {
      const res = await apiPost<RegisterResponse & { error?: string }>("/api/chat/register", {
        message: q,
        history: history,
      });

      if (res.error) {
        setMessages((prev) => [...prev, { ai: true, text: "⚠️ " + res.error }]);
        return;
      }

      const aiMsg = res.reply;
      setMessages((prev) => [...prev, { ai: true, text: aiMsg }]);
      setHistory([...newHistory, { role: "assistant", content: aiMsg }]);

      // Update extracted data
      if (res.extracted_data) {
        setExtractedData(res.extracted_data);
      }

      // Auto-register if confirmed
      if (res.confirmed && res.extracted_data) {
        const d = res.extracted_data;
        if (d.industry && d.name && d.staff_count && d.fixed_cost_monthly) {
          setTimeout(() => doRegister(d), 1500);
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { ai: true, text: "⚠️ 通信エラー: " + (e instanceof Error ? e.message : "接続できません") + "\nもう一度お試しください。" },
      ]);
    } finally {
      setTyping(false);
    }
  }, [input, typing, history, doRegister]);

  // Calculate progress
  const filledCount = extractedData
    ? [extractedData.industry, extractedData.name, extractedData.staff_count, extractedData.fixed_cost_monthly].filter(
        (v) => v !== null && v !== undefined,
      ).length
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 flex flex-col" style={{ height: "80vh" }}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-lg">
              ⚔️
            </div>
            <div>
              <h1 className="text-white font-bold text-lg">KATANA AI</h1>
              <div className="flex items-center gap-1.5 text-xs text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                企業登録モード
              </div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${(filledCount / 4) * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-white/50">{filledCount}/4</span>
          </div>

          {/* Extracted data chips */}
          {extractedData && filledCount > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {extractedData.industry && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-purple-500/30 text-purple-200 border border-purple-400/30">
                  {INDUSTRY_ICONS[extractedData.industry]} {INDUSTRY_LABELS[extractedData.industry] || extractedData.industry}
                </span>
              )}
              {extractedData.name && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-blue-500/30 text-blue-200 border border-blue-400/30">
                  🏢 {extractedData.name}
                </span>
              )}
              {extractedData.staff_count && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-green-500/30 text-green-200 border border-green-400/30">
                  👥 {extractedData.staff_count}名
                </span>
              )}
              {extractedData.fixed_cost_monthly && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-500/30 text-amber-200 border border-amber-400/30">
                  💰 {fF(extractedData.fixed_cost_monthly)}/月
                </span>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div ref={msgsRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.ai ? "justify-start" : "justify-end"}`}>
              <div className={`max-w-[80%] ${m.ai ? "flex gap-2" : ""}`}>
                {m.ai && (
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-sm shrink-0 mt-0.5">
                    ⚔️
                  </div>
                )}
                <div
                  className={`px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed ${
                    m.ai
                      ? "bg-white/10 text-white/90 rounded-tl-none"
                      : "bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-tr-none"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            </div>
          ))}
          {typing && (
            <div className="flex justify-start">
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-sm shrink-0">
                  ⚔️
                </div>
                <div className="px-4 py-3 rounded-2xl rounded-tl-none bg-white/10 text-white/60 text-sm">
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/10">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              rows={1}
              placeholder='例：「うちは食品スーパーで社員15人、固定費は月180万です」'
              className="flex-1 bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 resize-none focus:outline-none focus:border-purple-400/50 focus:ring-1 focus:ring-purple-400/30"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || typing}
              className={`w-11 h-11 rounded-xl flex items-center justify-center text-white text-lg transition-all ${
                input.trim() && !typing
                  ? "bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 shadow-lg shadow-purple-500/30"
                  : "bg-white/10 text-white/30 cursor-not-allowed"
              }`}
            >
              ↑
            </button>
          </div>
          <div className="mt-2 text-center text-[10px] text-white/30">
            会話で企業情報を登録 → 登録完了後ダッシュボードが表示されます
          </div>
        </div>
      </div>
    </div>
  );
}
