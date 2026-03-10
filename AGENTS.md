# AI-OCR デモ — 発注書構造化データ抽出

Streamlit ベースの AI-OCR デモ。2段階パイプライン（OCR + セグメンテーション検証）で
発注書から構造化データを抽出し、原本画像上に信頼度色分けバウンディングボックスを表示。

設計書: DESIGN.md を参照。

## 技術スタック

- UI: Streamlit
- モデル: Pydantic v2
- LLM: google-genai（Step1: **gemini-2.5-pro**, Step2: **gemini-2.5-flash**）
- 画像処理: Pillow
- テスト: pytest
- リンター: ruff

## パイプライン

```
Step 1: OCR + 構造化抽出（gemini-2.5-pro, response_schema）→ PurchaseOrder
Step 2: セグメンテーション + 検証（gemini-2.5-flash, thinking_budget=0）→ FieldSegment[]
Step 3: バリデーション・補完（LLM不使用）→ 最終結果
```

## 開発ルール

- TDD 必須（Red → Green → Refactor）
- LLM APIやライブラリは公式ドキュメント確認後に実装
- ruff 準拠、型ヒント必須
- Conventional Commits

## コマンド

- 起動: `streamlit run app.py`
- テスト: `python -m pytest tests/ -v`
- リント: `ruff check . && ruff format --check .`
