# AI-OCR デモ — 発注書構造化データ抽出

手書きを含む任意フォーマットの発注書から構造化データを自動抽出する Streamlit デモアプリ。
原本画像上にバウンディングボックスを描画し、信頼度に応じた色分けで確認箇所を視覚化する。

設計書: @DESIGN.md
要件定義: @REQUIREMENTS.md
API 技術メモ: @ARCHITECTURE.md

## ディレクトリ構造

```
├── app.py                  # Streamlit メインアプリ
├── ocr/
│   ├── models.py           # Pydantic ドメインモデル（PurchaseOrder, FieldSegment 等）
│   ├── pipeline.py         # 2段階パイプライン（OCR → セグメンテーション → 補完）
│   ├── llm_client.py       # Gemini API（構造化出力 + セグメンテーション）
│   ├── prompts.py          # プロンプトテンプレート（OCR用 + セグメンテーション用）
│   ├── calculator.py       # 金額補完・信頼度補正
│   └── visualizer.py       # バウンディングボックス描画・色分け（Pillow）
├── tests/
│   ├── test_models.py, test_calculator.py, test_prompts.py
│   ├── test_visualizer.py, test_pipeline.py
│   └── conftest.py
├── sample_data/            # デモ用発注書画像
├── requirements.txt
└── .env
```

## 技術スタック

| 技術 | 用途 |
|------|------|
| Streamlit | UI |
| Pydantic v2 | ドメインモデル |
| google-genai ≥1.66.0 | Gemini API |
| Pillow | バウンディングボックス描画 |
| pytest | テスト |
| ruff | リンター |

## LLM モデル

| 用途 | デフォルト | UI で切替可能 |
|------|-----------|--------------|
| Step 1: OCR + 構造化抽出 | **gemini-2.5-pro** | 2.5-pro / 2.5-flash / 3.x-preview |
| Step 2: セグメンテーション | **gemini-2.5-flash** | 2.5-flash / 2.5-pro / 3.x-preview |

- Gemini 3.x: mask 非対応だが box_2d は対応の可能性あり（公式コード例で使用）
- 3.x はプレビュー版（廃止リスクあり）だがデモ用途なら許容可能
- モデル間の精度比較データは未公開
- Google 公式推奨: 2.5-flash + thinking_budget=0
- **Streamlit サイドバーでモデルを切り替え可能にして検証する**

## google-genai SDK

```python
from google import genai          # ← google-genai パッケージ
from google.genai import types    # ← 旧 google-generativeai は使わない

client = genai.Client(api_key=...)
```

## 2段階パイプライン

```
Step 1: OCR + 構造化抽出（gemini-2.5-pro）
  ・画像 → Gemini（response_json_schema）→ Pydantic で再検証
  ・構造化出力で安定したフィールド抽出

Step 2: セグメンテーション + 検証（gemini-2.5-flash, thinking_budget=0）
  ・画像 + Step1結果 → Gemini → FieldSegment[]
  ・各フィールドの box_2d 座標 + OCR結果の再検証
  ・不一致があれば信頼度を引き下げ

Step 3: バリデーション・補完（LLM不使用）
  ・金額整合性チェック + 欠損値補完 + 信頼度最終調整
```

## モジュール依存ルール

- `models.py`, `prompts.py` → 外部依存なし（pydantic / 純粋テキスト）
- `calculator.py` → models のみ
- `visualizer.py` → Pillow + models のみ
- `llm_client.py` → google-genai + models + prompts
- `pipeline.py` → 上記すべて
- `app.py` → pipeline + models + visualizer

## 開発ルール

### TDD サイクル（必須）

```
🔴 RED → 🟢 GREEN → 🔵 REFACTOR
```

### LLM API 利用時（必須）

**LLM SDK やライブラリを使うコードを書く前に、必ず `/search-docs` で最新ドキュメントを確認する。**

### Gemini セグメンテーション仕様

- `box_2d`: `[y_min, x_min, y_max, x_max]` 0-1000 正規化座標
- ピクセル変換: `pixel = (normalized / 1000) * image_dimension`
- **`response_json_schema` で box_2d + カスタムフィールドを直接取得**
- mask は使わない（構造化出力との相性問題: GitHub #1378）
- **`thinking_budget=0` は gemini-2.5-flash のみ使用可能（pro は最小128）**

### Pydantic スキーマの注意点

- `Optional[str] = None` は OK
- `dict[str, ...]` を含むモデルは Gemini Developer API では `response_json_schema` を使う
- `str = "default"` のような非 None デフォルト値は schema 整形時に落とす

### コーディング規約

- ruff 準拠。型ヒント必須
- Conventional Commits
- コミット前に `/git-commit`

## コマンド

```bash
streamlit run app.py          # 起動
python -m pytest tests/ -v    # テスト
ruff check . && ruff format --check .  # リント
```

## 環境変数

`.env` に配置:
```
GEMINI_API_KEY=<your-key>
```

## スキル一覧

| スキル | 用途 |
|-------|------|
| `/run-tests` | pytest 実行・結果分析 |
| `/lint` | ruff lint・format チェック |
| `/search-docs` | LLM API 公式ドキュメント検索（実装前に必須） |
| `/git-commit` | 品質チェック後に git commit |

## エージェント一覧

| エージェント | 役割 | モデル |
|------------|------|--------|
| **doc-researcher** | LLM API ドキュメント調査 | sonnet |
| **test-writer** | 🔴 RED: テスト作成専門 | opus |
| **test-runner** | テスト実行・結果分析 | haiku |
