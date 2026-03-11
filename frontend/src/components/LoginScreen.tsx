"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";

export default function LoginScreen() {
  const { state, dispatch } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // 仮ログイン: 何を入力してもログイン可能
    await new Promise((resolve) => setTimeout(resolve, 500));

    dispatch({ type: "LOGIN", email: email || "demo@katana.ai" });

    if (state.companyRegistered) {
      // 登録済みユーザー: 通常のウェルカムメッセージ
      dispatch({
        type: "ADD_MESSAGE",
        message: {
          ai: true,
          text: `ようこそ、KATANA AIへ。\n経営データの確認、経費精算、AIへの質問など何でもお気軽にどうぞ。`,
          actions: [
            { icon: "📊", label: "ダッシュボードを見る", desc: "3視点の経営状況", href: "/" },
            { icon: "📷", label: "レシートスキャン", desc: "AI OCR自動読取", href: "/ocr" },
            { icon: "📝", label: "見積書を作成", desc: "手動 or AI生成", href: "/quote" },
          ],
        },
      });
    } else {
      // 新規ユーザー: オンボーディングメッセージ
      dispatch({
        type: "ADD_MESSAGE",
        message: {
          ai: true,
          text: `こんにちは！KATANA AIです。御社の経営を一刀両断します。\nまず、どんなお仕事をされていますか？`,
        },
      });
    }

    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-[#0a0a14] flex items-center justify-center">
      {/* Background */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 30% 20%, rgba(99,102,241,0.15) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(124,58,237,0.1) 0%, transparent 50%), #0a0a14",
        }}
      />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[400px] mx-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[#6366f1] to-[#7c3aed] mb-4 shadow-[0_4px_24px_rgba(99,102,241,0.4)]">
            <svg viewBox="0 0 24 24" fill="none" width="32" height="32">
              <path
                d="M8 4c0 0 2 1 4 1s4-1 4-1v3c0 1-1.5 2-4 2s-4-1-4-2V4z"
                fill="#fff"
              />
              <rect x="11" y="9" width="2" height="11" rx="1" fill="#fff" />
              <path
                d="M8 20h8"
                stroke="#fff"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-white tracking-wider">
            KATANA
          </h1>
          <p className="text-sm text-[#9ca3af] mt-1">
            エージェントAI総合業務管理
          </p>
        </div>

        {/* Form card */}
        <div className="bg-[#1a1a2e]/80 backdrop-blur-sm border border-white/10 rounded-2xl p-8">
          <h2 className="text-lg font-bold text-white mb-6">
            {mode === "login" ? "ログイン" : "新規登録"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#9ca3af] mb-1.5">
                メールアドレス
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full px-4 py-3 rounded-xl bg-[#0a0a14] border border-white/10 text-white text-sm placeholder-[#555] outline-none focus:border-[#6366f1] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#9ca3af] mb-1.5">
                パスワード
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-[#0a0a14] border border-white/10 text-white text-sm placeholder-[#555] outline-none focus:border-[#6366f1] transition-colors"
              />
            </div>

            {error && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#7c3aed] text-white font-semibold text-sm shadow-[0_4px_16px_rgba(99,102,241,0.4)] hover:shadow-[0_6px_24px_rgba(99,102,241,0.5)] hover:translate-y-[-1px] transition-all disabled:opacity-50 disabled:hover:translate-y-0"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {mode === "login" ? "ログイン中..." : "登録中..."}
                </span>
              ) : mode === "login" ? (
                "ログイン"
              ) : (
                "アカウント作成"
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[11px] text-[#555]">または</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          {/* Toggle login/register */}
          <div className="text-center">
            {mode === "login" ? (
              <p className="text-xs text-[#9ca3af]">
                アカウントをお持ちでない方は{" "}
                <button
                  onClick={() => {
                    setMode("register");
                    setError("");
                  }}
                  className="text-[#6366f1] font-semibold hover:underline"
                >
                  新規登録
                </button>
              </p>
            ) : (
              <p className="text-xs text-[#9ca3af]">
                既にアカウントをお持ちの方は{" "}
                <button
                  onClick={() => {
                    setMode("login");
                    setError("");
                  }}
                  className="text-[#6366f1] font-semibold hover:underline"
                >
                  ログイン
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] text-[#555] mt-6">
          &copy; 2026 J.NOVA Inc. All rights reserved.
        </p>
      </div>
    </div>
  );
}
