"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useApp } from "@/lib/store";
import { calc, fF, gSt, gSL, MO, TGT, RAG, expenseDemo } from "@/lib/data";
import { apiStreamChat } from "@/lib/api";
import StreamingText from "@/components/StreamingText";

type RagResult = {
  id: string;
  category: string;
  icon: string;
  color: string;
  title: string;
  detail: string;
  searchText: string;
};

export default function ChatPage() {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState("");
  const [tab, setTab] = useState<"chat" | "rag">("chat");
  const [ragResults, setRagResults] = useState<RagResult[]>([]);
  const [ragQuery, setRagQuery] = useState("");
  const msgsRef = useRef<HTMLDivElement>(null);

  // Build RAG search index from all data sources
  const ragIndex = useMemo((): RagResult[] => {
    const results: RagResult[] = [];
    // Clients
    state.clients.forEach((c) => {
      const staffNames = c.staff.map((s) => s.name + s.hrs + "h").join(", ");
      const profitRate = Math.round(((c.amt - c.cst) / c.amt) * 100);
      results.push({
        id: `client-${c.id}`,
        category: "取引先",
        icon: "🏢",
        color: "#6366f1",
        title: `${c.nm}（${c.fl}）- ${c.pj}`,
        detail: `売上 ¥${c.amt.toLocaleString()} / 原価 ¥${c.cst.toLocaleString()} / 利益率 ${profitRate}% / 担当: ${staffNames} / 契約${MO[c.cm]} 請求${MO[c.im]} 入金${MO[c.pm]}`,
        searchText: `${c.nm} ${c.fl} ${c.pj} ${staffNames} ${c.ct}`.toLowerCase(),
      });
    });
    // Staff
    state.staff.forEach((s) => {
      let totalHrs = 0;
      const projects: string[] = [];
      state.clients.forEach((c) => {
        c.staff.forEach((sf) => {
          if (sf.name === s.name) { totalHrs += sf.hrs; projects.push(c.nm); }
        });
      });
      results.push({
        id: `staff-${s.id}`,
        category: "社員",
        icon: "👤",
        color: "#7c3aed",
        title: `${s.id} ${s.full} - ${s.role}`,
        detail: `時給 ¥${s.rate.toLocaleString()} / 月給 ¥${s.salary.toLocaleString()} / 稼働 ${totalHrs}h / 担当: ${projects.join(", ") || "なし"}`,
        searchText: `${s.id} ${s.name} ${s.full} ${s.role} ${projects.join(" ")}`.toLowerCase(),
      });
    });
    // Expenses
    expenseDemo.forEach((e, i) => {
      results.push({
        id: `expense-${i}`,
        category: "経費",
        icon: "💰",
        color: "#d97706",
        title: `${e.cat} - ${e.item}`,
        detail: `¥${e.amt.toLocaleString()} / ${e.dt} / 申請者: ${e.by}`,
        searchText: `${e.cat} ${e.item} ${e.by}`.toLowerCase(),
      });
    });
    // Documents (existing RAG)
    RAG.forEach((r) => {
      results.push({
        id: `doc-${r.t}`,
        category: "文書",
        icon: "📄",
        color: r.c,
        title: r.t,
        detail: r.tx,
        searchText: `${r.t} ${r.tg} ${r.tx}`.toLowerCase(),
      });
    });
    // 3 Views
    results.push(
      { id: "view-future", category: "経営視点", icon: "🔮", color: "#10b981", title: "未来の数字", detail: "契約済売上(請求前含む) - 原価 - 固定費(月280万) - 税金(30%)", searchText: "未来 契約 受注 見込 予測" },
      { id: "view-now", category: "経営視点", icon: "📊", color: "#3b82f6", title: "今の数字", detail: "請求済売上 - 支払予定 - 日割固定費 - 税金(30%)", searchText: "今 請求 売掛 現在" },
      { id: "view-cash", category: "経営視点", icon: "💵", color: "#ef4444", title: "キャッシュフロー", detail: "入金済額 - 支払済額 - 日割固定費 - 税金。差額=必要運転資金", searchText: "キャッシュ cf 入金 資金繰り 現金" },
    );
    return results;
  }, [state.clients, state.staff]);

  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [state.messages, state.typing]);

  const askAI = useCallback(async (q: string) => {
    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: q } });
    dispatch({ type: "ADD_HISTORY", entry: { role: "user", content: q } });
    dispatch({ type: "SET_TYPING", typing: true });

    const { clients, staff, currentMonth: cm } = state;
    const d = calc(clients, cm, state.ocrAmount);
    const gap = d.future.profit - d.cash.profit;
    const ach = Math.round((d.future.rev / TGT) * 100);
    const projInfo = clients.filter(c => cm >= c.cm).map(c => {
      const lab = c.staff.reduce((s, sf) => s + sf.hrs * sf.rate, 0);
      const gr = c.amt - lab - c.cst;
      return `${c.nm}(${c.pj}/売上${fF(c.amt)}/粗利${fF(gr)}/${gSL(gSt(c, cm))})`;
    }).join(", ");
    const staffInfo = staff.map(s => {
      let hrs = 0; const pjs: string[] = [];
      clients.forEach(c => { if (cm < c.cm) return; c.staff.forEach(sf => { if (sf.name === s.name) { hrs += sf.hrs; pjs.push(c.nm); } }); });
      return hrs > 0 ? `${s.full}(${s.id}): ${hrs}h` : null;
    }).filter(Boolean).join("; ");
    const ctx = `\n[現在月:${MO[cm]} 未来利益:${fF(d.future.profit)} 今利益:${fF(d.now.profit)} CF利益:${fF(d.cash.profit)} 差額:${fF(gap)} 契約${d.future.cnt}社 目標達成${ach}%]\n[案件: ${projInfo}]\n[社員: ${staffInfo}]\n[回答は短く具体的な数字で]`;

    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "" } });
    let accumulated = "";
    try {
      await apiStreamChat("/api/chat",
        { message: q + ctx, history: state.history.slice(-8) },
        (text) => { accumulated += text; dispatch({ type: "UPDATE_LAST_MESSAGE", text: accumulated }); },
        (error) => { dispatch({ type: "SET_TYPING", typing: false }); dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + error }); },
        () => { dispatch({ type: "SET_TYPING", typing: false }); dispatch({ type: "ADD_HISTORY", entry: { role: "assistant", content: accumulated } }); },
      );
    } catch (e) {
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + (e instanceof Error ? e.message : "通信エラー") });
    }
  }, [state, dispatch]);

  const doRagSearch = useCallback((q: string) => {
    setRagQuery(q);
    if (!q) { setRagResults([]); return; }
    const terms = q.toLowerCase().split(/\s+/);
    const scored = ragIndex.map((r) => {
      const score = terms.reduce((s, t) => s + (r.searchText.includes(t) || r.title.toLowerCase().includes(t) ? 1 : 0), 0);
      return { ...r, score };
    }).filter((r) => r.score > 0);
    scored.sort((a, b) => b.score - a.score);
    setRagResults(scored);
  }, [ragIndex]);

  const sendChat = useCallback(async () => {
    const q = input.trim();
    if (!q || state.typing) return;
    setInput("");
    if (tab === "rag") {
      doRagSearch(q);
      return;
    }
    await askAI(q);
  }, [input, state.typing, tab, askAI, doRagSearch]);

  const openRagResult = useCallback((r: RagResult) => {
    setTab("chat");
    askAI(`「${r.title}」について教えて。データ: ${r.detail}`);
  }, [askAI]);

  return (
    <div className="animate-fade-up h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex items-center gap-3 mb-3">
        <h2 className="text-lg font-bold">💬 AIチャット</h2>
        <div className="flex gap-1 ml-auto">
          <button
            onClick={() => setTab("chat")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              tab === "chat" ? "bg-primary text-white" : "bg-gray-100 text-gray-500"
            }`}
          >
            💬 チャット
          </button>
          <button
            onClick={() => setTab("rag")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              tab === "rag" ? "bg-primary text-white" : "bg-gray-100 text-gray-500"
            }`}
          >
            🔍 RAG検索
          </button>
        </div>
      </div>

      <div className="flex-1 bg-card rounded-xl border border-border flex flex-col overflow-hidden">
        {tab === "chat" ? (
          <div ref={msgsRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {state.messages.map((m, i) => {
              const isLastAi = m.ai && i === state.messages.length - 1;
              return (
              <div key={i} className={`flex ${m.ai ? "justify-start" : "justify-end"}`}>
                <div className="max-w-[80%]">
                  <div className={`px-3 py-2 rounded-xl text-xs whitespace-pre-wrap ${
                    m.ai ? "bg-gray-100 text-gray-800 rounded-bl-none" : "bg-primary text-white rounded-br-none"
                  }`}>
                    {m.ai && isLastAi ? (
                      <StreamingText text={m.text} isStreaming={state.typing} />
                    ) : m.text}
                  </div>
                  {m.actions && (
                    <div className="mt-2 flex gap-2 flex-wrap">
                      {m.actions.map((a, ai) => (
                        <button key={ai} className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-xs hover:border-primary transition-colors">
                          <span>{a.icon}</span>
                          <span className="font-semibold">{a.label}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
            })}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            <div className="text-sm font-semibold mb-2">🔍 社内データ検索</div>
            <div className="flex gap-1 flex-wrap mb-3">
              {["田中", "A社", "経費", "キャッシュ", "AI"].map((kw) => (
                <button key={kw} onClick={() => { setInput(kw); doRagSearch(kw); }}
                  className="px-2 py-1 text-[10px] rounded-full border border-border hover:border-primary hover:text-primary transition-colors">
                  {kw}
                </button>
              ))}
            </div>
            {ragResults.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                {ragQuery ? `「${ragQuery}」に一致するデータがありません` : "キーワードを入力して社内データを検索"}
              </div>
            ) : (
              <>
                <div className="text-[11px] text-gray-400 mb-2">{ragResults.length}件の検索結果</div>
                {ragResults.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => openRagResult(r)}
                    className="w-full text-left p-3 border border-border rounded-lg hover:border-primary transition-colors"
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-semibold flex items-center gap-1.5">
                        <span>{r.icon}</span> {r.title}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded shrink-0 ml-2"
                        style={{ background: r.color + "18", color: r.color }}>
                        {r.category}
                      </span>
                    </div>
                    <div className="text-[11px] text-gray-400">{r.detail}</div>
                  </button>
                ))}
              </>
            )}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-border p-3">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } }}
              rows={2}
              placeholder={tab === "chat" ? '例：「今月儲かってる？」「A社の案件は？」' : '例：「田中」「A社」「経費」「キャッシュ」'}
              className="flex-1 text-xs border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:border-primary"
            />
            <button
              onClick={sendChat}
              className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm self-end transition-colors ${
                input.trim() ? "bg-primary" : "bg-gray-300"
              }`}
            >
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
