---
name: lint
description: Run ruff linter and formatter check. Use before committing.
---

# リント・フォーマットチェック

1. `ruff check . --output-format=concise` を実行
2. `ruff format --check .` を実行
3. エラーがあれば自動修正を提案
4. 結果サマリーを報告
