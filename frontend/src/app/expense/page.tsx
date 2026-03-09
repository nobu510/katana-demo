export default function ExpensePage() {
  return (
    <div className="animate-fade-up">
      <h2 className="text-lg font-bold mb-1">🤖 AI精算アシスタント</h2>
      <p className="text-xs text-gray-500 mb-6">
        経費精算・仕訳チェック・予実分析をAIがサポート
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {[
          { icon: "📷", label: "レシート読取" },
          { icon: "📈", label: "経費分析" },
          { icon: "💡", label: "節税提案" },
          { icon: "📋", label: "仕訳チェック" },
          { icon: "🧾", label: "領収書整理" },
          { icon: "📈", label: "予実対比" },
        ].map((item) => (
          <div
            key={item.label}
            className="bg-card rounded-xl border border-border p-4 text-center hover:border-primary transition-colors cursor-pointer"
          >
            <span className="text-2xl">{item.icon}</span>
            <p className="text-xs font-medium mt-2">{item.label}</p>
          </div>
        ))}
      </div>
      <div className="bg-card rounded-xl border border-border p-6 h-48 flex items-center justify-center text-gray-400 text-sm">
        経費データテーブル（実装予定）
      </div>
    </div>
  );
}
