"use client";

import Link from "next/link";

export default function EGovPage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Link href="/e-filing" className="text-[#6366f1] text-xs hover:underline">{"\u2190 \u96FB\u5B50\u7533\u8ACB"}</Link>
      </div>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{"\u{1F6E1}\uFE0F"}</span>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"e-Gov \u793E\u4F1A\u4FDD\u967A\u96FB\u5B50\u7533\u8ACB"}</h1>
          <p className="text-xs text-[#9ca3af]">{"e-Gov\u7D4C\u7531\u3067\u793E\u4F1A\u4FDD\u967A\u30FB\u52B4\u50CD\u4FDD\u967A\u306E\u5C4A\u51FA\u3092\u30AA\u30F3\u30E9\u30A4\u30F3\u3067\u5B8C\u7D50"}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        {[
          { title: "\u7B97\u5B9A\u57FA\u790E\u5C4A", desc: "\u6BCE\u5E747\u6708\u306E\u5B9A\u6642\u6C7A\u5B9A", deadline: "2026/07/10", status: "\u671F\u9593\u5916", color: "#9ca3af" },
          { title: "\u6708\u984D\u5909\u66F4\u5C4A", desc: "\u56FA\u5B9A\u7684\u8CC3\u91D1\u5909\u52D5\u6642", deadline: "\u968F\u6642", status: "\u8A72\u5F53\u306A\u3057", color: "#9ca3af" },
          { title: "\u8CDE\u4E0E\u652F\u6255\u5C4A", desc: "\u8CDE\u4E0E\u652F\u7D66\u304B\u30895\u65E5\u4EE5\u5185", deadline: "\u652F\u7D66\u5F8C5\u65E5", status: "\u8A72\u5F53\u306A\u3057", color: "#9ca3af" },
          { title: "\u52B4\u50CD\u4FDD\u967A \u5E74\u5EA6\u66F4\u65B0", desc: "\u6BCE\u5E746\u6708\u0031\u65E5\u301C7\u6708\u0031\u0030\u65E5", deadline: "2026/07/10", status: "\u671F\u9593\u5916", color: "#9ca3af" },
          { title: "\u88AB\u4FDD\u967A\u8005\u8CC7\u683C\u53D6\u5F97\u5C4A", desc: "\u5165\u793E\u6642", deadline: "\u5165\u793E\u5F8C5\u65E5", status: "\u8A72\u5F53\u306A\u3057", color: "#9ca3af" },
          { title: "\u88AB\u4FDD\u967A\u8005\u8CC7\u683C\u55AA\u5931\u5C4A", desc: "\u9000\u8077\u6642", deadline: "\u9000\u8077\u5F8C5\u65E5", status: "\u8A72\u5F53\u306A\u3057", color: "#9ca3af" },
        ].map((item) => (
          <div key={item.title} className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="flex justify-between items-start">
              <h3 className="text-sm font-bold text-[#1a1a2e]">{item.title}</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ backgroundColor: item.color + "20", color: item.color }}>{item.status}</span>
            </div>
            <p className="text-[11px] text-[#6b7280] mt-1">{item.desc}</p>
            <p className="text-[11px] text-[#6b7280]">{"\u671F\u9650: "}<b className="text-[#1a1a2e]">{item.deadline}</b></p>
            <button className="mt-3 w-full py-2 rounded-lg bg-[#f3f4f6] text-xs text-[#9ca3af] cursor-not-allowed">{"API\u9023\u643A\u6E96\u5099\u4E2D"}</button>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"e-Gov\u63A5\u7D9A\u8A2D\u5B9A"}</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u0047\u30D3\u30BA\u0049\u0044"}</label>
            <input type="text" placeholder={"\u0047\u30D3\u30BA\u0049\u0044\u30A2\u30AB\u30A6\u30F3\u30C8"} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" disabled />
          </div>
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u4E8B\u696D\u6240\u756A\u53F7"}</label>
            <input type="text" placeholder={"\u793E\u4F1A\u4FDD\u967A\u306E\u4E8B\u696D\u6240\u756A\u53F7"} className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" disabled />
          </div>
          <p className="text-[10px] text-[#9ca3af]">{"\u203B e-Gov\u9023\u643A\u306FAPI\u958B\u767A\u4E2D\u3067\u3059\u3002\u0047\u30D3\u30BA\u0049\u0044\u306E\u53D6\u5F97\u304C\u5FC5\u8981\u3067\u3059\u3002"}</p>
        </div>
      </div>
    </div>
  );
}
