"use client";

import { useState } from "react";
import { TRENDS } from "@/lib/data";
import { apiPost } from "@/lib/api";

export default function TrendPage() {
  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  const doSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setSearchResult(null);
    try {
      const res = await apiPost<{ reply?: string }>("/api/chat", {
        message: `以下のキーワードについて、中小企業の経営者向けに最新トレンドと具体的なアクションを3つ提案してください。短く具体的に。\nキーワード: ${query}`,
        history: [],
      });
      if (res.reply) setSearchResult(res.reply);
      else setSearchResult("検索エラー");
    } catch (e) {
      setSearchResult(e instanceof Error ? e.message : "エラー");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="animate-fade-up">
      {/* Search */}
      <div className="mb-4">
        <div className="flex gap-2 items-center">
          <input
            value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") doSearch(); }}
            placeholder="例：AI導入 補助金 経費削減..."
            className="flex-1 px-3 py-2.5 border border-[#e5e7eb] rounded-md text-sm text-[#1a1a2e] outline-none focus:border-[#6366f1]"
          />
          <button onClick={doSearch} className="px-5 py-2.5 rounded-lg bg-[#6366f1] text-white text-xs font-semibold hover:bg-[#4f46e5] transition-colors">
            🔍 AI検索
          </button>
        </div>
      </div>

      {/* Search result */}
      {searching && (
        <div className="text-center py-5 text-[#6b7280]">
          <div className="dots inline-flex"><span /><span /><span /></div>
          <div className="mt-2 text-xs">AI分析中...</div>
        </div>
      )}
      {searchResult && !searching && (
        <div className="card mb-4" style={{ borderLeft: "3px solid #6366f1" }}>
          <div className="text-xs font-bold text-[#6366f1] mb-2">🤖 KATANA AI分析結果: 「{query}」</div>
          <div className="text-xs text-[#374151] leading-relaxed whitespace-pre-wrap">{searchResult}</div>
        </div>
      )}

      {/* Trend categories */}
      {TRENDS.map(g => (
        <div key={g.cat} className="card mb-3">
          <div className="text-[15px] font-bold mb-3">{g.icon} {g.cat}</div>
          {g.items.map(it => (
            <div key={it.t} className="p-3 border border-[#f3f4f6] rounded-[10px] mb-2 cursor-pointer hover:border-[#6366f1] hover:bg-[#f5f3ff] transition-all">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[13px] font-bold text-[#1a1a2e]">{it.t}</span>
                <span className="badge" style={{ background: it.tc + "18", color: it.tc }}>{it.tag}</span>
              </div>
              <div className="text-[11px] text-[#6b7280] leading-relaxed">{it.s}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
