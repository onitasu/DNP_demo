---
name: search-docs
description: Search latest official documentation for LLM APIs (Google Gemini). MUST be used before writing any LLM-related code.
argument-hint: [topic or API name]
allowed-tools: WebSearch, WebFetch, Read
---

# LLM 公式ドキュメント検索

LLM API に関するコードを書く前に、必ず最新の公式ドキュメントを確認する。

## 検索対象

引数 `$ARGUMENTS` に基づいて以下のソースを検索する：

### Google Gemini
- 公式ドキュメント: https://ai.google.dev/gemini-api/docs
- Python SDK (google-genai): https://github.com/googleapis/python-genai
- 構造化出力: https://ai.google.dev/gemini-api/docs/structured-output
- 画像認識: https://ai.google.dev/gemini-api/docs/image-understanding
- Thinking: https://ai.google.dev/gemini-api/docs/thinking

## 手順

1. `$ARGUMENTS` のトピックに関連するドキュメントを WebSearch で検索
2. 公式ドキュメントの URL を WebFetch で取得
3. 最新の API 仕様、モデル名、使用パターンをまとめて報告
4. 非推奨（deprecated）になった API や変更点があれば警告
5. ARCHITECTURE.md の技術メモと突合し、更新が必要な箇所を指摘
