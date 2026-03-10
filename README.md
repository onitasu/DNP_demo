# AI-OCR デモ

`ocr_experiment.ipynb` を FastAPI + Next.js で動かす簡易デモ。画像/PDFをアップロードし、Gemini または OpenAI で構造化OCRを実行して結果を表示します。

## 構成
- backend: FastAPI (構造化出力 + 2ステップOCR + 金額補完)
- frontend: Next.js (app router) でアップロード & 結果表示

## セットアップ
### バックエンド
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # GEMINI_API_KEY / OPENAI_API_KEY を設定
uvicorn app.main:app --reload --port 8000
```

### フロントエンド
```bash
cd frontend
npm install
# バックエンドが http://localhost:8000 以外なら環境変数で指定
# export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

## 使い方
1. フロントでファイルを選択
2. プロバイダ (Gemini/OpenAI) とモデルを選択
3. 「アップロードして解析」を押すと `/api/ocr` に送信し、構造化結果と生JSONを表示

### API 手動確認
```bash
curl -X POST \
  -F "file=@/path/to/receipt.jpg" \
  -F "provider=google" \
  http://localhost:8000/api/ocr
```

## 補足
- 対応MIME: JPG/PNG/GIF/BMP/WebP/PDF（10MBまで）
- `calculate_missing=true` で消費税・税抜金額を自動計算
- CORSはローカルデモ用にオープン設定
