"use client";

import { useState, useEffect, useCallback } from "react";
import { useApp } from "@/lib/store";
import { apiGet } from "@/lib/api";
import { fF, MO } from "@/lib/data";

// ===== API types =====
type ViewData = { revenue: number; cost: number; fixed: number; tax: number; profit: number; count: number };
type SummaryData = {
  future: ViewData; now: ViewData; cash: ViewData;
  gap: number; achievement_rate: number; total_revenue: number; total_cost: number;
  gross_profit: number; gross_margin: number; month: string;
  company_name: string; fixed_cost_monthly: number; tax_rate: number; annual_target: number;
};
type ProjectData = {
  id: string; name: string; full_name: string; project_name: string;
  revenue: number; cost: number; labor_cost: number; gross_profit: number;
  margin: number; status: string; progress: number; contact: string;
  contract_month: number; invoice_month: number; payment_month: number;
  staff: { name: string; hours: number; rate: number }[];
};
type StaffData = {
  staff_id: string; name: string; total_hours: number;
  projects: string[]; hourly_rate: number; monthly_salary: number;
};

// ===== Data hook =====
function useDashboard() {
  const { state } = useApp();
  const { currentMonth: cm, template } = state;
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [staffReport, setStaffReport] = useState<StaffData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, p, st] = await Promise.all([
        apiGet<SummaryData>(`/api/dashboard/summary?month=${cm}&template=${template}`),
        apiGet<ProjectData[]>(`/api/dashboard/projects?month=${cm}&template=${template}`),
        apiGet<StaffData[]>(`/api/dashboard/staff?month=${cm}&template=${template}`),
      ]);
      setSummary(s);
      setProjects(p);
      setStaffReport(st);
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, [cm, template]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return { summary, projects, staffReport, loading };
}

// ===== Components =====

function ThreeViewCards({ data }: { data: SummaryData }) {
  const { state } = useApp();
  const cm = state.currentMonth;
  const fxMonthly = data.fixed_cost_monthly;

  const views = [
    { key: "future" as const, label: "未来の数字", sub: "契約済＋請求前", icon: "🔮", color: "#7c3aed", revLabel: "契約済売上", vd: data.future },
    { key: "now" as const, label: "今の数字", sub: "請求済ベース", icon: "📊", color: "#3b82f6", revLabel: "請求済売上", vd: data.now },
    { key: "cash" as const, label: "キャッシュフロー", sub: "入金ベース", icon: "💰", color: "#10b981", revLabel: "入金額", vd: data.cash },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {views.map((v) => (
        <div key={v.key} className="bg-card rounded-xl border border-border p-5 hover:shadow-md transition-shadow cursor-pointer">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full" style={{ background: v.color }} />
            <span className="text-xs text-gray-400">{v.icon} {v.label}</span>
            <span className="ml-auto text-[10px] text-gray-400">{v.sub}</span>
          </div>
          <div className="text-2xl font-extrabold my-2" style={{ color: v.vd.profit >= 0 ? "#1a1a2e" : "#ef4444" }}>
            {v.vd.profit >= 0 ? "+" : "−"}{fF(Math.abs(v.vd.profit))}
          </div>
          <div className="space-y-1 text-[11px] text-gray-500 leading-relaxed">
            <div className="flex justify-between">
              <span>{v.revLabel}</span>
              <span style={{ color: v.color }}>+{fF(v.vd.revenue)}</span>
            </div>
            <div className="flex justify-between">
              <span>原価</span>
              <span className="text-red-500">−{fF(v.vd.cost)}</span>
            </div>
            <div className="flex justify-between">
              <span>固定費(月{fF(fxMonthly)}×{v.key === "cash" ? Math.max(1, cm) : cm + 1}月)</span>
              <span className="text-orange-500">−{fF(v.vd.fixed)}</span>
            </div>
            <div className="flex justify-between">
              <span>税金({Math.round(data.tax_rate * 100)}%)</span>
              <span className="text-yellow-600">−{fF(v.vd.tax)}</span>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-gray-100 text-[10px] text-gray-400">
            対象: <b style={{ color: v.color }}>{v.vd.count}社</b>
          </div>
        </div>
      ))}
    </div>
  );
}

function WorkingCapitalWarning({ gap }: { gap: number }) {
  if (gap <= 0) return null;
  const wMsg =
    gap > 10000000
      ? "🚨 運転資金が1,000万円超。請求サイクルの短縮または融資検討を推奨します"
      : gap > 5000000
        ? "⚠️ 運転資金が500万円超。請求書の早期発行で改善できます"
        : "✅ 運転資金は管理可能な範囲です";

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
      <div className="text-[11px] text-amber-800">⚠️ 未来とキャッシュフローの差額 ＝ 必要運転資金</div>
      <div className="text-xl font-extrabold text-amber-700 my-1">{fF(gap)}</div>
      <div className="text-[11px] text-gray-500 border-t border-dashed border-amber-200 pt-2 mt-2">
        🤖 <b>KATANA AI:</b> {wMsg}
      </div>
    </div>
  );
}

function OverviewTab({ data }: { data: SummaryData }) {
  const { state } = useApp();
  const cm = state.currentMonth;
  const ach = Math.round(data.achievement_rate);

  const segments = [
    { v: Math.max(0, data.future.profit), c: "#7c3aed" },
    { v: Math.max(0, data.now.profit), c: "#3b82f6" },
    { v: Math.max(0, data.cash.profit), c: "#10b981" },
  ];
  const total = segments.reduce((s, x) => s + x.v, 0);
  const r = 65, sw = 14, ci = 2 * Math.PI * r;

  let offset = 0;
  const circles = segments.map((seg, i) => {
    const pct = total > 0 ? seg.v / total : 0;
    const dl = ci * pct;
    const circle = (
      <circle
        key={i} cx="90" cy="90" r={r} fill="none"
        stroke={seg.c} strokeWidth={sw}
        strokeDasharray={`${dl} ${ci - dl}`}
        strokeDashoffset={-ci * offset}
        strokeLinecap="round"
        transform="rotate(-90 90 90)"
      />
    );
    offset += pct;
    return circle;
  });

  return (
    <>
      <div className="bg-card rounded-xl border border-border p-5">
        <div className="text-sm font-bold mb-4">収益サマリ</div>
        <div className="flex items-center gap-8">
          <svg width="180" height="180" viewBox="0 0 180 180">
            <circle cx="90" cy="90" r={r} fill="none" stroke="#f0f0f0" strokeWidth={sw} />
            {circles}
            <text x="90" y="85" textAnchor="middle" fontSize="11" fill="#9ca3af">{MO[cm]}利益</text>
            <text x="90" y="105" textAnchor="middle" fontSize="15" fill="#1a1a2e" fontWeight="700">{fF(data.future.profit)}</text>
          </svg>
          <div className="flex-1 space-y-1">
            {[
              { label: "今日までの売上", value: data.future.revenue, color: "#7c3aed" },
              { label: "今日までの利益", value: data.now.profit, color: "#3b82f6" },
              { label: "明日以降の売上", value: Math.max(0, data.future.revenue - data.now.revenue), color: "#10b981" },
            ].map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 text-xs text-gray-500 border-b border-gray-100">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ background: row.color }} />
                  {row.label}
                </span>
                <span className="font-semibold text-foreground">{fF(row.value)}</span>
              </div>
            ))}
            <div className="mt-3 text-xs text-gray-500">
              年間目標達成率: <b className="text-primary">{ach}%</b>
              <span className="text-[10px] text-gray-400 ml-2">（目標: {fF(data.annual_target)}）</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full mt-1">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.min(100, ach)}%` }} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function ProjectsTab({ projects, month }: { projects: ProjectData[]; month: string }) {
  return (
    <div className="bg-card rounded-xl border border-border p-5 overflow-x-auto">
      <div className="text-sm font-bold mb-4">📋 案件別利益（{month}時点）</div>
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-gray-50 text-gray-600">
            <th className="text-left p-2 font-semibold">案件</th>
            <th className="text-left p-2 font-semibold">取引先</th>
            <th className="text-right p-2 font-semibold">売上</th>
            <th className="text-right p-2 font-semibold">原価</th>
            <th className="text-right p-2 font-semibold">人件費</th>
            <th className="text-right p-2 font-semibold">粗利</th>
            <th className="p-2 font-semibold">利益率</th>
            <th className="p-2 font-semibold">進捗</th>
            <th className="p-2 font-semibold">ステータス</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => {
            if (p.status === "未契約") return null;
            const rateBadge =
              p.margin >= 50
                ? "bg-green-100 text-green-700"
                : p.margin >= 30
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-red-100 text-red-600";
            const statusBadge: Record<string, string> = {
              "入金済": "bg-green-100 text-green-700",
              "請求済": "bg-blue-100 text-blue-700",
              "契約済": "bg-purple-100 text-purple-700",
              "未契約": "bg-gray-100 text-gray-500",
            };

            return (
              <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer">
                <td className="p-2 font-bold">{p.project_name}</td>
                <td className="p-2">
                  {p.name}
                  <br />
                  <span className="text-[10px] text-gray-400">{p.contact}</span>
                </td>
                <td className="text-right p-2">{fF(p.revenue)}</td>
                <td className="text-right p-2 text-red-500">{fF(p.cost)}</td>
                <td className="text-right p-2 text-orange-500">{fF(p.labor_cost)}</td>
                <td className="text-right p-2" style={{ color: p.gross_profit > 0 ? "#059669" : "#ef4444" }}>
                  {fF(p.gross_profit)}
                </td>
                <td className="p-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${rateBadge}`}>
                    {p.margin}%
                  </span>
                </td>
                <td className="p-2">
                  <div className="w-14 h-1.5 bg-gray-100 rounded-full">
                    <div className="h-full bg-primary rounded-full" style={{ width: `${p.progress}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-400">{p.progress}%</span>
                </td>
                <td className="p-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${statusBadge[p.status] || ""}`}>
                    {p.status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StaffTab({ staffReport, projects, month }: { staffReport: StaffData[]; projects: ProjectData[]; month: string }) {
  const staffData = staffReport
    .filter((s) => s.total_hours > 0)
    .map((s) => {
      let totalRev = 0;
      projects.forEach((p) => {
        if (p.status === "未契約") return;
        const totalProjectHours = p.staff.reduce((a, x) => a + x.hours, 0);
        p.staff.forEach((sf) => {
          if (sf.name === s.name.substring(0, 2) || sf.name === s.name) {
            totalRev += totalProjectHours > 0 ? p.revenue * (sf.hours / totalProjectHours) : 0;
          }
        });
      });
      const labCost = s.total_hours * s.hourly_rate;
      const hourProfit = s.total_hours > 0 ? Math.round((totalRev - labCost) / s.total_hours) : 0;
      return { ...s, totalRev, labCost, hourProfit };
    })
    .sort((a, b) => b.hourProfit - a.hourProfit);

  return (
    <div className="bg-card rounded-xl border border-border p-5 overflow-x-auto">
      <div className="text-sm font-bold mb-4">👥 社員別利益（{month}時点）</div>
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-gray-50 text-gray-600">
            <th className="text-left p-2 font-semibold">採番</th>
            <th className="text-left p-2 font-semibold">社員名</th>
            <th className="text-left p-2 font-semibold">担当案件</th>
            <th className="text-right p-2 font-semibold">稼働時間</th>
            <th className="text-right p-2 font-semibold">売上貢献</th>
            <th className="text-right p-2 font-semibold">人件費</th>
            <th className="text-right p-2 font-semibold">時間利益</th>
          </tr>
        </thead>
        <tbody>
          {staffData.map((s) => {
            const hpBadge =
              s.hourProfit >= 3000
                ? "bg-green-100 text-green-700"
                : s.hourProfit >= 1000
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-red-100 text-red-600";
            return (
              <tr key={s.staff_id} className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer">
                <td className="p-2 font-semibold text-primary">{s.staff_id}</td>
                <td className="p-2 font-bold">{s.name}</td>
                <td className="p-2">{s.projects.join(", ")}</td>
                <td className="text-right p-2">{s.total_hours}h</td>
                <td className="text-right p-2">{fF(s.totalRev)}</td>
                <td className="text-right p-2 text-orange-500">{fF(s.labCost)}</td>
                <td className="text-right p-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${hpBadge}`}>
                    ¥{s.hourProfit.toLocaleString()}/h
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ===== Main Page =====

export default function DashboardPage() {
  const { state, dispatch } = useApp();
  const cm = state.currentMonth;
  const { summary, projects, staffReport, loading } = useDashboard();

  if (loading || !summary) {
    return (
      <div className="animate-fade-up flex items-center justify-center h-64">
        <div className="text-gray-400 text-sm">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-up space-y-4">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div className="text-lg font-bold">Welcome back, GOTO</div>
        <div className="text-xs text-gray-400 bg-gray-50 px-3 py-1 rounded-full">
          {summary.company_name}
        </div>
      </div>

      {/* Month selector */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-semibold">
            📅 {summary.month} <span className="text-[11px] font-normal text-gray-400">/ 2026年度</span>
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => dispatch({ type: "SET_MONTH", month: Math.max(0, cm - 1) })}
              className="px-3 py-1 rounded-lg bg-gray-100 text-sm hover:bg-gray-200 transition-colors"
            >
              ◀
            </button>
            <button
              onClick={() => dispatch({ type: "SET_MONTH", month: Math.min(11, cm + 1) })}
              className="px-3 py-1 rounded-lg bg-gray-100 text-sm hover:bg-gray-200 transition-colors"
            >
              ▶
            </button>
          </div>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {MO.map((m, i) => (
            <button
              key={m}
              onClick={() => dispatch({ type: "SET_MONTH", month: i })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                i === cm
                  ? "bg-primary text-white"
                  : i < cm
                    ? "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    : "bg-white text-gray-400 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Three-view cards */}
      <ThreeViewCards data={summary} />

      {/* Working capital warning */}
      <WorkingCapitalWarning gap={summary.gap} />

      {/* Tabs */}
      <div className="flex gap-1.5">
        {([
          { key: "overview" as const, label: "📊 収益サマリ" },
          { key: "projects" as const, label: "📋 案件別利益" },
          { key: "staff" as const, label: "👥 社員別利益" },
        ]).map((tab) => (
          <button
            key={tab.key}
            onClick={() => dispatch({ type: "SET_DASH_TAB", tab: tab.key })}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-colors border ${
              state.dashTab === tab.key
                ? "bg-primary text-white border-primary"
                : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {state.dashTab === "overview" && <OverviewTab data={summary} />}
      {state.dashTab === "projects" && <ProjectsTab projects={projects} month={summary.month} />}
      {state.dashTab === "staff" && <StaffTab staffReport={staffReport} projects={projects} month={summary.month} />}
    </div>
  );
}
