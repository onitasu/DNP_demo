---
name: git-commit
description: コード品質チェック（formatter/linter/test）を実行してから git commit する
disable-model-invocation: true
allowed-tools: Bash, Read
---

# git-commit: 品質チェック & Commit

## Procedure

### Step 1: 変更内容確認

```bash
git status
git diff --stat
```

### Step 2: 品質チェック

```bash
# Formatter（自動修正）
ruff format ocr tests app.py

# Linter（自動修正）
ruff check --fix ocr tests app.py

# テスト
python -m pytest tests/ -v
```

エラーがあれば修正してから次へ。

### Step 3: Git commit

```bash
git add -A
git commit -m "{type}: {description}

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

type: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`

### Step 4: 完了

チェック結果とコミットハッシュを報告。

## Constraints

- チェック失敗時は commit しない
- 変更なしの場合はその旨を伝え終了
