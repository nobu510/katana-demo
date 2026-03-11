"use client";

import Link from "next/link";

export default function InvoicePage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Link href="/e-filing" className="text-[#6366f1] text-xs hover:underline">{"\u2190 \u96FB\u5B50\u7533\u8ACB"}</Link>
      </div>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{"\u{1F4C4}"}</span>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"\u30A4\u30F3\u30DC\u30A4\u30B9\u5236\u5EA6\u5BFE\u5FDC"}</h1>
          <p className="text-xs text-[#9ca3af]">{"\u9069\u683C\u8ACB\u6C42\u66F8\uFF08\u30A4\u30F3\u30DC\u30A4\u30B9\uFF09\u306E\u767A\u884C\u30FB\u53D7\u9818\u30FB\u4FDD\u7BA1\u3092\u4E00\u5143\u7BA1\u7406"}</p>
        </div>
        <span className="ml-auto px-3 py-1 rounded-full bg-[#d1fae5] text-[#059669] text-[11px] font-bold">{"\u5BFE\u5FDC\u6E08"}</span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: "\u767A\u884C\u6E08\u30A4\u30F3\u30DC\u30A4\u30B9", value: "24\u4EF6", sub: "\u4ECA\u671F\u7D2F\u8A08", color: "#6366f1" },
          { label: "\u53D7\u9818\u30A4\u30F3\u30DC\u30A4\u30B9", value: "156\u4EF6", sub: "\u4ECA\u671F\u7D2F\u8A08", color: "#3b82f6" },
          { label: "\u4ED5\u5165\u7A0E\u984D\u63A7\u9664", value: "\u00A52,340,000", sub: "\u4ECA\u671F\u7D2F\u8A08", color: "#10b981" },
          { label: "\u767B\u9332\u756A\u53F7", value: "T1234567890123", sub: "\u6709\u52B9", color: "#059669" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-[#eee] p-4 text-center">
            <div className="text-[10px] text-[#9ca3af]">{s.label}</div>
            <div className="text-base font-extrabold mt-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[10px] text-[#9ca3af] mt-0.5">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Recent invoices */}
      <div className="bg-white rounded-xl border border-[#eee] p-5 mb-4">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"\u6700\u8FD1\u306E\u767A\u884C\u30A4\u30F3\u30DC\u30A4\u30B9"}</h3>
        <table className="tbl">
          <thead>
            <tr><th>{"\u756A\u53F7"}</th><th>{"\u767A\u884C\u65E5"}</th><th>{"\u5B9B\u5148"}</th><th className="ar">{"\u7A0E\u629C\u91D1\u984D"}</th><th className="ar">{"\u6D88\u8CBB\u7A0E"}</th><th>{"\u533A\u5206"}</th></tr>
          </thead>
          <tbody>
            {[
              { no: "INV-2026-001", date: "2026/04/15", to: "\u682A\u5F0F\u4F1A\u793E\u30A2\u30EB\u30D5\u30A1", amt: 4800000, tax: 480000, type: "10%" },
              { no: "INV-2026-002", date: "2026/04/20", to: "\u682A\u5F0F\u4F1A\u793E\u30D9\u30FC\u30BF", amt: 3200000, tax: 320000, type: "10%" },
              { no: "INV-2026-003", date: "2026/05/01", to: "\u682A\u5F0F\u4F1A\u793E\u30AC\u30F3\u30DE", amt: 12000000, tax: 1200000, type: "10%" },
            ].map((inv) => (
              <tr key={inv.no}>
                <td className="text-[#6366f1] font-semibold">{inv.no}</td>
                <td>{inv.date}</td>
                <td>{inv.to}</td>
                <td className="ar">{"\u00A5"}{inv.amt.toLocaleString()}</td>
                <td className="ar">{"\u00A5"}{inv.tax.toLocaleString()}</td>
                <td><span className="badge bg-[#ede9fe] text-[#6366f1]">{inv.type}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Settings */}
      <div className="bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"\u30A4\u30F3\u30DC\u30A4\u30B9\u8A2D\u5B9A"}</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u9069\u683C\u8ACB\u6C42\u66F8\u767A\u884C\u4E8B\u696D\u8005\u767B\u9332\u756A\u53F7"}</label>
            <input type="text" defaultValue="T1234567890123" className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm" />
          </div>
          <div>
            <label className="text-xs text-[#6b7280] block mb-1">{"\u30C7\u30D5\u30A9\u30EB\u30C8\u7A0E\u7387"}</label>
            <select className="w-full px-3 py-2 border border-[#e5e7eb] rounded-lg text-sm">
              <option>{"10%\uFF08\u6A19\u6E96\u7A0E\u7387\uFF09"}</option>
              <option>{"8%\uFF08\u8EFD\u6E1B\u7A0E\u7387\uFF09"}</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
