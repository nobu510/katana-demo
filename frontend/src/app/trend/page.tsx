export default function TrendPage() {
  return (
    <div className="animate-fade-up">
      <h2 className="text-lg font-bold mb-1">📈 AIトレンド検索</h2>
      <p className="text-xs text-gray-500 mb-6">
        AI・DX、会計・経営、補助金・制度のトレンド分析
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { title: "🤖 AI・DX", count: 4 },
          { title: "📊 会計・経営", count: 3 },
          { title: "💰 補助金・制度", count: 3 },
        ].map((cat) => (
          <div
            key={cat.title}
            className="bg-card rounded-xl border border-border p-5"
          >
            <h3 className="text-sm font-bold mb-3">{cat.title}</h3>
            <p className="text-xs text-gray-400">
              {cat.count}件のトレンド（実装予定）
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
