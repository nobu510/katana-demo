"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useApp } from "@/lib/store";
import { calc, fF, gSt, gSL, MO, TGT, RAG, expenseDemo, type Client } from "@/lib/data";
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

export default function ChatSidebar() {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState("");
  const [sideTab, setSideTab] = useState<"chat" | "rag">("chat");
  const [ragResults, setRagResults] = useState<RagResult[]>([]);
  const [ragQuery, setRagQuery] = useState("");
  const msgsRef = useRef<HTMLDivElement>(null);

  // Build RAG search index
  const ragIndex = useMemo((): RagResult[] => {
    const results: RagResult[] = [];
    state.clients.forEach((c) => {
      const staffNames = c.staff.map((s) => s.name + s.hrs + "h").join(", ");
      const profitRate = Math.round(((c.amt - c.cst) / c.amt) * 100);
      results.push({
        id: `client-${c.id}`, category: "取引先", icon: "🏢", color: "#6366f1",
        title: `${c.nm}（${c.fl}）- ${c.pj}`,
        detail: `売上¥${c.amt.toLocaleString()} / 原価¥${c.cst.toLocaleString()} / 利益率${profitRate}% / 担当:${staffNames} / 契約${MO[c.cm]} 請求${MO[c.im]} 入金${MO[c.pm]}`,
        searchText: `${c.nm} ${c.fl} ${c.pj} ${staffNames} ${c.ct}`.toLowerCase(),
      });
    });
    state.staff.forEach((s) => {
      let totalHrs = 0;
      const projects: string[] = [];
      state.clients.forEach((c) => {
        c.staff.forEach((sf) => {
          if (sf.name === s.name) { totalHrs += sf.hrs; projects.push(c.nm); }
        });
      });
      results.push({
        id: `staff-${s.id}`, category: "社員", icon: "👤", color: "#7c3aed",
        title: `${s.id} ${s.full} - ${s.role}`,
        detail: `時給¥${s.rate.toLocaleString()} / 月給¥${s.salary.toLocaleString()} / 稼働${totalHrs}h / 担当:${projects.join(",") || "なし"}`,
        searchText: `${s.id} ${s.name} ${s.full} ${s.role} ${projects.join(" ")}`.toLowerCase(),
      });
    });
    expenseDemo.forEach((e, i) => {
      results.push({
        id: `expense-${i}`, category: "経費", icon: "💰", color: "#d97706",
        title: `${e.cat} - ${e.item}`,
        detail: `¥${e.amt.toLocaleString()} / ${e.dt} / ${e.by}`,
        searchText: `${e.cat} ${e.item} ${e.by}`.toLowerCase(),
      });
    });
    RAG.forEach((r) => {
      results.push({
        id: `doc-${r.t}`, category: "文書", icon: "📄", color: r.c,
        title: r.t, detail: r.tx,
        searchText: `${r.t} ${r.tg} ${r.tx}`.toLowerCase(),
      });
    });
    results.push(
      { id: "view-future", category: "経営視点", icon: "🔮", color: "#10b981", title: "未来の数字", detail: "契約済売上 - 原価 - 固定費(月280万) - 税金(30%)", searchText: "未来 契約 受注 見込 予測" },
      { id: "view-now", category: "経営視点", icon: "📊", color: "#3b82f6", title: "今の数字", detail: "請求済売上 - 支払予定 - 日割固定費 - 税金(30%)", searchText: "今 請求 売掛 現在" },
      { id: "view-cash", category: "経営視点", icon: "💵", color: "#ef4444", title: "キャッシュフロー", detail: "入金済額 - 支払済額 - 日割固定費 - 税金", searchText: "キャッシュ cf 入金 資金繰り 現金" },
    );
    return results;
  }, [state.clients, state.staff]);

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

  useEffect(() => {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [state.messages, state.typing]);

  // ===== Command detection =====
  const detectCmd = useCallback(
    (q: string): string | null => {
      const { clients, staff, currentMonth: cm } = state;

      const moNum = q.match(/(\d+)月/);
      if (moNum && !q.includes("案件") && !q.includes("利益") && !q.includes("社員") && !q.includes("儲")) {
        const mi = MO.indexOf(parseInt(moNum[1]) + "月");
        if (mi >= 0) {
          dispatch({ type: "SET_MONTH", month: mi });
          const dd = calc(clients, mi, state.ocrAmount);
          return `📅 ${MO[mi]}に切り替えました\n🔮 未来: ${fF(dd.future.profit)}\n📊 今: ${fF(dd.now.profit)}\n💰 CF: ${fF(dd.cash.profit)}`;
        }
      }

      if (q.includes("案件") && (q.includes("登録") || q.includes("追加") || q.includes("作成"))) {
        let pjName = "新規案件";
        const b1 = q.indexOf("「"), b2 = q.indexOf("」");
        if (b1 >= 0 && b2 > b1) pjName = q.substring(b1 + 1, b2);
        let amt = 5000000;
        const am = q.match(/(\d+)万/);
        if (am) amt = parseInt(am[1]) * 10000;
        let coName = String.fromCharCode(65 + clients.length) + "社";
        const cm2 = q.match(/([A-Za-z]+)社/);
        if (cm2) coName = cm2[0];
        const newClient: Client = {
          id: String.fromCharCode(65 + clients.length),
          nm: coName, fl: coName, pj: pjName, amt, cst: Math.round(amt * 0.4),
          cm, im: Math.min(11, cm + 2), pm: Math.min(11, cm + 4),
          ct: "担当未定", staff: [{ name: "田中", hrs: Math.round(amt / 30000), rate: 3000 }],
          progress: 0, inv: [],
        };
        dispatch({ type: "ADD_CLIENT", client: newClient });
        dispatch({ type: "SET_DASH_TAB", tab: "projects" });
        return `✅ 案件登録完了！\n📋 案件名: ${pjName}\n🏢 取引先: ${coName}\n💰 受注額: ${fF(amt)}\n\nダッシュボードに反映済み（${clients.length + 1}社）`;
      }

      if ((q.includes("社員") || q.includes("スタッフ")) && (q.includes("登録") || q.includes("追加"))) {
        let sName = "新人太郎";
        const s1 = q.indexOf("「"), s2 = q.indexOf("」");
        if (s1 >= 0 && s2 > s1) sName = q.substring(s1 + 1, s2);
        const newSid = "S" + String(staff.length + 1).padStart(3, "0");
        dispatch({
          type: "ADD_STAFF",
          staff: { id: newSid, name: sName.substring(0, 2), full: sName, role: "エンジニア", rate: 2500, salary: 350000 },
        });
        dispatch({ type: "SET_DASH_TAB", tab: "staff" });
        return `✅ 社員登録完了！\n🆔 採番: ${newSid}\n👤 氏名: ${sName}`;
      }

      if (q.includes("請求") && (q.includes("出") || q.includes("発行"))) {
        for (let ci = 0; ci < clients.length; ci++) {
          if (q.includes(clients[ci].nm)) {
            dispatch({ type: "UPDATE_CLIENT", index: ci, client: { im: Math.min(clients[ci].im, cm) } });
            return `✅ ${clients[ci].nm}に請求書を発行しました\n💰 請求額: ${fF(clients[ci].amt)}\n\n「今の数字」に反映済み`;
          }
        }
      }

      if (q.includes("入金")) {
        for (let ci = 0; ci < clients.length; ci++) {
          if (q.includes(clients[ci].nm)) {
            dispatch({ type: "UPDATE_CLIENT", index: ci, client: { pm: Math.min(clients[ci].pm, cm) } });
            return `✅ ${clients[ci].nm}からの入金を確認しました\n💰 入金額: ${fF(clients[ci].amt)}\n\nキャッシュフローに反映済み`;
          }
        }
      }

      if (q.includes("案件別") || q.includes("案件一覧")) {
        dispatch({ type: "SET_DASH_TAB", tab: "projects" });
        return "📋 案件別利益テーブルを表示しました";
      }
      if (q.includes("社員別") || q.includes("一人当たり")) {
        dispatch({ type: "SET_DASH_TAB", tab: "staff" });
        return "👥 社員別利益テーブルを表示しました";
      }
      if (q.includes("収益") && q.includes("サマリ")) {
        dispatch({ type: "SET_DASH_TAB", tab: "overview" });
        return "📊 収益サマリを表示しました";
      }

      return null;
    },
    [state, dispatch]
  );

  const askAI = useCallback(
    async (q: string) => {
      const { clients, staff, currentMonth: cm } = state;
      dispatch({ type: "ADD_HISTORY", entry: { role: "user", content: q } });
      dispatch({ type: "SET_TYPING", typing: true });

      const d = calc(clients, cm, state.ocrAmount);
      const gap = d.future.profit - d.cash.profit;
      const ach = Math.round((d.future.rev / TGT) * 100);

      const projInfo = clients
        .filter((c) => cm >= c.cm)
        .map((c) => {
          const lab = c.staff.reduce((s, sf) => s + sf.hrs * sf.rate, 0);
          const gr = c.amt - lab - c.cst;
          const st = gSt(c, cm);
          return `${c.nm}(${c.pj}/売上${fF(c.amt)}/粗利${fF(gr)}/${gSL(st)}/担当:${c.staff.map((s) => s.name + s.hrs + "h").join("+")})`;
        })
        .join(", ");

      const staffInfo = staff
        .map((s) => {
          let hrs = 0;
          const pjs: string[] = [];
          clients.forEach((c) => {
            if (cm < c.cm) return;
            c.staff.forEach((sf) => {
              if (sf.name === s.name) { hrs += sf.hrs; pjs.push(c.nm); }
            });
          });
          return hrs > 0 ? `${s.full}(${s.id}): ${hrs}h, ${pjs.join("/")}, 時給¥${s.rate}` : null;
        })
        .filter(Boolean)
        .join("; ");

      const ctx = `\n[現在月:${MO[cm]} 未来利益:${fF(d.future.profit)} 今利益:${fF(d.now.profit)} CF利益:${fF(d.cash.profit)} 差額(運転資金):${fF(gap)} 契約${d.future.cnt}社 目標達成${ach}%]\n[案件: ${projInfo}]\n[社員: ${staffInfo}]\n[回答は短く具体的な数字で。箇条書きより文章で。来場者が感動する回答を]`;

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
    },
    [state, dispatch]
  );

  // ===== Main send handler =====
  const sendChat = useCallback(async () => {
    const q = input.trim();
    if (!q || state.typing) return;
    setInput("");

    if (sideTab === "rag") {
      doRagSearch(q);
      return;
    }

    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: q } });

    // Normal command detection
    const cmdResult = detectCmd(q);
    if (cmdResult) {
      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: cmdResult } });
      return;
    }

    // Fall through to AI
    await askAI(q);
  }, [input, state.typing, sideTab, detectCmd, askAI, dispatch, doRagSearch]);

  const openRagResult = useCallback((r: RagResult) => {
    setSideTab("chat");
    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: `${r.title}について教えて` } });
    askAI(`「${r.title}」について教えて。データ: ${r.detail}`);
  }, [askAI, dispatch]);

  if (!state.chatOpen) return null;

  return (
    <aside className="fixed top-0 right-0 w-80 h-screen bg-card border-l border-border z-50 shadow-lg flex flex-col">
      {/* Header */}
      <div className="border-b border-border shrink-0">
        <div className="h-14 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span>⚔️</span>
            <div>
              <div className="text-sm font-bold">AI経営アシスタント</div>
              <div className="text-[10px] text-green-600 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                Claude AI 接続中
              </div>
            </div>
          </div>
          <button
            onClick={() => dispatch({ type: "SET_CHAT_OPEN", open: false })}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            ✕
          </button>
        </div>
        {/* Tabs */}
        <div className="flex">
          <button
            onClick={() => setSideTab("chat")}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors border-b-2 ${
              sideTab === "chat"
                ? "border-primary text-primary"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            💬 チャット
          </button>
          <button
            onClick={() => setSideTab("rag")}
            className={`flex-1 py-2 text-xs font-medium text-center transition-colors border-b-2 ${
              sideTab === "rag"
                ? "border-primary text-primary"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            🔍 RAG検索
          </button>
        </div>
      </div>

      {/* Content */}
      {sideTab === "chat" ? (
        <div ref={msgsRef} className="flex-1 overflow-y-auto p-3 space-y-3">
          {state.messages.map((m, i) => {
            const isLastAi = m.ai && i === state.messages.length - 1;
            return (
            <div key={i} className={`flex ${m.ai ? "justify-start" : "justify-end"}`}>
              <div className="max-w-[90%]">
                <div
                  className={`px-3 py-2 rounded-xl text-xs whitespace-pre-wrap ${
                    m.ai
                      ? "bg-gray-100 text-gray-800 rounded-bl-none"
                      : "bg-primary text-white rounded-br-none"
                  }`}
                >
                  {m.ai && isLastAi ? (
                    <StreamingText text={m.text} isStreaming={state.typing} />
                  ) : m.text}
                </div>
                {m.actions && (
                  <div className="mt-2 space-y-1.5">
                    {m.actions.map((a, ai) => (
                      <button
                        key={ai}
                        className="w-full flex items-center gap-2 p-2 border border-border rounded-lg text-left hover:border-primary hover:bg-purple-50 transition-colors"
                      >
                        <span className="text-lg">{a.icon}</span>
                        <div>
                          <div className="text-xs font-semibold">{a.label}</div>
                          {a.desc && <div className="text-[10px] text-gray-400">{a.desc}</div>}
                        </div>
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
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {/* Quick search tags */}
          <div className="flex gap-1 flex-wrap mb-2">
            {["田中", "A社", "G社", "経費", "キャッシュ"].map((kw) => (
              <button key={kw} onClick={() => { setInput(kw); doRagSearch(kw); }}
                className="px-2 py-0.5 text-[10px] rounded-full border border-border hover:border-primary hover:text-primary transition-colors">
                {kw}
              </button>
            ))}
          </div>

          {ragResults.length === 0 ? (
            <div className="text-center py-6 text-gray-400 text-[11px]">
              {ragQuery ? `「${ragQuery}」に一致なし` : "キーワードで社内データを検索"}
            </div>
          ) : (
            <>
              <div className="text-[10px] text-gray-400 mb-1">{ragResults.length}件ヒット</div>
              {ragResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => openRagResult(r)}
                  className="w-full text-left p-2.5 border border-border rounded-lg hover:border-primary transition-colors"
                >
                  <div className="flex justify-between items-start gap-1 mb-1">
                    <span className="text-[11px] font-semibold flex items-center gap-1 leading-tight">
                      <span className="shrink-0">{r.icon}</span>
                      <span>{r.title}</span>
                    </span>
                    <span className="text-[9px] px-1 py-0.5 rounded shrink-0"
                      style={{ background: r.color + "18", color: r.color }}>
                      {r.category}
                    </span>
                  </div>
                  <div className="text-[10px] text-gray-400 leading-relaxed">{r.detail}</div>
                </button>
              ))}
            </>
          )}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border p-3 shrink-0">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
            }}
            rows={2}
            placeholder={
              sideTab === "chat"
                ? '例：「今月の利益は？」「A社に請求出して」'
                : '例：「田中」「A社」「経費」'
            }
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
    </aside>
  );
}
