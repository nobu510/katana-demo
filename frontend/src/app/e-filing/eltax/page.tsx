"use client";

import Link from "next/link";

export default function ELTaxPage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Link href="/e-filing" className="text-[#6366f1] text-xs hover:underline">{"\u2190 \u96FB\u5B50\u7533\u8ACB"}</Link>
      </div>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{"\u{1F3E2}"}</span>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"eLTAX \u5730\u65B9\u7A0E\u96FB\u5B50\u7533\u544A"}</h1>
          <p className="text-xs text-[#9ca3af]">{"\u5730\u65B9\u7A0E\u30DD\u30FC\u30BF\u30EBeLTAX\u3068\u9023\u643A\u3057\u305F\u6CD5\u4EBA\u4F4F\u6C11\u7A0E\u30FB\u4E8B\u696D\u7A0E\u306E\u96FB\u5B50\u7533\u544A"}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        {[
          { title: "\u6CD5\u4EBA\u4F4F\u6C11\u7A0E", deadline: "2026/05/31", status: "\u672A\u7533\u544A", color: "#ef4444" },
          { title: "\u6CD5\u4EBA\u4E8B\u696D\u7A0E", deadline: "2026/05/31", status: "\u672A\u7533\u544A", color: "#ef4444" },
          { title: "\u7279\u5225\u6CD5\u4EBA\u4E8B\u696D\u7A0E", deadline: "2026/05/31", status: "\u672A\u7533\u544A", color: "#ef4444" },
          { title: "\u511F\u5374\u8CC7\u7523\u7533\u544A", deadline: "2027/01/31", status: "\u671F\u9593\u5916", color: "#9ca3af" },
        ].map((item) => (
          <div key={item.title} className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="flex justify-between items-start">
              <h3 className="text-sm font-bold text-[#1a1a2e]">{item.title}</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ backgroundColor: item.color + "20", color: item.color }}>{item.status}</span>
            </div>
            <p className="text-[11px] text-[#6b7280]">{"\u7533\u544A\u671F\u9650: "}<b className="text-[#1a1a2e]">{item.deadline}</b></p>
            <button className="mt-3 w-full py-2 rounded-lg bg-[#f3f4f6] text-xs text-[#9ca3af] cursor-not-allowed">{"API\u9023\u643A\u6E96\u5099\u4E2D"}</button>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"eLTAX\u63A5\u7D9A\u8A2D\u5B9A"}</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u5229\u7528\u8005ID"}</label>
            <input type="text" placeholder={"eLTAX\u5229\u7528\u8005ID"} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" disabled />
          </div>
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u63D0\u51FA\u5148\u81EA\u6CBB\u4F53"}</label>
            <input type="text" placeholder={"\u4F8B: \u5927\u962A\u5E02\u3001\u6771\u4EAC\u90FD"} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" disabled />
          </div>
          <p className="text-[10px] text-[#9ca3af]">{"\u203B eLTAX\u9023\u643A\u306FAPI\u958B\u767A\u4E2D\u3067\u3059\u3002PCdesk\u7B49\u306E\u5229\u7528\u8005ID\u304C\u5FC5\u8981\u3067\u3059\u3002"}</p>
        </div>
      </div>
    </div>
  );
}
