export default function OcrPage() {
  return (
    <div className="animate-fade-up">
      <h2 className="text-lg font-bold mb-1">📷 レシートスキャン</h2>
      <p className="text-xs text-gray-500 mb-6">
        Claude Vision AI でレシートを自動読み取り
      </p>
      <div className="bg-card rounded-xl border border-border p-6 h-64 flex items-center justify-center text-gray-400 text-sm">
        ドラッグ&ドロップ / ファイル選択（実装予定）
      </div>
    </div>
  );
}
