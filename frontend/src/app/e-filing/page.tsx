"use client";

import Link from "next/link";

const SERVICES = [
  {
    id: "etax",
    icon: "\u{1F3DB}\uFE0F",
    title: "e-Tax",
    subtitle: "\u6CD5\u4EBA\u7A0E\u30FB\u6D88\u8CBB\u7A0E \u96FB\u5B50\u7533\u544A",
    description: "\u56FD\u7A0E\u5E81e-Tax\u3068\u9023\u643A\u3057\u3001\u6CD5\u4EBA\u7A0E\u30FB\u6D88\u8CBB\u7A0E\u306E\u96FB\u5B50\u7533\u544A\u3092KATANA\u304B\u3089\u76F4\u63A5\u5B9F\u884C",
    status: "\u6E96\u5099\u4E2D",
    statusColor: "#f59e0b",
    href: "/e-filing/etax",
    features: ["\u6CD5\u4EBA\u7A0E\u78BA\u5B9A\u7533\u544A", "\u6D88\u8CBB\u7A0E\u7533\u544A", "\u4E2D\u9593\u7533\u544A", "\u4FEE\u6B63\u7533\u544A"],
  },
  {
    id: "eltax",
    icon: "\u{1F3E2}",
    title: "eLTAX",
    subtitle: "\u5730\u65B9\u7A0E \u96FB\u5B50\u7533\u544A",
    description: "\u5730\u65B9\u7A0E\u30DD\u30FC\u30BF\u30EBeLTAX\u3068\u9023\u643A\u3057\u3001\u6CD5\u4EBA\u4F4F\u6C11\u7A0E\u30FB\u4E8B\u696D\u7A0E\u3092\u96FB\u5B50\u7533\u544A",
    status: "\u6E96\u5099\u4E2D",
    statusColor: "#f59e0b",
    href: "/e-filing/eltax",
    features: ["\u6CD5\u4EBA\u4F4F\u6C11\u7A0E", "\u6CD5\u4EBA\u4E8B\u696D\u7A0E", "\u7279\u5225\u6CD5\u4EBA\u4E8B\u696D\u7A0E", "\u511F\u5374\u8CC7\u7523\u7533\u544A"],
  },
  {
    id: "egov",
    icon: "\u{1F6E1}\uFE0F",
    title: "e-Gov",
    subtitle: "\u793E\u4F1A\u4FDD\u967A \u96FB\u5B50\u7533\u8ACB",
    description: "e-Gov\u7D4C\u7531\u3067\u793E\u4F1A\u4FDD\u967A\u30FB\u52B4\u50CD\u4FDD\u967A\u306E\u5C4A\u51FA\u3092\u30AA\u30F3\u30E9\u30A4\u30F3\u3067\u5B8C\u7D50",
    status: "\u6E96\u5099\u4E2D",
    statusColor: "#f59e0b",
    href: "/e-filing/egov",
    features: ["\u7B97\u5B9A\u57FA\u790E\u5C4A", "\u6708\u984D\u5909\u66F4\u5C4A", "\u8CDE\u4E0E\u652F\u6255\u5C4A", "\u5E74\u5EA6\u66F4\u65B0"],
  },
  {
    id: "invoice",
    icon: "\u{1F4C4}",
    title: "\u30A4\u30F3\u30DC\u30A4\u30B9\u5236\u5EA6",
    subtitle: "\u9069\u683C\u8ACB\u6C42\u66F8 \u767A\u884C\u30FB\u7BA1\u7406",
    description: "\u30A4\u30F3\u30DC\u30A4\u30B9\u5236\u5EA6\u306B\u5B8C\u5168\u5BFE\u5FDC\u3002\u9069\u683C\u8ACB\u6C42\u66F8\u306E\u767A\u884C\u30FB\u53D7\u9818\u30FB\u4FDD\u7BA1\u3092\u4E00\u5143\u7BA1\u7406",
    status: "\u5BFE\u5FDC\u6E08",
    statusColor: "#10b981",
    href: "/e-filing/invoice",
    features: ["\u9069\u683C\u8ACB\u6C42\u66F8\u767A\u884C", "\u53D7\u9818\u30A4\u30F3\u30DC\u30A4\u30B9\u7BA1\u7406", "\u4ED5\u5165\u7A0E\u984D\u63A7\u9664\u8A08\u7B97", "\u767B\u9332\u756A\u53F7\u7BA1\u7406"],
  },
  {
    id: "ebooks",
    icon: "\u{1F4DA}",
    title: "\u96FB\u5B50\u5E33\u7C3F\u4FDD\u5B58\u6CD5",
    subtitle: "\u8A3C\u6191\u306E\u96FB\u5B50\u4FDD\u5B58",
    description: "\u96FB\u5B50\u5E33\u7C3F\u4FDD\u5B58\u6CD5\u306B\u5BFE\u5FDC\u3002\u30BF\u30A4\u30E0\u30B9\u30BF\u30F3\u30D7\u4ED8\u4E0E\u30FB\u691C\u7D22\u8981\u4EF6\u3092\u81EA\u52D5\u3067\u5145\u8DB3",
    status: "\u5BFE\u5FDC\u6E08",
    statusColor: "#10b981",
    href: "/e-filing/ebooks",
    features: ["\u96FB\u5B50\u53D6\u5F15\u30C7\u30FC\u30BF\u4FDD\u5B58", "\u30B9\u30AD\u30E3\u30CA\u4FDD\u5B58", "\u30BF\u30A4\u30E0\u30B9\u30BF\u30F3\u30D7", "\u691C\u7D22\u6A5F\u80FD"],
  },
];

export default function EFilingPage() {
  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-[#1a1a2e]">{"\u96FB\u5B50\u7533\u8ACB\u30FB\u6CD5\u4EE4\u5BFE\u5FDC"}</h1>
          <p className="text-xs text-[#9ca3af] mt-1">
            {"\u004B\u0041\u0054\u0041\u004E\u0041\u304B\u3089\u5404\u7A2E\u96FB\u5B50\u7533\u8ACB\u3092\u76F4\u63A5\u5B9F\u884C\u3002\u65E5\u672C\u306E\u6CD5\u4EE4\u306B\u5B8C\u5168\u6E96\u62E0\u3002"}
          </p>
        </div>
        <span className="px-3 py-1 rounded-full bg-[#ede9fe] text-[#6366f1] text-[11px] font-semibold">
          {"5\u30B5\u30FC\u30D3\u30B9\u9023\u643A"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SERVICES.map((s) => (
          <Link
            key={s.id}
            href={s.href}
            className="bg-white rounded-xl border border-[#eee] p-5 hover:shadow-lg hover:border-[#6366f1]/30 transition-all group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="text-3xl">{s.icon}</div>
              <span
                className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                style={{
                  backgroundColor: s.statusColor + "20",
                  color: s.statusColor,
                }}
              >
                {s.status}
              </span>
            </div>
            <h2 className="text-sm font-bold text-[#1a1a2e] group-hover:text-[#6366f1] transition-colors">
              {s.title}
            </h2>
            <p className="text-[11px] text-[#6366f1] font-medium mt-0.5">{s.subtitle}</p>
            <p className="text-[11px] text-[#6b7280] mt-2 leading-relaxed">{s.description}</p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {s.features.map((f) => (
                <span
                  key={f}
                  className="px-2 py-0.5 rounded bg-[#f3f4f6] text-[10px] text-[#6b7280]"
                >
                  {f}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>

      {/* Compliance status */}
      <div className="mt-6 bg-white rounded-xl border border-[#eee] p-5">
        <h3 className="text-sm font-bold text-[#1a1a2e] mb-3">{"\u6CD5\u4EE4\u5BFE\u5FDC\u72B6\u6CC1"}</h3>
        <div className="space-y-2">
          {[
            { label: "\u96FB\u5B50\u5E33\u7C3F\u4FDD\u5B58\u6CD5", status: "\u5BFE\u5FDC\u6E08", pct: 100, color: "#10b981" },
            { label: "\u30A4\u30F3\u30DC\u30A4\u30B9\u5236\u5EA6", status: "\u5BFE\u5FDC\u6E08", pct: 100, color: "#10b981" },
            { label: "e-Tax\u9023\u643A", status: "\u958B\u767A\u4E2D", pct: 60, color: "#f59e0b" },
            { label: "eLTAX\u9023\u643A", status: "\u958B\u767A\u4E2D", pct: 40, color: "#f59e0b" },
            { label: "e-Gov\u9023\u643A", status: "\u8A2D\u8A08\u4E2D", pct: 20, color: "#6366f1" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3">
              <span className="text-xs text-[#6b7280] w-32">{item.label}</span>
              <div className="flex-1 h-2 bg-[#f3f4f6] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${item.pct}%`, backgroundColor: item.color }}
                />
              </div>
              <span
                className="text-[10px] font-semibold w-16 text-right"
                style={{ color: item.color }}
              >
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
