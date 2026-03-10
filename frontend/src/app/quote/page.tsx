"use client";

import { useState } from "react";
import { useApp, type Quote } from "@/lib/store";
import { fF } from "@/lib/data";

type QuoteItem = { n: string; q: number; p: number };

export default function QuotePage() {
  const { state, dispatch } = useApp();
  const [mode, setMode] = useState<"none" | "manual" | "ai">("none");
  const [to, setTo] = useState("株式会社サンプル");
  const [person, setPerson] = useState("山田太郎");
  const [subject, setSubject] = useState("システム開発");
  const [expiry, setExpiry] = useState("2026/05/15");
  const [items, setItems] = useState<QuoteItem[]>([{ n: "システム設計・開発", q: 1, p: 3000000 }]);
  const [aiPrompt, setAiPrompt] = useState("A社向けのクラウド導入見積を作って");
  const [aiLoading, setAiLoading] = useState(false);

  const addRow = () => setItems([...items, { n: "", q: 1, p: 0 }]);

  const updateItem = (idx: number, field: keyof QuoteItem, value: string | number) => {
    const next = [...items];
    if (field === "n") next[idx] = { ...next[idx], n: value as string };
    else if (field === "q") next[idx] = { ...next[idx], q: parseInt(value as string) || 1 };
    else next[idx] = { ...next[idx], p: parseInt(value as string) || 0 };
    setItems(next);
  };

  const createQuote = () => {
    const validItems = items.filter(it => it.n && it.p);
    const total = validItems.reduce((s, it) => s + it.q * it.p, 0);
    const quote: Quote = {
      co: to, ps: person, total, tax: Math.round(total * 0.1),
      no: "QT-" + String(state.quotes.length + 1).padStart(4, "0"),
      items: validItems,
    };
    dispatch({ type: "ADD_QUOTE", quote });
    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "📝 見積作成完了！" } });
    setMode("none");
  };

  const aiGenerate = () => {
    setAiLoading(true);
    setTimeout(() => {
      const quote: Quote = {
        co: "A社（株式会社アルファ）", ps: "田中太郎",
        total: 3400000, tax: 340000,
        no: "QT-" + String(state.quotes.length + 1).padStart(4, "0"),
        items: [
          { n: "クラウド環境構築", q: 1, p: 2000000 },
          { n: "データ移行", q: 1, p: 800000 },
          { n: "運用保守3ヶ月", q: 3, p: 200000 },
        ],
      };
      dispatch({ type: "ADD_QUOTE", quote });
      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "🤖 AI見積生成完了！" } });
      setAiLoading(false);
      setMode("none");
    }, 2500);
  };

  const dlPDF = (idx: number) => {
    const q = state.quotes[idx];
    alert(`PDF出力: ${q.no}\n${q.co} 御中\n合計: ¥${(q.total + q.tax).toLocaleString()}\n\n※ jsPDFライブラリ未導入のためアラート表示`);
    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: `📥 PDF出力: ${q.no}` } });
  };

  return (
    <div className="animate-fade-up">
      <div className="text-lg font-bold mb-4">見積書</div>

      {/* Action buttons */}
      <div className="flex gap-3 mb-5">
        <button onClick={() => setMode("manual")} className="flex-1 py-4 rounded-lg bg-[#6366f1] text-white text-sm font-semibold hover:bg-[#4f46e5] transition-colors">
          📝 手動で作成
        </button>
        <button onClick={() => setMode("ai")} className="flex-1 py-4 rounded-lg bg-[#7c3aed] text-white text-sm font-semibold hover:bg-[#6d28d9] transition-colors">
          🤖 AIに依頼
        </button>
      </div>

      {/* Manual form */}
      {mode === "manual" && (
        <div className="card">
          <div className="text-sm font-bold mb-4">📝 見積書作成</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="mb-3">
              <label className="block text-[11px] font-semibold text-[#6b7280] mb-1">宛先</label>
              <input value={to} onChange={e => setTo(e.target.value)} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-md text-xs text-[#1a1a2e] outline-none focus:border-[#6366f1]" />
            </div>
            <div className="mb-3">
              <label className="block text-[11px] font-semibold text-[#6b7280] mb-1">担当者</label>
              <input value={person} onChange={e => setPerson(e.target.value)} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-md text-xs text-[#1a1a2e] outline-none focus:border-[#6366f1]" />
            </div>
            <div className="mb-3">
              <label className="block text-[11px] font-semibold text-[#6b7280] mb-1">件名</label>
              <input value={subject} onChange={e => setSubject(e.target.value)} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-md text-xs text-[#1a1a2e] outline-none focus:border-[#6366f1]" />
            </div>
            <div className="mb-3">
              <label className="block text-[11px] font-semibold text-[#6b7280] mb-1">有効期限</label>
              <input value={expiry} onChange={e => setExpiry(e.target.value)} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-md text-xs text-[#1a1a2e] outline-none focus:border-[#6366f1]" />
            </div>
          </div>
          {items.map((it, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <input value={it.n} onChange={e => updateItem(i, "n", e.target.value)} placeholder="品目" className="flex-[3] px-3 py-2 border border-[#e5e7eb] rounded-md text-xs outline-none focus:border-[#6366f1]" />
              <input value={it.q} onChange={e => updateItem(i, "q", e.target.value)} placeholder="数量" type="number" className="flex-1 px-3 py-2 border border-[#e5e7eb] rounded-md text-xs outline-none focus:border-[#6366f1]" />
              <input value={it.p} onChange={e => updateItem(i, "p", e.target.value)} placeholder="単価" type="number" className="flex-[2] px-3 py-2 border border-[#e5e7eb] rounded-md text-xs outline-none focus:border-[#6366f1]" />
            </div>
          ))}
          <button onClick={addRow} className="px-4 py-1.5 rounded-lg bg-[#f3f4f6] text-xs text-[#374151] mb-4 hover:bg-gray-200 transition-colors">+ 行追加</button>
          <div className="text-right">
            <button onClick={createQuote} className="px-5 py-2 rounded-lg bg-[#6366f1] text-white text-xs font-semibold hover:bg-[#4f46e5] transition-colors">作成</button>
          </div>
        </div>
      )}

      {/* AI form */}
      {mode === "ai" && (
        <div className="card">
          <div className="text-sm font-bold mb-4">🤖 AI見積作成</div>
          <div className="mb-3">
            <label className="block text-[11px] font-semibold text-[#6b7280] mb-1">AIへの指示</label>
            <textarea value={aiPrompt} onChange={e => setAiPrompt(e.target.value)} rows={3}
              className="w-full px-3 py-2 border border-[#e5e7eb] rounded-md text-xs text-[#1a1a2e] outline-none resize-y focus:border-[#6366f1]" />
          </div>
          <button onClick={aiGenerate} disabled={aiLoading}
            className="w-full py-2.5 rounded-lg bg-[#7c3aed] text-white text-xs font-semibold hover:bg-[#6d28d9] transition-colors disabled:opacity-50">
            {aiLoading ? "🤖 生成中..." : "🤖 生成"}
          </button>
          {aiLoading && (
            <div className="text-center py-5 text-[#7c3aed] animate-pulse-custom">🤖 生成中...</div>
          )}
        </div>
      )}

      {/* Created quotes */}
      {state.quotes.length > 0 && (
        <div className="card">
          <div className="text-sm font-bold mb-3">作成済み（{state.quotes.length}件）</div>
          {state.quotes.map((q, i) => (
            <div key={i} className="px-3 py-3 border border-[#eee] rounded-lg mb-2 flex justify-between items-center">
              <div>
                <div className="text-[13px] font-semibold">{q.co}</div>
                <div className="text-[11px] text-[#9ca3af]">¥{(q.total + q.tax).toLocaleString()} · {q.no}</div>
              </div>
              <button onClick={() => dlPDF(i)} className="px-3 py-1.5 rounded-lg bg-[#6366f1] text-white text-[11px] font-semibold hover:bg-[#4f46e5] transition-colors">
                📥 PDF
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
