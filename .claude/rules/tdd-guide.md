---
paths:
  - "ocr/**/*.py"
  - "tests/**/*.py"
---

# TDD（テスト駆動開発）ガイド

## サイクル

```
🔴 RED    → 🟢 GREEN  → 🔵 REFACTOR
(テスト)    (実装)       (改善)
```

1. **RED**: 失敗するテストを `tests/` に書く → `python -m pytest tests/ -v` で失敗確認
2. **GREEN**: テストを通す最小限の実装 → テスト成功確認
3. **REFACTOR**: テスト通ったままコード改善

## ルール

- テストなしで実装を始めない
- テストを修正してコードに合わせない（コードをテストに合わせる）
- 複数機能を同時に開発しない

## テスト配置

```
tests/
├── conftest.py          # 共通 fixture
├── test_models.py       # models.py テスト（モック不要）
├── test_calculator.py   # calculator.py テスト（モック不要）
├── test_prompts.py      # prompts.py テスト（モック不要）
└── test_pipeline.py     # pipeline.py テスト（llm_client をモック）
```

## モック方針

| テスト対象 | モック | 理由 |
|-----------|--------|------|
| models.py | 不要 | 純粋な Pydantic モデル |
| calculator.py | 不要 | 純粋なビジネスロジック |
| prompts.py | 不要 | 純粋なテキスト生成 |
| pipeline.py | llm_client をモック | LLM API 呼び出しを回避 |
| llm_client.py | LLM SDK をモック | 外部 API 呼び出しを回避 |

## テスト実行

```bash
python -m pytest tests/ -v
```
