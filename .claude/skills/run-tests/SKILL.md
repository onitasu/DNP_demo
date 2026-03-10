---
name: run-tests
description: Run pytest and report results. Use after implementing or modifying code.
allowed-tools: Bash, Read
---

# テスト実行

## 手順

1. `cd /Users/tasukuonizawa/DNP_画像認識 && python -m pytest tests/ -v --tb=short` を実行
2. 失敗したテストがあれば、該当テストファイルと実装ファイルを読んで原因を分析
3. 結果サマリーを報告（通過数、失敗数、失敗の原因）
