---
paths:
  - "ocr/**/*.py"
  - "app.py"
---

# モジュール依存ルール

## 依存関係図

```
app.py
  ├→ ocr/pipeline.py
  │    ├→ ocr/llm_client.py
  │    │    ├→ ocr/models.py
  │    │    └→ ocr/prompts.py
  │    ├→ ocr/calculator.py
  │    │    └→ ocr/models.py
  │    └→ ocr/models.py
  └→ ocr/visualizer.py
       └→ ocr/models.py
```

## 各モジュールの import 制約

### ocr/models.py（ドメインモデル）
- **許可**: 標準ライブラリ, pydantic
- **禁止**: streamlit, google.genai, PIL, ocr 内の他モジュール

### ocr/prompts.py（プロンプトテンプレート）
- **許可**: 標準ライブラリのみ
- **禁止**: すべての外部ライブラリ, ocr 内の他モジュール

### ocr/calculator.py（ビジネスロジック）
- **許可**: 標準ライブラリ, pydantic, ocr.models
- **禁止**: streamlit, google.genai, PIL

### ocr/visualizer.py（画像描画）
- **許可**: 標準ライブラリ, PIL/Pillow, ocr.models
- **禁止**: streamlit, google.genai

### ocr/llm_client.py（LLM クライアント）
- **許可**: 標準ライブラリ, google.genai, ocr.models, ocr.prompts
- **禁止**: streamlit, PIL

### ocr/pipeline.py（オーケストレーション）
- **許可**: 標準ライブラリ, ocr 内の全モジュール
- **禁止**: streamlit

### app.py（UI）
- **許可**: streamlit, ocr.pipeline, ocr.models, ocr.visualizer
- **禁止**: ocr.llm_client の直接呼び出し（pipeline 経由）

## 原則

- `models.py` と `prompts.py` は外部依存ゼロ
- `calculator.py` と `visualizer.py` は LLM に依存しない
- `llm_client.py` だけが Gemini SDK に依存する
- `app.py` は Streamlit UI のみ。ビジネスロジック禁止
