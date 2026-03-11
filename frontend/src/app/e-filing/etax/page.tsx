"use client";

import Link from "next/link";

export default function ETaxPage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Link href="/e-filing" className="text-[#6366f1] text-xs hover:underline">{"\u2190 \u96FB\u5B50\u7533\u8ACB"}</Link>
      </div>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{"\u{1F3DB}\uFE0F"}</span>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"e-Tax \u96FB\u5B50\u7533\u544A"}</h1>
          <p className="text-xs text-[#9ca3af]">{"\u56FD\u7A0E\u5E81e-Tax\u3068\u9023\u643A\u3057\u305F\u6CD5\u4EBA\u7A0E\u30FB\u6D88\u8CBB\u7A0E\u306E\u96FB\u5B50\u7533\u544A"}</p>
        </div>
      </div>

      {/* Tax filing cards */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        {[
          { title: "\u6CD5\u4EBA\u7A0E \u78BA\u5B9A\u7533\u544A", period: "2025\u5E744\u6708\u301C2026\u5E743\u6708", deadline: "2026/05/31", status: "\u672A\u7533\u544A", color: "#ef4444" },
          { title: "\u6D88\u8CBB\u7A0E \u78BA\u5B9A\u7533\u544A", period: "2025\u5E744\u6708\u301C2026\u5E743\u6708", deadline: "2026/05/31", status: "\u672A\u7533\u544A", color: "#ef4444" },
          { title: "\u6CD5\u4EBA\u7A0E \u4E2D\u9593\u7533\u544A", period: "2026\u5E744\u6708\u301C9\u6708", deadline: "2026/11/30", status: "\u671F\u9593\u5916", color: "#9ca3af" },
          { title: "\u6D88\u8CBB\u7A0E \u4E2D\u9593\u7533\u544A", period: "2026\u5E744\u6708\u301C9\u6708", deadline: "2026/11/30", status: "\u671F\u9593\u5916", color: "#9ca3af" },
        ].map((item) => (
          <div key={item.title} className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="flex justify-between items-start">
              <h3 className="text-sm font-bold text-[#1a1a2e]">{item.title}</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ backgroundColor: item.color + "20", color: item.color }}>{item.status}</span>
            </div>
            <p className="text-[11px] text-[#6b7280] mt-1">{"\u5BFE\u8C61\u671F\u9593: "}{item.period}</p>
            <p className="text-[11px] text-[#6b7280]">{"\u7533\u544A\u671F\u9650: "}<b className="text-[#1a1a2e]">{item.deadline}</b></p>
            <button className="mt-3 w-full py-2 rounded-lg bg-[#f3f4f6] text-xs text-[#9ca3af] cursor-not-allowed">
              {"API\u9023\u643A\u6E96\u5099\u4E2D"}
            </button>
          </div>
        ))}
      </div>

      {/* Settings */}
      <div className="bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"e-Tax\u63A5\u7D9A\u8A2D\u5B9A"}</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u5229\u7528\u8005\u8B58\u5225\u756A\u53F7\uFF0816\u6841\uFF09"}</label>
            <input type="text" placeholder="0000-0000-0000-0000" maxLength={19} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" disabled />
          </div>
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u96FB\u5B50\u8A3C\u660E\u66F8"}</label>
            <div className="flex items-center gap-2">
              <span className="px-3 py-2 bg-[#f3f4f6] rounded-lg text-xs text-[#9ca3af] flex-1">{"\u672A\u8A2D\u5B9A"}</span>
              <button className="px-3 py-2 rounded-lg bg-[#f3f4f6] text-xs text-[#9ca3af] cursor-not-allowed">{"\u30A2\u30C3\u30D7\u30ED\u30FC\u30C9"}</button>
            </div>
          </div>
          <p className="text-[10px] text-[#9ca3af]">{"\u203B e-Tax\u9023\u643A\u306FAPI\u958B\u767A\u4E2D\u3067\u3059\u3002\u30DE\u30A4\u30CA\u30F3\u30D0\u30FC\u30AB\u30FC\u30C9\u307E\u305F\u306F\u6CD5\u4EBA\u306E\u96FB\u5B50\u8A3C\u660E\u66F8\u304C\u5FC5\u8981\u3067\u3059\u3002"}</p>
        </div>
      </div>
    </div>
  );
}
