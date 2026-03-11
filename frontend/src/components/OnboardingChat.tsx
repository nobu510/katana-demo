"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useApp } from "@/lib/store";
import { apiPost } from "@/lib/api";
import StreamingText from "@/components/StreamingText";

type FixedCostBreakdownRaw = {
  personnel: number | null;
  rent: number | null;
  utilities: number | null;
  communication: number | null;
  lease: number | null;
  insurance: number | null;
  depreciation: number | null;
  interest: number | null;
  other: number | null;
};

type CompanyData = {
  industry: string | null;
  name: string | null;
  staff_count: number | null;
  fixed_cost_monthly: number | null;
  fixed_cost_breakdown?: FixedCostBreakdownRaw | null;
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

type Props = {
  onComplete?: () => void;
};

export default function OnboardingChat({ onComplete }: Props) {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState("");
  const [collected, setCollected] = useState<CompanyData>({ ...EMPTY_DATA });
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const [phase, setPhase] = useState<"registration" | "data-input">("registration");
  const [dataInputHistory, setDataInputHistory] = useState<{ role: string; content: string }[]>([]);
  const msgsRef = useRef<HTMLDivElement>(null);
  const initRef = useRef(false);

  // 初回メッセージを1回だけ追加
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    dispatch({
      type: "ADD_MESSAGE",
      message: {
        ai: true,
        text: "こんにちは！KATANA AIです。御社の経営を一刀両断します。\nまず、どんなお仕事をされていますか？",
      },
    });
  }, [dispatch]);

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

      // 登録確認された場合
      if (res.confirmed) {
        setTimeout(() => {
          // 固定費内訳があればstoreに反映（万円→円に変換）
          if (merged.fixed_cost_monthly != null) {
            const breakdown = res.extracted_data?.fixed_cost_breakdown;
            const hasBreakdown = breakdown && Object.values(breakdown).some(v => v != null);
            if (hasBreakdown && breakdown) {
              const costs: Record<string, number> = {};
              for (const [k, v] of Object.entries(breakdown)) {
                if (v != null) costs[k] = v * 10000;
              }
              dispatch({ type: "UPDATE_FIXED_COSTS", costs });
            } else {
              dispatch({ type: "UPDATE_FIXED_COSTS", costs: {
                personnel: 0, rent: 0, utilities: 0, communication: 0,
                lease: 0, insurance: 0, depreciation: 0, interest: 0,
                other: merged.fixed_cost_monthly * 10000,
              }});
            }
          }
          dispatch({ type: "REGISTER_COMPANY", companyName: merged.name || "", industry: merged.industry || "" });

          // データ入力フェーズへ遷移
          setPhase("data-input");
          setDataInputHistory([]);
          dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: "" } }); // clear for new phase

          // 業種に応じた初回ガイドメッセージ
          const industryGuides: Record<string, string> = {
            "AI": "まずは案件データを入力しましょう！\n取引先と案件名、受注額を教えてください。\n例：「A社のクラウド導入案件 480万、B社のAI研修 320万」",
            "IT": "まずは案件データを入力しましょう！\n取引先と案件名、受注額を教えてください。\n例：「A社のシステム開発 500万、B社のDX支援 300万」",
            "it": "まずは案件データを入力しましょう！\n取引先と案件名、受注額を教えてください。\n例：「A社のシステム開発 500万、B社のDX支援 300万」",
            "小売": "まずは売上データを入力しましょう。\n4月の商品カテゴリ別売上を教えてください。\n例：「和菓子 300万、洋菓子 200万、ギフト 150万」",
            "retail": "まずは売上データを入力しましょう。\n4月の商品カテゴリ別売上を教えてください。\n例：「和菓子 300万、洋菓子 200万、ギフト 150万」",
            "飲食": "まずはメニュー別売上を入力しましょう！\n4月の売上を教えてください。\n例：「ランチ 180万、ディナー 320万、テイクアウト 80万」",
            "建設": "まずは工事データを入力しましょう！\n受注中の工事名と金額を教えてください。\n例：「○○邸新築工事 3000万、△△ビル改修 1500万」",
            "製造": "まずは製品別売上を入力しましょう！\n4月の売上を教えてください。\n例：「製品A 500万、製品B 300万」",
            "サービス": "まずはサービス別売上を入力しましょう！\n4月の売上を教えてください。\n例：「コンサルティング 400万、研修 200万」",
          };
          const industry = merged.industry || "";
          const guide = Object.entries(industryGuides).find(([k]) => industry.toLowerCase().includes(k.toLowerCase()))?.[1]
            || `まずは売上データを入力しましょう。\n4月の売上を教えてください。`;

          setTimeout(() => {
            dispatch({
              type: "ADD_MESSAGE",
              message: { ai: true, text: `🎉 ${merged.name || "企業"}の登録が完了しました！\n\n${guide}\n\n💡 「スキップ」で後から入力もできます。` },
            });
          }, 500);
        }, 1500);
      }
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      console.error("[OnboardingChat] error:", errMsg);
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({
        type: "ADD_MESSAGE",
        message: { ai: true, text: `⚠️ 通信エラー: ${errMsg}\nもう一度お試しください。` },
      });
    }
  }, [input, state.typing, history, collected, mergeCollected, dispatch]);

  const sendDataInput = useCallback(async () => {
    const q = input.trim();
    if (!q || state.typing) return;
    setInput("");

    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: q } });

    // スキップ処理
    if (q === "スキップ" || q === "skip" || q === "後で") {
      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "了解です！後からチャットでいつでもデータ入力できます。ダッシュボードに移動します。" } });
      setTimeout(() => {
        dispatch({ type: "SET_DATA_INPUT_DONE" });
        onComplete?.();
      }, 1500);
      return;
    }

    dispatch({ type: "SET_TYPING", typing: true });
    const newHistory = [...dataInputHistory, { role: "user", content: q }];

    try {
      const res = await apiPost<{
        reply: string;
        actions: { type: string; data: Record<string, unknown> }[];
        input_complete: boolean;
      }>("/api/chat/data-input", {
        message: q,
        history: newHistory,
        industry: collected.industry || state.industry || "",
        company_name: state.companyName || "",
        current_clients: state.clients.map(c => ({ nm: c.nm, amt: c.amt, pj: c.pj })),
        current_staff: state.staff.map(s => ({ full: s.full, role: s.role })),
      });

      // アクションを実行（ADD_CLIENT, ADD_STAFF, UPDATE_FIXED_COSTS, LOG_WORK）
      if (res.actions && res.actions.length > 0) {
        for (const action of res.actions) {
          if (action.type === "ADD_CLIENT" && action.data) {
            const d = action.data;
            dispatch({
              type: "ADD_CLIENT",
              client: {
                id: String(d.id || String.fromCharCode(65 + state.clients.length)),
                nm: String(d.nm || ""),
                fl: String(d.fl || d.nm || ""),
                pj: String(d.pj || ""),
                amt: Number(d.amt) || 0,
                cst: Number(d.cst) || 0,
                cm: Number(d.cm) ?? 0,
                im: Number(d.im) ?? 0,
                pm: Number(d.pm) ?? 1,
                ct: String(d.ct || ""),
                staff: Array.isArray(d.staff) ? d.staff as { name: string; hrs: number; rate: number }[] : [],
                progress: Number(d.progress) || 0,
                inv: Array.isArray(d.inv) ? d.inv as { item: string; qty: number; cost: number }[] : [],
              },
            });
          } else if (action.type === "ADD_STAFF" && action.data) {
            const d = action.data;
            dispatch({
              type: "ADD_STAFF",
              staff: {
                id: String(d.id || `S${String(state.staff.length + 1).padStart(3, "0")}`),
                name: String(d.name || ""),
                full: String(d.full || ""),
                role: String(d.role || ""),
                rate: Number(d.rate) || 0,
                salary: Number(d.salary) || 0,
              },
            });
          } else if (action.type === "UPDATE_FIXED_COSTS" && action.data) {
            const d = action.data;
            const cat = String(d.category || "other");
            const amtMan = Number(d.amount_man) || 0;
            const validKeys = ["personnel", "rent", "utilities", "communication", "lease", "insurance", "depreciation", "interest", "other"];
            if (validKeys.includes(cat)) {
              dispatch({ type: "UPDATE_FIXED_COSTS", costs: { [cat]: amtMan * 10000 } as Partial<import("@/lib/data").FixedCostBreakdown> });
            }
          } else if (action.type === "LOG_WORK" && action.data) {
            const d = action.data;
            const staffName = String(d.staff_name || "");
            const clientNm = String(d.client_nm || "");
            const hours = Number(d.hours) || 0;
            if (staffName && clientNm && hours > 0) {
              const clientIdx = state.clients.findIndex(c => c.nm.includes(clientNm) || clientNm.includes(c.nm));
              if (clientIdx >= 0) {
                const client = state.clients[clientIdx];
                const existStaff = client.staff.find(s => s.name.includes(staffName) || staffName.includes(s.name));
                const staffRecord = state.staff.find(s => s.name.includes(staffName) || s.full.includes(staffName));
                const rate = staffRecord?.rate || existStaff?.rate || 2500;
                const newStaffList = existStaff
                  ? client.staff.map(s => s.name === existStaff.name ? { ...s, hrs: s.hrs + hours } : s)
                  : [...client.staff, { name: staffName, hrs: hours, rate }];
                dispatch({ type: "UPDATE_CLIENT", index: clientIdx, client: { staff: newStaffList } });
              }
            }
          }
        }
      }

      const reply = res.reply || "データを登録しました。";
      setDataInputHistory([...newHistory, { role: "assistant", content: reply }]);

      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: reply } });
      dispatch({ type: "SET_TYPING", typing: false });

      // データ入力完了
      if (res.input_complete) {
        setTimeout(() => {
          dispatch({ type: "SET_DATA_INPUT_DONE" });
          onComplete?.();
        }, 2000);
      }
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({
        type: "ADD_MESSAGE",
        message: { ai: true, text: `⚠️ 通信エラー: ${errMsg}\nもう一度お試しください。` },
      });
    }
  }, [input, state, dataInputHistory, collected, dispatch, onComplete]);

  // 取得済み項目のインジケーター
  const items = phase === "registration" ? [
    { key: "industry", label: "業種", done: !!collected.industry },
    { key: "name", label: "会社名", done: !!collected.name },
    { key: "staff_count", label: "社員数", done: collected.staff_count != null },
    { key: "fixed_cost_monthly", label: "固定費", done: collected.fixed_cost_monthly != null },
  ] : [
    { key: "sales", label: "売上", done: state.clients.length > 0 },
    { key: "cost", label: "原価", done: state.clients.some(c => c.cst > 0) },
    { key: "staff", label: "社員", done: state.staff.length > 0 },
    { key: "done", label: "完了", done: false },
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
              {phase === "registration" ? "企業登録" : "データ入力"}
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

        {/* Input - 画面下部に大きく表示 */}
        <div className="px-6 py-5 bg-[#0d0d1a] border-t border-white/5">
          <div className="flex gap-3 items-end max-w-[700px] mx-auto">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  phase === "registration" ? sendMessage() : sendDataInput();
                }
              }}
              rows={3}
              placeholder="メッセージを入力..."
              className="flex-1 px-5 py-4 bg-[#1a1a2e] border border-white/10 rounded-2xl text-base text-white placeholder-[#555] outline-none resize-none leading-relaxed focus:border-[#6366f1] transition-colors"
            />
            <button
              onClick={phase === "registration" ? sendMessage : sendDataInput}
              className={`w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl transition-all shrink-0 ${
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
