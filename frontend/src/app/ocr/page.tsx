"use client";

import { useState, useRef } from "react";
import { useApp } from "@/lib/store";
import { RCP, fF } from "@/lib/data";
import { apiPost } from "@/lib/api";

type OcrResult = {
  store: string;
  date: string;
  items: { name: string; price: number }[];
  total: number;
  category: string;
};

export default function OcrPage() {
  const { dispatch } = useApp();
  const [status, setStatus] = useState<"idle" | "scanning" | "done" | "registered">("idle");
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [demoIdx, setDemoIdx] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const dataUrl = e.target?.result as string;
      setPreview(dataUrl);
      setStatus("scanning");
      setResult(null);
      try {
        const res = await apiPost<{ success: boolean; data?: OcrResult }>("/api/ocr", { image: dataUrl });
        if (res.success && res.data) {
          setResult(res.data);
          setStatus("done");
          dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: `📷 AI読取完了！ ${res.data.store} ¥${res.data.total.toLocaleString()}` } });
        } else {
          setStatus("idle");
        }
      } catch {
        setStatus("idle");
      }
    };
    reader.readAsDataURL(file);
  };

  const handleDemo = (idx: number) => {
    setDemoIdx(idx);
    setPreview(null);
    setStatus("scanning");
    setResult(null);
    setTimeout(() => {
      const rc = RCP[idx % RCP.length];
      setResult({
        store: rc.store,
        date: rc.date,
        items: rc.items.map(it => ({ name: it.n, price: it.p })),
        total: rc.total,
        category: rc.cat,
      });
      setStatus("done");
      dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: `📷 読取完了: ${rc.store}` } });
    }, 2000);
  };

  const registerExpense = () => {
    if (!result) return;
    dispatch({ type: "ADD_OCR_AMOUNT", amount: result.total });
    dispatch({ type: "ADD_MESSAGE", message: { ai: true, text: "✅ 登録完了！" } });
    setStatus("registered");
  };

  return (
    <div className="animate-fade-up">
      <div className="text-lg font-bold mb-4">レシートスキャン</div>

      <div className="card">
        <div className="text-sm font-bold mb-3.5">📷 AI OCRスキャン</div>

        {/* Upload zone */}
        <div
          onClick={() => fileRef.current?.click()}
          className="uz"
          style={{
            borderColor: status === "done" ? "#10b981" : status === "scanning" ? "#6366f1" : undefined,
          }}
        >
          {status === "idle" && (
            <>
              <div className="text-5xl mb-3">📁</div>
              <div className="text-sm font-semibold text-[#6366f1]">クリックしてレシート画像を選択</div>
              <div className="text-xs text-[#9ca3af] mt-2">JPG/PNG対応 · Claude Vision AIが自動解析</div>
            </>
          )}
          {status === "scanning" && (
            <>
              <div className="text-5xl mb-3 animate-pulse-custom">🔍</div>
              <div className="text-sm font-semibold text-[#6366f1]">Claude Vision AIが解析中...</div>
            </>
          )}
          {(status === "done" || status === "registered") && (
            <>
              <div className="text-5xl mb-3">✅</div>
              <div className="text-sm font-semibold text-[#059669]">{status === "registered" ? "登録済み" : "AI読取完了"}</div>
            </>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />

        {/* Preview */}
        {preview && (
          <div className="my-4">
            <img src={preview} className="max-w-full max-h-[250px] rounded-lg border-2 border-[#c7d2fe]" alt="receipt" />
          </div>
        )}

        {/* AI Result */}
        {status === "scanning" && !result && (
          <div className="text-center py-5 text-[#6366f1]">
            <div className="animate-pulse-custom text-[32px] mb-2">🤖</div>
            AIが解析中...
          </div>
        )}
        {result && status === "done" && (
          <div className="mt-4">
            <div className="text-[13px] font-semibold mb-2">🤖 AI読取結果</div>
            <div className="bg-white border border-[#eee] rounded-[10px] overflow-hidden">
              {[
                { l: "店舗名", v: result.store },
                { l: "日付", v: result.date },
                ...result.items.map(it => ({ l: it.name, v: `¥${it.price.toLocaleString()}` })),
                { l: "税込合計", v: `<b style="color:#6366f1;font-size:16px">¥${result.total.toLocaleString()}</b>` },
                { l: "勘定科目（AI）", v: `<span style="color:#7c3aed">${result.category}</span>` },
              ].map((row, i) => (
                <div key={i} className="flex justify-between px-4 py-3 border-b border-[#f3f4f6] text-[13px]">
                  <span className="text-[#6b7280]">{row.l}</span>
                  <span className="font-semibold" dangerouslySetInnerHTML={{ __html: row.v }} />
                </div>
              ))}
            </div>
            <div className="text-center">
              <button onClick={registerExpense} className="mt-4 px-5 py-2 rounded-lg bg-[#6366f1] text-white text-xs font-semibold hover:bg-[#4f46e5] transition-colors">
                ✅ 経費として登録
              </button>
            </div>
          </div>
        )}

        {/* Registered */}
        {status === "registered" && result && (
          <div className="mt-4">
            <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-lg p-4 text-center text-[#059669] font-semibold">
              ✅ ¥{result.total.toLocaleString()} を {result.category} として登録
            </div>
            <div className="text-center mt-4">
              <a href="/" className="px-5 py-2 rounded-lg bg-[#10b981] text-white text-xs font-semibold inline-block">
                📊 ダッシュボードで確認 →
              </a>
            </div>
          </div>
        )}
      </div>

      {/* Demo samples */}
      <div className="card">
        <div className="text-sm font-bold mb-3">💡 デモ用サンプル</div>
        <div className="text-xs text-[#6b7280] mb-3">お手元にレシートがない場合</div>
        <div className="flex gap-2 flex-wrap">
          {RCP.map((r, i) => (
            <button key={i} onClick={() => handleDemo(i)}
              className="px-4 py-2.5 rounded-lg border border-[#e5e7eb] bg-white text-xs text-[#374151] hover:border-[#6366f1] transition-colors">
              <b>{r.store}</b><br/>¥{r.total.toLocaleString()}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
