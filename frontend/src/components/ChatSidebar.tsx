"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/lib/store";
import { calc, fF, gSt, gSL, MO, TGT, RAG, expenseDemo, FIXED_COST_LABELS, fixedCostTotal, type Client, type FixedCostBreakdown } from "@/lib/data";
import { apiStreamChat, apiPost } from "@/lib/api";
import StreamingText from "@/components/StreamingText";

type RagResult = {
  id: string;
  category: string;
  icon: string;
  color: string;
  title: string;
  detail: string;
  searchText: string;
};

export default function ChatSidebar() {
  const { state, dispatch } = useApp();
  const router = useRouter();
  const [input, setInput] = useState("");
  const [sideTab, setSideTab] = useState<"chat" | "rag">("chat");
  const [ragResults, setRagResults] = useState<RagResult[]>([]);
  const [ragQuery, setRagQuery] = useState("");
  const msgsRef = useRef<HTMLDivElement>(null);

  // RAG index
  const ragIndex = useMemo((): RagResult[] => {
    const results: RagResult[] = [];
    state.clients.forEach((c) => {
      const staffNames = c.staff.map((s) => s.name + s.hrs + "h").join(", ");
      const profitRate = Math.round(((c.amt - c.cst) / c.amt) * 100);
      results.push({
        id: `client-${c.id}`, category: "取引先", icon: "🏢", color: "#6366f1",
        title: `${c.nm}（${c.fl}）- ${c.pj}`,
        detail: `売上¥${c.amt.toLocaleString()} / 原価¥${c.cst.toLocaleString()} / 利益率${profitRate}% / 担当:${staffNames}`,
        searchText: `${c.nm} ${c.fl} ${c.pj} ${staffNames} ${c.ct}`.toLowerCase(),
      });
    });
    state.staff.forEach((s) => {
      let totalHrs = 0;
      const projects: string[] = [];
      state.clients.forEach((c) => {
        c.staff.forEach((sf) => {
          if (sf.name === s.name) { totalHrs += sf.hrs; projects.push(c.nm); }
        });
      });
      results.push({
        id: `staff-${s.id}`, category: "社員", icon: "👤", color: "#7c3aed",
        title: `${s.id} ${s.full} - ${s.role}`,
        detail: `時給¥${s.rate.toLocaleString()} / 月給¥${s.salary.toLocaleString()} / 稼働${totalHrs}h`,
        searchText: `${s.id} ${s.name} ${s.full} ${s.role} ${projects.join(" ")}`.toLowerCase(),
      });
    });
    expenseDemo.forEach((e, i) => {
      results.push({
        id: `expense-${i}`, category: "経費", icon: "💰", color: "#d97706",
        title: `${e.cat} - ${e.item}`,
        detail: `¥${e.amt.toLocaleString()} / ${e.dt} / ${e.by}`,
        searchText: `${e.cat} ${e.item} ${e.by}`.toLowerCase(),
      });
    });
    RAG.forEach((r) => {
      results.push({
        id: `doc-${r.t}`, category: "文書", icon: "📄", color: r.c,
        title: r.t, detail: r.tx,
        searchText: `${r.t} ${r.tg} ${r.tx}`.toLowerCase(),
      });
    });
    return results;
  }, [state.clients, state.staff]);

  const doRagSearch = useCallback((q: string) => {
    setRagQuery(q);
    if (!q) { setRagResults([]); return; }
    const terms = q.toLowerCase().split(/\s+/);
    const scored = ragIndex.map((r) => {
      const score = terms.reduce((s, t) => s + (r.searchText.includes(t) || r.title.toLowerCase().includes(t) ? 1 : 0), 0);
      return { ...r, score };
    }).filter((r) => r.score > 0).sort((a, b) => b.score - a.score);
    setRagResults(scored);
  }, [ragIndex]);

  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [state.messages, state.typing]);

  // Command detection matching HTML exactly
  const detectCmd = useCallback((q: string): string | null => {
    const { clients, staff, currentMonth: cm } = state;

    // 固定費の表示
    if ((q.includes("固定費") && (q.includes("見") || q.includes("確認") || q.includes("表示") || q.includes("内訳") || q.includes("いくら"))) ||
        q === "固定費") {
      const fc = state.fixedCosts;
      const total = fixedCostTotal(fc);
      const lines = Object.entries(FIXED_COST_LABELS)
        .map(([k, label]) => {
          const val = fc[k as keyof FixedCostBreakdown];
          return val > 0 ? `  ${label}: ${fF(val)}` : null;
        }).filter(Boolean).join("\n");
      return `📊 現在の固定費内訳（月額）\n\n${lines || "  未設定"}\n\n合計: ${fF(total)}/月\n\n💡 内訳を変更するには「家賃を35万に変更」のように話しかけてください`;
    }

    // Navigation commands
    if (q.includes("レシート") || q.includes("スキャン")) {
      router.push("/ocr");
      return "📷 レシートスキャン画面を開きました";
    }
    if (q.includes("見積") && (q.includes("作") || q.includes("開"))) {
      router.push("/quote");
      return "📝 見積書画面を開きました";
    }
    if (q.includes("ホーム") || q.includes("ダッシュボード") || q.includes("戻")) {
      dispatch({ type: "SET_DASH_TAB", tab: "overview" });
      router.push("/");
      return "🏠 ダッシュボードに戻りました";
    }

    // Tab switching
    if (q.includes("案件別") || q.includes("案件一覧")) {
      dispatch({ type: "SET_DASH_TAB", tab: "projects" });
      router.push("/");
      return "📋 案件別利益テーブルを表示しました";
    }
    if (q.includes("社員別") || q.includes("一人当たり")) {
      dispatch({ type: "SET_DASH_TAB", tab: "staff" });
      router.push("/");
      return "👥 社員別利益テーブルを表示しました";
    }
    if (q.includes("収益") && q.includes("サマリ")) {
      dispatch({ type: "SET_DASH_TAB", tab: "overview" });
      router.push("/");
      return "📊 収益サマリを表示しました";
    }

    // Project registration
    if (q.includes("案件") && (q.includes("登録") || q.includes("追加") || q.includes("作成"))) {
      let pjName = "新規案件";
      const b1 = q.indexOf("「"), b2 = q.indexOf("」");
      if (b1 >= 0 && b2 > b1) pjName = q.substring(b1 + 1, b2);
      let amt = 5000000;
      const am = q.match(/(\d+)万/);
      if (am) amt = parseInt(am[1]) * 10000;
      let coName = String.fromCharCode(65 + clients.length) + "社";
      const cm2 = q.match(/([A-Za-z]+)社/);
      if (cm2) coName = cm2[0];
      const newClient: Client = {
        id: String.fromCharCode(65 + clients.length),
        nm: coName, fl: coName, pj: pjName, amt, cst: Math.round(amt * 0.4),
        cm, im: Math.min(11, cm + 2), pm: Math.min(11, cm + 4),
        ct: "担当未定", staff: [{ name: "田中", hrs: Math.round(amt / 30000), rate: 3000 }],
        progress: 0, inv: [],
      };
      dispatch({ type: "ADD_CLIENT", client: newClient });
      dispatch({ type: "SET_DASH_TAB", tab: "projects" });
      router.push("/");
      const nd = calc([...clients, newClient], cm, state.ocrAmount);
      return `✅ 案件登録完了！\n📋 案件名: ${pjName}\n🏢 取引先: ${coName}\n💰 受注額: ${fF(amt)}\n\nダッシュボードに反映済み（${clients.length + 1}社）\n🔮 未来: ${fF(nd.future.profit)}`;
    }

    // Staff registration
    if ((q.includes("社員") || q.includes("スタッフ")) && (q.includes("登録") || q.includes("追加"))) {
      let sName = "新人太郎";
      const s1 = q.indexOf("「"), s2 = q.indexOf("」");
      if (s1 >= 0 && s2 > s1) sName = q.substring(s1 + 1, s2);
      const newSid = "S" + String(staff.length + 1).padStart(3, "0");
      dispatch({
        type: "ADD_STAFF",
        staff: { id: newSid, name: sName.substring(0, 2), full: sName, role: "エンジニア", rate: 2500, salary: 350000 },
      });
      // Assign to largest project
      const assignPj = clients.filter(c => cm >= c.cm).sort((a, b) => b.amt - a.amt)[0];
      if (assignPj) {
        const idx = clients.indexOf(assignPj);
        dispatch({ type: "UPDATE_CLIENT", index: idx, client: { staff: [...assignPj.staff, { name: sName.substring(0, 2), hrs: 40, rate: 2500 }] } });
      }
      dispatch({ type: "SET_DASH_TAB", tab: "staff" });
      router.push("/");
      return `✅ 社員登録完了！\n🆔 採番: ${newSid}\n👤 氏名: ${sName}\n💼 役職: エンジニア\n⏰ 時給: ¥2,500${assignPj ? `\n📋 担当: ${assignPj.nm}(${assignPj.pj})` : ""}\n\n社員別利益テーブルに反映済み`;
    }

    // Invoice
    if (q.includes("請求") && (q.includes("出") || q.includes("発行"))) {
      for (let ci = 0; ci < clients.length; ci++) {
        if (q.includes(clients[ci].nm)) {
          dispatch({ type: "UPDATE_CLIENT", index: ci, client: { im: Math.min(clients[ci].im, cm) } });
          router.push("/");
          return `✅ ${clients[ci].nm}に請求書を発行しました\n💰 請求額: ${fF(clients[ci].amt)}\n\n「今の数字」に反映済み`;
        }
      }
      return "⚠️ 取引先名を指定してください\n例: 「A社に請求出して」";
    }

    // Payment
    if (q.includes("入金")) {
      for (let ci = 0; ci < clients.length; ci++) {
        if (q.includes(clients[ci].nm)) {
          dispatch({ type: "UPDATE_CLIENT", index: ci, client: { pm: Math.min(clients[ci].pm, cm) } });
          router.push("/");
          return `✅ ${clients[ci].nm}からの入金を確認しました\n💰 入金額: ${fF(clients[ci].amt)}\n\nキャッシュフローに反映済み`;
        }
      }
      return "⚠️ 取引先名を指定してください\n例: 「A社の入金確認」";
    }

    // Month change (only if no other keywords)
    if (!q.includes("案件") && !q.includes("利益") && !q.includes("社員") && !q.includes("儲")) {
      const qq = q.replace(/[０-９]/g, (s) => String.fromCharCode(s.charCodeAt(0) - 0xFEE0));
      const moNum = qq.match(/(\d+)月/);
      if (moNum) {
        const mi = MO.indexOf(parseInt(moNum[1]) + "月");
        if (mi >= 0) {
          dispatch({ type: "SET_MONTH", month: mi });
          router.push("/");
          const dd = calc(clients, mi, state.ocrAmount);
          return `📅 ${MO[mi]}に切り替えました\n\n🔮 未来: ${fF(dd.future.profit)}\n📊 今: ${fF(dd.now.profit)}\n💰 CF: ${fF(dd.cash.profit)}`;
        }
      }
    }

    return null;
  }, [state, dispatch, router]);

  // 固定費更新AI
  const askFixedCostAI = useCallback(async (q: string) => {
    dispatch({ type: "ADD_HISTORY", entry: { role: "user", content: q } });
    dispatch({ type: "SET_TYPING", typing: true });
    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "" } });

    try {
      const currentCosts: Record<string, number> = {};
      for (const [k, label] of Object.entries(FIXED_COST_LABELS)) {
        currentCosts[label] = state.fixedCosts[k as keyof FixedCostBreakdown] / 10000; // 万円単位
      }
      const res = await apiPost<{ reply: string; updated_costs?: Record<string, number> | null }>("/api/chat/fixed-costs", {
        message: q,
        history: state.history.slice(-8),
        current_costs: currentCosts,
      });

      if (res.updated_costs) {
        const costs: Partial<FixedCostBreakdown> = {};
        for (const [k, v] of Object.entries(res.updated_costs)) {
          if (v != null) (costs as Record<string, number>)[k] = v * 10000; // 万円→円
        }
        dispatch({ type: "UPDATE_FIXED_COSTS", costs });
      }

      const reply = res.reply || "更新しました";
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: reply });
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "ADD_HISTORY", entry: { role: "assistant", content: reply } });
    } catch (e) {
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + (e instanceof Error ? e.message : "通信エラー") });
    }
  }, [state, dispatch]);

  // データ入力AI（売上・経費・勤怠・社員の統合ハンドラ）
  const askDataInputAI = useCallback(async (q: string) => {
    dispatch({ type: "ADD_HISTORY", entry: { role: "user", content: q } });
    dispatch({ type: "SET_TYPING", typing: true });
    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "" } });

    try {
      type DataInputAction = { type: string; data: Record<string, unknown> };
      const res = await apiPost<{ reply: string; actions: DataInputAction[]; input_complete: boolean }>("/api/chat/data-input", {
        message: q,
        history: state.history.slice(-8),
        industry: state.industry || "",
        company_name: state.companyName || "",
        current_clients: state.clients.map(c => ({ nm: c.nm, amt: c.amt, pj: c.pj, cst: c.cst, staff: c.staff })),
        current_staff: state.staff.map(s => ({ name: s.name, full: s.full, role: s.role, rate: s.rate })),
        fixed_costs: state.fixedCosts,
      });

      if (res.actions && res.actions.length > 0) {
        for (const action of res.actions) {
          if (action.type === "ADD_CLIENT" && action.data) {
            const d = action.data;
            dispatch({
              type: "ADD_CLIENT",
              client: {
                id: String(d.id || String.fromCharCode(65 + state.clients.length)),
                nm: String(d.nm || ""), fl: String(d.fl || d.nm || ""),
                pj: String(d.pj || ""), amt: Number(d.amt) || 0, cst: Number(d.cst) || 0,
                cm: Number(d.cm) ?? 0, im: Number(d.im) ?? 0, pm: Number(d.pm) ?? 1,
                ct: String(d.ct || ""),
                staff: Array.isArray(d.staff) ? d.staff as { name: string; hrs: number; rate: number }[] : [],
                progress: Number(d.progress) || 0,
                inv: Array.isArray(d.inv) ? d.inv as { item: string; qty: number; cost: number }[] : [],
              },
            });
          } else if (action.type === "ADD_STAFF" && action.data) {
            const d = action.data;
            dispatch({
              type: "ADD_STAFF",
              staff: {
                id: String(d.id || `S${String(state.staff.length + 1).padStart(3, "0")}`),
                name: String(d.name || ""), full: String(d.full || ""),
                role: String(d.role || ""), rate: Number(d.rate) || 0, salary: Number(d.salary) || 0,
              },
            });
          } else if (action.type === "UPDATE_FIXED_COSTS" && action.data) {
            const d = action.data;
            const cat = String(d.category || "other");
            const amtMan = Number(d.amount_man) || 0;
            const costs: Partial<FixedCostBreakdown> = {};
            const validKeys = ["personnel", "rent", "utilities", "communication", "lease", "insurance", "depreciation", "interest", "other"];
            if (validKeys.includes(cat)) {
              // 現在の値に加算（経費は累積）
              const currentVal = state.fixedCosts[cat as keyof FixedCostBreakdown] || 0;
              (costs as Record<string, number>)[cat] = currentVal + amtMan * 10000;
              dispatch({ type: "UPDATE_FIXED_COSTS", costs });
            }
          } else if (action.type === "LOG_WORK" && action.data) {
            const d = action.data;
            const staffName = String(d.staff_name || "");
            const clientNm = String(d.client_nm || "");
            const hours = Number(d.hours) || 0;
            if (staffName && clientNm && hours > 0) {
              const clientIdx = state.clients.findIndex(c => c.nm.includes(clientNm) || clientNm.includes(c.nm));
              if (clientIdx >= 0) {
                const client = state.clients[clientIdx];
                const existStaff = client.staff.find(s => s.name.includes(staffName) || staffName.includes(s.name));
                const staffRecord = state.staff.find(s => s.name.includes(staffName) || s.full.includes(staffName));
                const rate = staffRecord?.rate || existStaff?.rate || 2500;
                let newStaffList;
                if (existStaff) {
                  newStaffList = client.staff.map(s =>
                    s.name === existStaff.name ? { ...s, hrs: s.hrs + hours } : s
                  );
                } else {
                  newStaffList = [...client.staff, { name: staffName, hrs: hours, rate }];
                }
                dispatch({ type: "UPDATE_CLIENT", index: clientIdx, client: { staff: newStaffList } });
              }
            }
          }
        }
      }

      if (res.input_complete) {
        dispatch({ type: "SET_DATA_INPUT_DONE" });
      }

      const reply = res.reply || "データを登録しました。";
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: reply });
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "ADD_HISTORY", entry: { role: "assistant", content: reply } });
    } catch (e) {
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + (e instanceof Error ? e.message : "通信エラー") });
    }
  }, [state, dispatch]);

  // AI chat
  const askAI = useCallback(async (q: string) => {
    const { clients, staff, currentMonth: cm } = state;
    dispatch({ type: "ADD_HISTORY", entry: { role: "user", content: q } });
    dispatch({ type: "SET_TYPING", typing: true });

    const d = calc(clients, cm, state.ocrAmount);
    const gap = d.future.profit - d.cash.profit;
    const ach = Math.round((d.future.rev / TGT) * 100);

    const projInfo = clients
      .filter((c) => cm >= c.cm)
      .map((c) => {
        const lab = c.staff.reduce((s, sf) => s + sf.hrs * sf.rate, 0);
        const gr = c.amt - lab - c.cst;
        const st = gSt(c, cm);
        return `${c.nm}(${c.pj}/売上${fF(c.amt)}/粗利${fF(gr)}/${gSL(st)}/担当:${c.staff.map((s) => s.name + s.hrs + "h").join("+")})`;
      }).join(", ");

    const staffInfo = staff.map((s) => {
      let hrs = 0;
      const pjs: string[] = [];
      clients.forEach((c) => {
        if (cm < c.cm) return;
        c.staff.forEach((sf) => { if (sf.name === s.name) { hrs += sf.hrs; pjs.push(c.nm); } });
      });
      return hrs > 0 ? `${s.full}(${s.id}): ${hrs}h, ${pjs.join("/")}, 時給¥${s.rate}` : null;
    }).filter(Boolean).join("; ");

    const ctx = `\n[現在月:${MO[cm]} 未来利益:${fF(d.future.profit)} 今利益:${fF(d.now.profit)} CF利益:${fF(d.cash.profit)} 差額(運転資金):${fF(gap)} 契約${d.future.cnt}社 目標達成${ach}%]\n[案件: ${projInfo}]\n[社員: ${staffInfo}]\n[回答は短く具体的な数字で。箇条書きより文章で。来場者が感動する回答を]`;

    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "" } });
    let accumulated = "";
    try {
      await apiStreamChat("/api/chat",
        { message: q + ctx, history: state.history.slice(-8) },
        (text) => { accumulated += text; dispatch({ type: "UPDATE_LAST_MESSAGE", text: accumulated }); },
        (error) => { dispatch({ type: "SET_TYPING", typing: false }); dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + error }); },
        () => { dispatch({ type: "SET_TYPING", typing: false }); dispatch({ type: "ADD_HISTORY", entry: { role: "assistant", content: accumulated } }); },
      );
    } catch (e) {
      dispatch({ type: "SET_TYPING", typing: false });
      dispatch({ type: "UPDATE_LAST_MESSAGE", text: "⚠️ " + (e instanceof Error ? e.message : "通信エラー") });
    }
  }, [state, dispatch]);

  // ===== ルーティング判定ヘルパー =====

  // データ入力・経費・勤怠の記録メッセージか？
  const _isDataEntryMessage = useCallback((q: string): boolean => {
    // 金額を含む → ほぼ確実にデータ入力
    if (q.match(/\d+万/) || q.match(/\d+千/) || q.match(/\d+億/) || q.match(/\d{4,}円/)) return true;
    // 経費キーワード + 「払った」「支払」等
    const expenseWords = ["家賃", "賃料", "水道", "電気", "ガス", "光熱", "通信", "電話", "ネット", "AWS", "サーバー",
      "リース", "レンタル", "保険", "交通費", "タクシー", "新幹線", "飛行機", "出張", "接待", "交際",
      "広告", "宣伝", "消耗品", "文房具", "修繕", "研修", "会議", "手数料", "税金", "印紙", "顧問",
      "外注", "仕入", "材料", "食材", "給与", "給料", "賞与", "ボーナス", "役員報酬"];
    const payWords = ["払った", "払い", "支払", "かかった", "使った", "購入", "買った"];
    if (expenseWords.some(kw => q.includes(kw)) && payWords.some(kw => q.includes(kw))) return true;
    // 勤怠キーワード
    if (q.match(/\d+時間/) || q.match(/\d+h/i)) return true;
    if (q.includes("働いた") || q.includes("稼働") || q.includes("工数")) return true;
    // 売上・案件・社員の登録
    const dataWords = ["売上", "案件", "商品", "メニュー", "工事", "製品", "社員", "スタッフ", "カテゴリ", "原価率", "原価"];
    const actionWords = ["登録", "追加", "入力", "記録", "計上"];
    if (dataWords.some(kw => q.includes(kw)) && actionWords.some(kw => q.includes(kw))) return true;
    // 固定費の変更
    const fixedCostWords = ["家賃", "人件費", "光熱費", "通信費", "リース", "保険料", "減価償却", "支払利息"];
    if (fixedCostWords.some(kw => q.includes(kw)) && (q.includes("変更") || q.includes("設定") || q.includes("更新"))) return true;
    return false;
  }, []);

  // 分析・質問メッセージか？
  const _isAnalysisQuestion = useCallback((q: string): boolean => {
    const questionWords = ["儲", "利益", "いくら", "教えて", "分析", "状況", "どう", "3視点", "三視点"];
    const questionMarks = ["？", "?"];
    if (questionWords.some(kw => q.includes(kw))) return true;
    if (questionMarks.some(kw => q.includes(kw))) return true;
    return false;
  }, []);

  // Send handler
  const sendChat = useCallback(async () => {
    const q = input.trim();
    if (!q || state.typing) return;
    setInput("");

    if (sideTab === "rag") { doRagSearch(q); return; }

    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: q } });
    const cmdResult = detectCmd(q);
    if (cmdResult) {
      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: cmdResult } });
      return;
    }

    // データ入力 or 質問のルーティング
    // まずdata-input AIに送るべきかを判定
    const isDataEntry = _isDataEntryMessage(q);
    const isAnalysisQuestion = _isAnalysisQuestion(q);

    // データ未入力時
    if (state.clients.length === 0) {
      if (isAnalysisQuestion && !isDataEntry) {
        // データなしで質問 → 案内
        await askDataInputAI(q);
        return;
      }
      // それ以外は全てdata-input AIへ
      await askDataInputAI(q);
      return;
    }

    // データあり: data-input AIに送る条件
    if (isDataEntry) {
      await askDataInputAI(q);
      return;
    }

    // 分析質問はストリーミングAIへ（リッチな回答）
    await askAI(q);
  }, [input, state, sideTab, detectCmd, askAI, askFixedCostAI, askDataInputAI, _isDataEntryMessage, _isAnalysisQuestion, dispatch, doRagSearch]);

  const openRagResult = useCallback((r: RagResult) => {
    setSideTab("chat");
    dispatch({ type: "ADD_MESSAGE", message: { ai: false, text: `${r.title}について教えて` } });
    askAI(`「${r.title}」について教えて。データ: ${r.detail}`);
  }, [askAI, dispatch]);

  return (
    <aside className="w-80 bg-white border-l border-[#e5e7eb] flex flex-col shrink-0 h-screen">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#eee] flex items-center gap-3">
        <div className="w-12 h-12 rounded-[10px] bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] flex items-center justify-center text-[28px] relative overflow-hidden">
          ⚔️
        </div>
        <div>
          <div className="text-sm font-bold text-[#1a1a2e]">AI精算アシスタント</div>
          <div className="text-[10px] text-[#10b981] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] inline-block" />
            Claude AI 接続中
          </div>
        </div>
        <span className="ml-auto text-[#ccc] text-base cursor-pointer">›</span>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#eee]">
        <button
          onClick={() => setSideTab("chat")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition-all border-b-2 ${
            sideTab === "chat" ? "text-[#6366f1] border-[#6366f1] font-semibold" : "text-[#9ca3af] border-transparent"
          }`}
        >
          💬 チャット
        </button>
        <button
          onClick={() => setSideTab("rag")}
          className={`flex-1 py-2.5 text-center text-xs font-medium transition-all border-b-2 ${
            sideTab === "rag" ? "text-[#6366f1] border-[#6366f1] font-semibold" : "text-[#9ca3af] border-transparent"
          }`}
        >
          🔍 RAG検索
        </button>
      </div>

      {/* Messages / RAG */}
      {sideTab === "chat" ? (
        <div ref={msgsRef} className="flex-1 overflow-y-auto p-3.5 text-[#374151]">
          {state.messages.map((m, i) => {
            const isLastAi = m.ai && i === state.messages.length - 1;
            return (
              <div key={i} className={`mb-3.5 flex flex-col ${m.ai ? "items-start" : "items-end"}`}>
                <div className={`max-w-[90%] px-3.5 py-3 rounded-xl text-xs leading-relaxed whitespace-pre-line ${
                  m.ai ? "bg-[#f3f4f6] text-[#374151] rounded-bl-[4px]" : "bg-[#6366f1] text-white rounded-br-[4px]"
                }`}>
                  {m.ai && isLastAi ? <StreamingText text={m.text} isStreaming={state.typing} /> : m.text}
                </div>
                {m.actions && (
                  <div className="flex flex-col gap-1.5 mt-2 w-[90%]">
                    {m.actions.map((a, ai) => (
                      <button
                        key={ai}
                        onClick={() => a.href && router.push(a.href)}
                        className="flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] bg-white border border-[#e5e7eb] text-left text-xs text-[#374151] hover:border-[#6366f1] hover:bg-[#f5f3ff] transition-all"
                      >
                        <span className="text-lg">{a.icon}</span>
                        <div>
                          <div className="font-semibold text-[#1a1a2e]">{a.label}</div>
                          {a.desc && <div className="text-[10px] text-[#9ca3af]">{a.desc}</div>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {state.typing && (
            <div className="mb-3.5 flex flex-col items-start">
              <div className="dots"><span /><span /><span /></div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-3.5 text-[#374151]">
          <div className="text-[13px] font-semibold mb-3">📂 社内ドキュメント</div>
          {ragResults.length === 0 && !ragQuery ? (
            RAG.map((r) => (
              <div
                key={r.t}
                onClick={() => openRagResult({ id: r.t, category: r.tg, icon: "📄", color: r.c, title: r.t, detail: r.tx, searchText: "" })}
                className="p-3 border border-[#eee] rounded-lg mb-2 cursor-pointer hover:border-[#6366f1] hover:bg-[#f5f3ff] transition-all"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-semibold">{r.t}</span>
                  <span className="badge" style={{ background: r.c + "18", color: r.c }}>{r.tg}</span>
                </div>
                <div className="text-[11px] text-[#9ca3af]">{r.tx.substring(0, 50)}...</div>
              </div>
            ))
          ) : ragResults.length > 0 ? (
            ragResults.map((r) => (
              <div
                key={r.id}
                onClick={() => openRagResult(r)}
                className="p-3 border border-[#eee] rounded-lg mb-2 cursor-pointer hover:border-[#6366f1] hover:bg-[#f5f3ff] transition-all"
              >
                <span className="text-xs font-semibold">{r.title}</span>
                <div className="text-[11px] text-[#9ca3af]">{r.detail}</div>
              </div>
            ))
          ) : (
            <div className="text-center py-5 text-[#9ca3af] text-xs">「{ragQuery}」に一致なし</div>
          )}
        </div>
      )}

      {/* Input */}
      <div className="px-3.5 py-2.5 border-t border-[#eee] flex gap-2 items-end">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } }}
          rows={2}
          placeholder={sideTab === "chat" ? '例：「今月儲かってる？」「A社の案件は？」' : '社内文書を検索...'}
          className="flex-1 px-3 py-2.5 border border-[#e5e7eb] rounded-[10px] text-xs resize-none outline-none leading-normal text-[#374151] focus:border-[#6366f1]"
        />
        <button
          onClick={sendChat}
          className={`w-[34px] h-[34px] rounded-lg border-none text-white text-[15px] flex items-center justify-center ${
            input.trim() ? "bg-[#6366f1]" : "bg-[#e5e7eb]"
          }`}
        >
          ↑
        </button>
      </div>
    </aside>
  );
}
