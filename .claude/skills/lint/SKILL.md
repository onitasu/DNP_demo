---
name: lint
description: Run ruff linter and formatter check. Use before committing.
allowed-tools: Bash, Read
---

# リント・フォーマットチェック

## 手順

1. `cd /Users/tasukuonizawa/DNP_画像認識 && ruff check . --output-format=concise` を実行
2. `cd /Users/tasukuonizawa/DNP_画像認識 && ruff format --check .` を実行
3. エラーがあれば自動修正を提案（`ruff check --fix .` / `ruff format .`）
4. 結果サマリーを報告
