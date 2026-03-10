---
name: git-commit
description: コード品質チェック（formatter/linter/test）後に git commit する
---

# git-commit

1. `git status` で変更確認
2. `ruff format . && ruff check --fix . && python -m pytest tests/ -v`
3. すべて成功したら `git add -A && git commit`
4. Conventional Commits 形式でメッセージ作成
