"use client";

import Link from "next/link";

export default function EBooksPage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Link href="/e-filing" className="text-[#6366f1] text-xs hover:underline">{"\u2190 \u96FB\u5B50\u7533\u8ACB"}</Link>
      </div>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{"\u{1F4DA}"}</span>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"\u96FB\u5B50\u5E33\u7C3F\u4FDD\u5B58\u6CD5\u5BFE\u5FDC"}</h1>
          <p className="text-xs text-[#9ca3af]">{"\u96FB\u5B50\u53D6\u5F15\u30C7\u30FC\u30BF\u30FB\u30B9\u30AD\u30E3\u30CA\u4FDD\u5B58\u306E\u6CD5\u7684\u8981\u4EF6\u3092\u81EA\u52D5\u5145\u8DB3"}</p>
        </div>
        <span className="ml-auto px-3 py-1 rounded-full bg-[#d1fae5] text-[#059669] text-[11px] font-bold">{"\u5BFE\u5FDC\u6E08"}</span>
      </div>

      {/* Compliance checklist */}
      <div className="bg-white rounded-xl border border-[#eee] p-5 mb-4">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"\u6CD5\u7684\u8981\u4EF6\u30C1\u30A7\u30C3\u30AF\u30EA\u30B9\u30C8"}</h3>
        <div className="space-y-2">
          {[
            { label: "\u96FB\u5B50\u53D6\u5F15\u30C7\u30FC\u30BF\u306E\u4FDD\u5B58", desc: "\u30E1\u30FC\u30EB\u30FBWeb\u7B49\u3067\u53D7\u9818\u3057\u305F\u8ACB\u6C42\u66F8\u7B49\u306E\u96FB\u5B50\u30C7\u30FC\u30BF\u4FDD\u5B58", done: true },
            { label: "\u30BF\u30A4\u30E0\u30B9\u30BF\u30F3\u30D7\u306E\u4ED8\u4E0E", desc: "\u7DCF\u52D9\u7701\u8A8D\u5B9A\u30BF\u30A4\u30E0\u30B9\u30BF\u30F3\u30D7\u306B\u3088\u308B\u6539\u3056\u3093\u9632\u6B62", done: true },
            { label: "\u691C\u7D22\u6A5F\u80FD\u306E\u78BA\u4FDD", desc: "\u53D6\u5F15\u5E74\u6708\u65E5\u30FB\u91D1\u984D\u30FB\u53D6\u5F15\u5148\u3067\u306E\u691C\u7D22\u304C\u53EF\u80FD", done: true },
            { label: "\u8A02\u6B63\u30FB\u524A\u9664\u306E\u5C65\u6B74\u7BA1\u7406", desc: "\u30C7\u30FC\u30BF\u306E\u8A02\u6B63\u30FB\u524A\u9664\u306E\u4E8B\u5B9F\u3068\u5185\u5BB9\u3092\u78BA\u8A8D\u53EF\u80FD", done: true },
            { label: "\u30B9\u30AD\u30E3\u30CA\u4FDD\u5B58\u5BFE\u5FDC", desc: "\u7D19\u306E\u9818\u53CE\u66F8\u3092\u30B9\u30AD\u30E3\u30F3\u3057\u3066\u539F\u672C\u5EC3\u68C4", done: true },
            { label: "\u5E33\u7C3F\u9593\u306E\u76F8\u4E92\u95A2\u9023\u6027", desc: "\u5E33\u7C3F\u3068\u8A3C\u6191\u306E\u7D10\u4ED8\u3051\u304C\u78BA\u8A8D\u53EF\u80FD", done: true },
          ].map((item) => (
            <div key={item.label} className="flex items-start gap-3 p-3 rounded-lg bg-[#f9fafb]">
              <span className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${item.done ? "bg-[#d1fae5] text-[#059669]" : "bg-[#fee2e2] text-[#dc2626]"}`}>
                {item.done ? "\u2713" : "\u00D7"}
              </span>
              <div>
                <div className="text-xs font-semibold text-[#1a1a2e]">{item.label}</div>
                <div className="text-[10px] text-[#9ca3af] mt-0.5">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Storage stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {[
          { label: "\u4FDD\u5B58\u6E08\u307F\u8A3C\u6191", value: "342\u4EF6", color: "#6366f1" },
          { label: "\u30BF\u30A4\u30E0\u30B9\u30BF\u30F3\u30D7\u6E08", value: "342\u4EF6", color: "#10b981" },
          { label: "\u30B9\u30C8\u30EC\u30FC\u30B8\u4F7F\u7528\u91CF", value: "1.2 GB", color: "#3b82f6" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-[#eee] p-4 text-center">
            <div className="text-[10px] text-[#9ca3af]">{s.label}</div>
            <div className="text-lg font-extrabold mt-1" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"\u8A3C\u6191\u691C\u7D22\uFF08\u96FB\u5B50\u5E33\u7C3F\u4FDD\u5B58\u6CD5 \u691C\u7D22\u8981\u4EF6\u5BFE\u5FDC\uFF09"}</h3>
        <div className="grid grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-[10px] text-[#6b7280] block mb-1">{"\u53D6\u5F15\u5E74\u6708\u65E5"}</label>
            <input type="date" className="w-full px-2 py-1.5 border border-[#e5e7eb] rounded-lg text-xs" />
          </div>
          <div>
            <label className="text-[10px] text-[#6b7280] block mb-1">{"\u301C"}</label>
            <input type="date" className="w-full px-2 py-1.5 border border-[#e5e7eb] rounded-lg text-xs" />
          </div>
          <div>
            <label className="text-[10px] text-[#6b7280] block mb-1">{"\u91D1\u984D\u7BC4\u56F2"}</label>
            <input type="text" placeholder={"\u00A50 \u301C \u00A5999,999"} className="w-full px-2 py-1.5 border border-[#e5e7eb] rounded-lg text-xs" />
          </div>
          <div>
            <label className="text-[10px] text-[#6b7280] block mb-1">{"\u53D6\u5F15\u5148"}</label>
            <input type="text" placeholder={"\u53D6\u5F15\u5148\u540D"} className="w-full px-2 py-1.5 border border-[#e5e7eb] rounded-lg text-xs" />
          </div>
        </div>
        <button className="px-4 py-2 rounded-lg bg-[#6366f1] text-white text-xs font-medium hover:bg-[#5558e6] transition-colors">
          {"\u691C\u7D22"}
        </button>
      </div>
    </div>
  );
}
