"use client";

import { useRouter } from "next/navigation";
import { useApp } from "@/lib/store";
import { expenseDemo, fF, MO } from "@/lib/data";

export default function ExpensePage() {
  const { state } = useApp();
  const router = useRouter();
  const cm = state.currentMonth;
  const totalExp = expenseDemo.reduce((s, e) => s + e.amt, 0);
  const catSum: Record<string, number> = {};
  expenseDemo.forEach(e => { catSum[e.cat] = (catSum[e.cat] || 0) + e.amt; });

  const catColors: Record<string, string> = {
    "交通費": "#3b82f6", "会議費": "#10b981", "消耗品費": "#f59e0b",
    "通信費": "#8b5cf6", "接待交際費": "#ef4444", "研修費": "#06b6d4",
  };

  const quickActions = [
    { icon: "📷", t: "レシート読取", d: "写真からAI自動入力", act: () => router.push("/ocr") },
    { icon: "📊", t: "経費分析", d: "カテゴリ別の傾向分析", act: () => {} },
    { icon: "💡", t: "節税提案", d: "AIが節税ポイントを提案", act: () => {} },
    { icon: "📋", t: "仕訳チェック", d: "AIが仕訳ミスを検出", act: () => {} },
    { icon: "🧾", t: "領収書整理", d: "電帳法に準拠した管理", act: () => {} },
    { icon: "📈", t: "予算vs実績", d: "経費予算の達成状況", act: () => {} },
  ];

  return (
    <div className="animate-fade-up">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="rounded-xl p-4 text-white text-center" style={{ background: "linear-gradient(135deg, #6366f1, #7c3aed)" }}>
          <div className="text-[10px] opacity-80">今月の経費合計</div>
          <div className="text-[22px] font-extrabold my-1">{fF(totalExp)}</div>
          <div className="text-[10px] opacity-70">{expenseDemo.length}件</div>
        </div>
        <div className="rounded-xl p-4 text-white text-center" style={{ background: "linear-gradient(135deg, #059669, #10b981)" }}>
          <div className="text-[10px] opacity-80">承認済み</div>
          <div className="text-[22px] font-extrabold my-1">{fF(Math.round(totalExp * 0.7))}</div>
          <div className="text-[10px] opacity-70">{Math.round(expenseDemo.length * 0.7)}件</div>
        </div>
        <div className="rounded-xl p-4 text-white text-center" style={{ background: "linear-gradient(135deg, #d97706, #f59e0b)" }}>
          <div className="text-[10px] opacity-80">未承認</div>
          <div className="text-[22px] font-extrabold my-1">{fF(Math.round(totalExp * 0.3))}</div>
          <div className="text-[10px] opacity-70">{Math.ceil(expenseDemo.length * 0.3)}件</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card mb-3">
        <div className="text-sm font-bold mb-3">🤖 AIクイックアクション</div>
        <div className="grid grid-cols-2 gap-2">
          {quickActions.map(a => (
            <button key={a.t} onClick={a.act}
              className="flex items-center gap-2.5 p-3 border border-[#f3f4f6] rounded-[10px] bg-white text-left hover:border-[#6366f1] hover:bg-[#f5f3ff] transition-all">
              <span className="text-2xl">{a.icon}</span>
              <div>
                <div className="text-xs font-bold text-[#1a1a2e]">{a.t}</div>
                <div className="text-[10px] text-[#9ca3af]">{a.d}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Recent expenses */}
      <div className="card mb-3">
        <div className="flex justify-between items-center mb-3">
          <div className="text-sm font-bold">📄 最近の経費（{MO[cm]}）</div>
          <div className="text-[11px] text-[#6366f1] cursor-pointer">AIに分析依頼 →</div>
        </div>
        <table className="tbl">
          <thead>
            <tr><th>日付</th><th>勘定科目</th><th>内容</th><th className="ar">金額</th><th>申請者</th></tr>
          </thead>
          <tbody>
            {expenseDemo.map((e, i) => (
              <tr key={i} className="cursor-pointer">
                <td className="text-[11px] text-[#6b7280]">{e.dt}</td>
                <td><span className="badge bg-[#f3f4f6] text-[#374151]">{e.cat}</span></td>
                <td className="text-xs">{e.item}</td>
                <td className="ar" style={{ fontWeight: 600 }}>{fF(e.amt)}</td>
                <td className="text-[11px] text-[#6b7280]">{e.by}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Category breakdown */}
      <div className="card">
        <div className="text-sm font-bold mb-3">📊 カテゴリ別内訳</div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(catSum).map(([k, v]) => (
            <div key={k} className="flex-1 min-w-[120px] p-2.5 bg-[#f9fafb] rounded-lg text-center">
              <div className="text-[10px] text-[#6b7280]">{k}</div>
              <div className="text-sm font-bold mt-0.5" style={{ color: catColors[k] || "#374151" }}>{fF(v)}</div>
              <div className="text-[9px] text-[#9ca3af]">{Math.round(v / totalExp * 100)}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
