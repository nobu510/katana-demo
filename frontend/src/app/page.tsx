"use client";

import { useApp } from "@/lib/store";
import { calc, fF, gSt, gSL, MO, TGT, FX, FASSETS, fixedCostTotal, FIXED_COST_LABELS, type FixedCostBreakdown } from "@/lib/data";

export default function DashboardPage() {
  const { state, dispatch } = useApp();

  // データ未入力の場合の空状態
  if (state.clients.length === 0) {
    const fcTotal = fixedCostTotal(state.fixedCosts);
    return (
      <div className="animate-fade-up">
        {state.companyName && (
          <div className="text-lg font-bold mb-4">Welcome, {state.companyName}</div>
        )}
        <div className="bg-white rounded-xl border border-[#eee] p-8 text-center mb-4">
          <div className="text-5xl mb-4">📊</div>
          <div className="text-lg font-bold text-[#1a1a2e] mb-2">売上データがまだありません</div>
          <p className="text-sm text-[#9ca3af] mb-4 max-w-md mx-auto">
            右のチャットで売上データを入力すると、3視点（未来・今・CF）で経営状況をリアルタイム分析します。
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => dispatch({ type: "SET_CHAT_OPEN", open: true })}
              className="px-5 py-2.5 bg-[#6366f1] text-white rounded-lg text-sm font-medium hover:bg-[#5558e6] transition-colors"
            >
              チャットでデータ入力
            </button>
          </div>
        </div>

        {/* 登録済み情報 */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="text-[10px] text-[#9ca3af] mb-1">業種</div>
            <div className="text-sm font-bold text-[#1a1a2e]">{state.industry || "未設定"}</div>
          </div>
          <div className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="text-[10px] text-[#9ca3af] mb-1">月額固定費</div>
            <div className="text-sm font-bold text-[#1a1a2e]">{fF(fcTotal)}</div>
          </div>
          <div className="bg-white rounded-xl border border-[#eee] p-4">
            <div className="text-[10px] text-[#9ca3af] mb-1">登録データ</div>
            <div className="text-sm font-bold text-[#9ca3af]">売上 0件 / 社員 0名</div>
          </div>
        </div>

        {/* 固定費内訳 */}
        {fcTotal > 0 && (
          <div className="bg-white rounded-xl border border-[#eee] p-5 mt-4">
            <div className="text-sm font-bold text-[#1a1a2e] mb-3">固定費内訳（月額）</div>
            <div className="grid grid-cols-3 gap-2">
              {(Object.entries(FIXED_COST_LABELS) as [keyof FixedCostBreakdown, string][]).map(([k, label]) => {
                const val = state.fixedCosts[k];
                if (val <= 0) return null;
                return (
                  <div key={k} className="flex justify-between text-xs py-1 px-2 bg-[#f9fafb] rounded">
                    <span className="text-[#6b7280]">{label}</span>
                    <span className="font-semibold text-[#1a1a2e]">{fF(val)}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between mt-2 pt-2 border-t border-[#f3f4f6] text-xs">
              <span className="font-bold">合計</span>
              <span className="font-bold text-[#6366f1]">{fF(fcTotal)}/月</span>
            </div>
          </div>
        )}

        <div className="bg-[#f5f3ff] rounded-xl border border-[#ede9fe] p-4 mt-4">
          <div className="text-xs text-[#6366f1] font-semibold mb-1">入力例（{state.industry || "業種"}）</div>
          <div className="text-[11px] text-[#6b7280] space-y-1">
            {(state.industry || "").match(/小売|retail|菓子|スーパー|食品/) ? (<>
              <p>「和菓子 300万、洋菓子 200万、ギフト 150万」</p>
              <p>「和菓子 原価率45%、洋菓子 原価率40%」</p>
            </>) : (state.industry || "").match(/飲食|restaurant|カフェ/) ? (<>
              <p>「ランチ 180万、ディナー 320万、テイクアウト 80万」</p>
              <p>「食材原価率 ランチ35%、ディナー30%」</p>
            </>) : (state.industry || "").match(/建設|construction|工事/) ? (<>
              <p>「○○邸新築工事 3000万、△△ビル改修 1500万」</p>
              <p>「外注費 新築1800万、改修800万」</p>
            </>) : (state.industry || "").match(/製造|manufacturing/) ? (<>
              <p>「製品A 500万、製品B 300万」</p>
              <p>「材料費 製品A 原価率55%」</p>
            </>) : (<>
              <p>「A社のシステム開発 500万、B社のDX支援 300万」</p>
              <p>「原価率 A社40%、B社35%」</p>
            </>)}
            <p>「田中太郎、エンジニア、月給45万」</p>
          </div>
        </div>
      </div>
    );
  }

  const cm = state.currentMonth;
  const d = calc(state.clients, cm, state.ocrAmount, state.fixedCosts);
  const gap = d.future.profit - d.cash.profit;
  const ach = Math.round((d.future.rev / TGT) * 100);

  const views = [
    { key: "future" as const, label: "未来の数字", sub: "契約済＋請求前", icon: "🔮", color: "#7c3aed", revLabel: "契約済売上", data: d.future },
    { key: "now" as const, label: "今の数字", sub: "請求済ベース", icon: "📊", color: "#3b82f6", revLabel: "請求済売上", data: d.now },
    { key: "cash" as const, label: "キャッシュフロー", sub: "入金ベース", icon: "💰", color: "#10b981", revLabel: "入金額", data: d.cash },
  ];

  // Donut chart
  const r = 65, sw = 14, ci = 2 * Math.PI * r;
  const segments = views.map(v => ({ v: Math.max(0, v.data.profit), c: v.color }));
  const total = segments.reduce((s, x) => s + x.v, 0);
  let offset = 0;
  const circles = segments.map((seg, i) => {
    const pct = total > 0 ? seg.v / total : 0;
    const dl = ci * pct;
    const el = <circle key={i} cx="90" cy="90" r={r} fill="none" stroke={seg.c} strokeWidth={sw} strokeDasharray={`${dl} ${ci - dl}`} strokeDashoffset={-ci * offset} strokeLinecap="round" transform="rotate(-90 90 90)" />;
    offset += pct;
    return el;
  });

  // Assets
  const recvAmt = state.clients.filter(c => gSt(c, cm) === "iv").reduce((s, c) => s + c.amt, 0);
  const faTotal = FASSETS.reduce((s, a) => s + a.val - a.dep, 0);
  const totalAssets = recvAmt + faTotal + d.cash.rev;

  // Staff data for staff tab
  const staffData = state.staff.map(s => {
    let totalHrs = 0, totalRev = 0;
    const projects: string[] = [];
    state.clients.forEach(c => {
      if (cm < c.cm) return;
      const totalProjHrs = c.staff.reduce((a, x) => a + x.hrs, 0);
      c.staff.forEach(sf => {
        if (sf.name === s.name) {
          totalHrs += sf.hrs;
          totalRev += totalProjHrs > 0 ? c.amt * (sf.hrs / totalProjHrs) : 0;
          if (!projects.includes(c.nm)) projects.push(c.nm);
        }
      });
    });
    const labCost = totalHrs * s.rate;
    const profit = totalRev - labCost - s.salary * (cm + 1);
    const hourProfit = totalHrs > 0 ? Math.round((totalRev - labCost) / totalHrs) : 0;
    return { ...s, totalHrs, totalRev, labCost, profit, hourProfit, projects };
  }).filter(s => s.totalHrs > 0).sort((a, b) => b.hourProfit - a.hourProfit);

  return (
    <div className="animate-fade-up">
      {state.companyName && (
        <div className="text-lg font-bold mb-4">Welcome back, {state.companyName}</div>
      )}

      {state.ocrDone && (
        <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-lg px-3.5 py-2.5 mb-3 text-xs text-[#059669]">
          ✅ OCR反映済（+{fF(state.ocrAmount)}）
        </div>
      )}

      {/* Month selector */}
      <div className="card">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-semibold">📅 {MO[cm]} <span className="text-[11px] font-normal text-[#9ca3af]">/ 2026年度</span></span>
          <div className="flex gap-1.5">
            <button onClick={() => dispatch({ type: "SET_MONTH", month: Math.max(0, cm - 1) })} className="px-3 py-1 rounded-lg bg-[#f3f4f6] text-sm hover:bg-gray-200 transition-colors text-[#374151]">◀</button>
            <button onClick={() => dispatch({ type: "SET_MONTH", month: Math.min(11, cm + 1) })} className="px-3 py-1 rounded-lg bg-[#f3f4f6] text-sm hover:bg-gray-200 transition-colors text-[#374151]">▶</button>
          </div>
        </div>
        <div className="flex gap-0.5">
          {MO.map((m, i) => (
            <button key={m} onClick={() => dispatch({ type: "SET_MONTH", month: i })}
              className={`flex-1 py-2 rounded-md text-[11px] font-medium transition-all ${
                i === cm ? "bg-[#6366f1] text-white font-semibold" : i < cm ? "bg-[#ede9fe] text-[#6366f1]" : "bg-[#f3f4f6] text-[#9ca3af]"
              }`}>
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* 3 View Cards */}
      <div className="grid grid-cols-3 gap-3.5 mb-4">
        {views.map(v => (
          <div key={v.key} className="bg-white rounded-[10px] border border-[#eee] p-[18px] relative overflow-hidden cursor-pointer hover:shadow-md transition-shadow animate-fade-up"
            style={{ borderTop: `3px solid ${v.color}` }}>
            <div className="text-[11px] text-[#9ca3af] flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: v.color }} />
              {v.icon} {v.label}
              <span className="ml-auto text-[10px]">{v.sub}</span>
            </div>
            <div className="text-[26px] font-extrabold my-2" style={{ color: v.data.profit >= 0 ? "#1a1a2e" : "#ef4444" }}>
              {v.data.profit >= 0 ? "+" : "−"}{fF(Math.abs(v.data.profit))}
            </div>
            <div className="text-[11px] text-[#6b7280] leading-[2.2]">
              {v.revLabel}<span className="float-right" style={{ color: v.color }}>+{fF(v.data.rev)}</span><br/>
              原価<span className="float-right text-[#ef4444]">−{fF(v.data.cost)}</span><br/>
              固定費(月280万×{v.key === "cash" ? Math.max(1, cm) : cm + 1}月)<span className="float-right text-[#f97316]">−{fF(v.data.fixed)}</span><br/>
              税金(30%)<span className="float-right text-[#eab308]">−{fF(v.data.tax)}</span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#f3f4f6] text-[10px] text-[#9ca3af]">
              対象: <b style={{ color: v.color }}>{v.data.cnt}社</b>
              <span className="float-right text-[#6366f1] cursor-pointer">→ AIに聞く</span>
            </div>
          </div>
        ))}
      </div>

      {/* Working capital gap */}
      {gap > 0 && (
        <div className="bg-[#fef3c7] border border-[#fcd34d] rounded-lg p-3.5 mb-3 text-center">
          <div className="text-[11px] text-[#92400e]">⚠️ 未来とキャッシュフローの差額 ＝ 必要運転資金</div>
          <div className="text-xl font-extrabold text-[#b45309] my-1">{fF(gap)}</div>
          <div className="text-[11px] text-[#6b7280] mt-1 pt-1.5 border-t border-dashed border-[#e5e7eb]">
            🤖 <b>KATANA AI:</b> {gap > 10000000
              ? "🚨 運転資金が1,000万円超。請求サイクルの短縮または融資検討を推奨します"
              : gap > 5000000
                ? "⚠️ 運転資金が500万円超。請求書の早期発行で改善できます"
                : "✅ 運転資金は管理可能な範囲です"}
          </div>
        </div>
      )}

      {/* Assets */}
      <div className="card" style={{ marginTop: 12 }}>
        <div className="text-sm font-bold mb-3">💎 資産状況（{MO[cm]}時点）</div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-[#f0fdf4] rounded-[10px] p-3 text-center">
            <div className="text-[10px] text-[#6b7280]">💰 現金（入金済）</div>
            <div className="text-base font-extrabold text-[#059669] mt-1">{fF(d.cash.rev)}</div>
          </div>
          <div className="bg-[#fef3c7] rounded-[10px] p-3 text-center">
            <div className="text-[10px] text-[#6b7280]">📄 売掛金（請求済未入金）</div>
            <div className="text-base font-extrabold text-[#d97706] mt-1">{fF(recvAmt)}</div>
            <div className="text-[9px] text-[#9ca3af] mt-0.5">
              {state.clients.filter(c => gSt(c, cm) === "iv").map(c => c.nm).join(", ") || "なし"}
            </div>
          </div>
          <div className="bg-[#eff6ff] rounded-[10px] p-3 text-center">
            <div className="text-[10px] text-[#6b7280]">🏢 固定資産（簿価）</div>
            <div className="text-base font-extrabold text-[#2563eb] mt-1">{fF(faTotal)}</div>
          </div>
        </div>
        <div className="flex justify-between px-3 py-2 bg-[#f9fafb] rounded-lg mb-3">
          <span className="text-xs font-bold text-[#1a1a2e]">📊 総資産</span>
          <span className="text-base font-extrabold text-[#1a1a2e]">{fF(totalAssets)}</span>
        </div>
        <div className="text-[11px] text-[#6b7280]"><b>固定資産明細:</b></div>
        <table className="tbl" style={{ marginTop: 6 }}>
          <thead><tr><th>資産名</th><th className="ar">取得価額</th><th className="ar">減価償却累計</th><th className="ar">簿価</th></tr></thead>
          <tbody>
            {FASSETS.map(a => (
              <tr key={a.nm}>
                <td>{a.nm}</td>
                <td className="ar">{fF(a.val)}</td>
                <td className="ar" style={{ color: "#ef4444" }}>{fF(a.dep)}</td>
                <td className="ar" style={{ color: "#2563eb", fontWeight: 600 }}>{fF(a.val - a.dep)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4">
        {([
          { key: "overview" as const, label: "📊 収益サマリ" },
          { key: "projects" as const, label: "📋 案件別利益" },
          { key: "staff" as const, label: "👥 社員別利益" },
        ]).map(tab => (
          <button key={tab.key} onClick={() => dispatch({ type: "SET_DASH_TAB", tab: tab.key })}
            className={`px-4 py-2 rounded-lg text-xs font-medium border transition-colors ${
              state.dashTab === tab.key ? "bg-[#6366f1] text-white border-[#6366f1]" : "bg-white text-[#6b7280] border-[#e5e7eb]"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {state.dashTab === "overview" && (
        <>
          <div className="card">
            <div className="text-sm font-bold mb-3.5">収益サマリ</div>
            <div className="flex items-center gap-8">
              <svg width="180" height="180" viewBox="0 0 180 180">
                <circle cx="90" cy="90" r={r} fill="none" stroke="#f0f0f0" strokeWidth={sw} />
                {circles}
                <text x="90" y="85" textAnchor="middle" fontSize="11" fill="#9ca3af">{MO[cm]}利益</text>
                <text x="90" y="105" textAnchor="middle" fontSize="15" fill="#1a1a2e" fontWeight="700">{fF(d.future.profit)}</text>
              </svg>
              <div className="flex-1">
                {[
                  { label: "今日までの売上", value: d.future.rev, color: "#7c3aed" },
                  { label: "今日までの利益", value: d.now.profit, color: "#3b82f6" },
                  { label: "明日以降の売上", value: Math.max(0, d.future.rev - d.now.rev), color: "#10b981" },
                ].map(row => (
                  <div key={row.label} className="flex justify-between py-1.5 text-xs text-[#6b7280] border-b border-[#f3f4f6]">
                    <span><span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: row.color }} />{row.label}</span>
                    <span className="font-semibold text-[#1a1a2e]">{fF(row.value)}</span>
                  </div>
                ))}
                <div className="mt-3 text-xs text-[#6b7280]">
                  年間目標達成率: <b className="text-[#6366f1]">{ach}%</b>
                </div>
                <div className="h-1 bg-[#f3f4f6] rounded-full mt-1 overflow-hidden">
                  <div className="h-full bg-[#6366f1] rounded-full transition-all" style={{ width: `${Math.min(100, ach)}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Bar chart */}
          <div className="card">
            <div className="text-sm font-bold mb-3.5">月別利益推移</div>
            <div className="flex items-end gap-1 h-[120px]">
              {MO.map((m, i) => {
                const dd = calc(state.clients, i, state.ocrAmount, state.fixedCosts);
                const mx = 40000000;
                return (
                  <div key={m} className="flex-1 flex flex-col items-center gap-1" style={{ opacity: i <= cm ? 1 : 0.15 }}>
                    <div className="flex gap-0.5 items-end h-[100px]">
                      <div className="w-1.5 rounded-t-sm transition-all duration-800" style={{ background: "#7c3aed", height: `${Math.max(2, Math.max(0, dd.future.profit) / mx * 90)}px` }} />
                      <div className="w-1.5 rounded-t-sm transition-all duration-800" style={{ background: "#3b82f6", height: `${Math.max(2, Math.max(0, dd.now.profit) / mx * 90)}px` }} />
                      <div className="w-1.5 rounded-t-sm transition-all duration-800" style={{ background: "#10b981", height: `${Math.max(2, Math.max(0, dd.cash.profit) / mx * 90)}px` }} />
                    </div>
                    <span className="text-[9px]" style={{ color: i === cm ? "#6366f1" : "#ccc", fontWeight: i === cm ? 700 : 400 }}>{m}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-4 justify-center mt-3">
              {views.map(p => (
                <span key={p.key} className="text-[10px] text-[#9ca3af]">
                  <span className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: p.color }} />{p.label}
                </span>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Projects tab */}
      {state.dashTab === "projects" && (
        <div className="card">
          <div className="text-sm font-bold mb-3.5">📋 案件別利益（{MO[cm]}時点）</div>
          <table className="tbl">
            <thead>
              <tr><th>案件</th><th>取引先</th><th className="ar">売上</th><th className="ar">原価</th><th className="ar">人件費</th><th className="ar">粗利</th><th>利益率</th><th>進捗</th><th>ステータス</th></tr>
            </thead>
            <tbody>
              {state.clients.map(c => {
                const st = gSt(c, cm);
                if (st === "pn") return null;
                const labCost = c.staff.reduce((s, sf) => s + sf.hrs * sf.rate, 0);
                const matCost = c.inv.reduce((s, iv) => s + iv.qty * iv.cost, 0);
                const gross = c.amt - labCost - matCost;
                const rate = Math.round(gross / c.amt * 100);
                const prog = cm >= c.cm ? Math.min(100, c.progress + cm * 5) : 0;
                const rateBadge = rate >= 50 ? "bg-[#d1fae5] text-[#059669]" : rate >= 30 ? "bg-[#fef3c7] text-[#b45309]" : "bg-[#fee2e2] text-[#dc2626]";
                const stBadge: Record<string, string> = { pd: "bg-[#d1fae5] text-[#059669]", iv: "bg-[#dbeafe] text-[#3b82f6]", ct: "bg-[#ede9fe] text-[#7c3aed]" };
                return (
                  <tr key={c.id} className="cursor-pointer">
                    <td><b>{c.pj}</b></td>
                    <td>{c.nm}<br/><span className="text-[10px] text-[#9ca3af]">{c.ct}</span></td>
                    <td className="ar">{fF(c.amt)}</td>
                    <td className="ar" style={{ color: "#ef4444" }}>{fF(matCost)}</td>
                    <td className="ar" style={{ color: "#f97316" }}>{fF(labCost)}</td>
                    <td className="ar" style={{ color: gross > 0 ? "#059669" : "#ef4444" }}>{fF(gross)}</td>
                    <td><span className={`badge ${rateBadge}`}>{rate}%</span></td>
                    <td>
                      <div className="prog" style={{ width: 60 }}><div className="prog-f" style={{ width: `${prog}%`, background: "#6366f1" }} /></div>
                      <span className="text-[10px] text-[#9ca3af]">{prog}%</span>
                    </td>
                    <td><span className={`badge ${stBadge[st] || ""}`}>{gSL(st)}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Staff tab */}
      {state.dashTab === "staff" && (
        <div className="card">
          <div className="text-sm font-bold mb-3.5">👥 社員別利益（{MO[cm]}時点）</div>
          <table className="tbl">
            <thead>
              <tr><th>採番</th><th>社員名</th><th>役職</th><th>担当案件</th><th className="ar">稼働時間</th><th className="ar">売上貢献</th><th className="ar">人件費</th><th className="ar">時間利益</th></tr>
            </thead>
            <tbody>
              {staffData.map(s => {
                const hpBadge = s.hourProfit >= 3000 ? "bg-[#d1fae5] text-[#059669]" : s.hourProfit >= 1000 ? "bg-[#fef3c7] text-[#b45309]" : "bg-[#fee2e2] text-[#dc2626]";
                return (
                  <tr key={s.id} className="cursor-pointer">
                    <td style={{ fontWeight: 600, color: "#6366f1" }}>{s.id}</td>
                    <td><b>{s.full}</b></td>
                    <td className="text-[11px] text-[#9ca3af]">{s.role}</td>
                    <td className="text-[11px]">{s.projects.join(", ")}</td>
                    <td className="ar">{s.totalHrs}h</td>
                    <td className="ar">{fF(s.totalRev)}</td>
                    <td className="ar" style={{ color: "#f97316" }}>{fF(s.labCost)}</td>
                    <td className="ar"><span className={`badge ${hpBadge}`}>¥{s.hourProfit.toLocaleString()}/h</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* News */}
      <div className="card">
        <div className="text-sm font-bold mb-3.5">社内ニュース</div>
        <div className="text-center py-8 text-[#9ca3af] text-[13px]">ニュースがありません</div>
      </div>
    </div>
  );
}
