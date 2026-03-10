# AI-OCR デモアプリケーション 設計書

## 1. プロジェクト背景と目的

### 背景

DNP モビリティ&リビング事業部では輸出業務において以下の課題を抱えている：

- 入力項目が多く作業負荷が高い
- 顧客から送られてくる発注書にテンプレートがなく、形式がバラバラ
- 手書きで送られてくるものもあり、一つ一つExcelに手入力している
- 過去にOCRを検討したが、読み取り結果の目視確認業務が発生し、見落としリスクを懸念して見送った経緯がある

### 目的

**手書きを含む任意フォーマットの発注書から、構造化データを自動抽出するAI-OCRデモ**を構築し、以下を実証する：

1. フォーマットが統一されていない発注書でも高精度に情報抽出が可能であること
2. 手書き文字の認識が実用レベルで機能すること
3. 抽出結果に対する信頼度スコアを付与し、目視確認の優先度を自動判定できること
4. **原本画像上にバウンディングボックスを描画し、信頼度に応じた色分けで「どこを確認すべきか」を視覚的に示すこと**

---

## 2. アーキテクチャ方針

### なぜ Streamlit か

- **デモ用途**に特化。`streamlit run app.py` 一発で起動
- Python 単一言語で完結。LLM SDK（google-genai）をそのまま利用
- 本番化時は FastAPI + Next.js 構成に発展させる前提

### LLM モデル

| 用途 | デフォルト | 選択肢 | 備考 |
|------|-----------|--------|------|
| Step 1: OCR + 構造化抽出 | `gemini-2.5-pro` | 2.5-pro / 2.5-flash / 3.x-preview | pro は最高精度の安定版 |
| Step 2: セグメンテーション | `gemini-2.5-flash` | 2.5-flash / 2.5-pro / 3.x-preview | Google 公式推奨は flash + thinking_budget=0 |

**Streamlit サイドバーでモデルを切り替え可能にする（検証用）。**

> **Gemini 3.x の制約**: mask（ピクセルレベル）は非対応。box_2d は公式コード例で
> `gemini-3-flash-preview` が使われており対応している可能性あり。
> プレビュー版は廃止リスクあるが、デモ用途なら許容可能。
>
> **モデル間の精度比較データは未公開。**
> UI 上で切り替えて実際の発注書で検証する。

### システム構成

```
┌──────────────────────────────────────────────────────┐
│  Streamlit App (app.py)                              │
│                                                       │
│  ┌──────────────┐  ┌─────────────────────────────┐  │
│  │ Upload &     │  │ Results                      │  │
│  │ Annotated    │  │ ・構造化データ表（信頼度色付き）│  │
│  │ Preview      │  │ ・要確認サマリー              │  │
│  │ (左カラム)    │  │ ・全文テキスト / Raw JSON     │  │
│  └──────┬───────┘  └───────────▲──────────────────┘  │
│         │                      │                     │
│  ┌──────▼──────────────────────┴──────────────────┐  │
│  │  OCR Pipeline (ocr/)                           │  │
│  │                                                │  │
│  │  Step 1: OCR + 構造化抽出                       │  │
│  │    → PurchaseOrder + confidence_scores          │  │
│  │                                                │  │
│  │  Step 2: セグメンテーション + 検証               │  │
│  │    → box_2d 座標 + 検証結果                     │  │
│  │                                                │  │
│  │  Step 3: バリデーション・補完                    │  │
│  │    → 金額整合性チェック + 信頼度最終調整          │  │
│  └──────────────────┬─────────────────────────────┘  │
└─────────────────────│─────────────────────────────────┘
                      │ API 呼び出し
                      ▼
           ┌──────────────────────┐
           │  Google Gemini API   │
           │  gemini-2.5-pro/flash│
           └──────────────────────┘
```

---

## 3. ディレクトリ構造

```
├── app.py                  # Streamlit メインアプリ（UI + オーケストレーション呼び出し）
├── ocr/                    # OCR パイプラインモジュール
│   ├── __init__.py
│   ├── models.py           # Pydantic ドメインモデル（PurchaseOrder, SegmentationResult 等）
│   ├── pipeline.py         # パイプラインオーケストレーション（Step1→2→3）
│   ├── llm_client.py       # LLM クライアント（Gemini 構造化出力 + セグメンテーション）
│   ├── prompts.py          # プロンプトテンプレート（OCR用 + セグメンテーション用）
│   ├── calculator.py       # 金額補完・信頼度補正ロジック
│   └── visualizer.py       # 画像へのバウンディングボックス描画・色分け
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_calculator.py
│   ├── test_prompts.py
│   ├── test_visualizer.py
│   └── test_pipeline.py
├── sample_data/            # デモ用テストデータ
│   ├── printed_order.png
│   ├── handwritten_order.png
│   └── varied_format_order.png
├── requirements.txt
└── .env
```

### モジュール責務

| モジュール | 責務 | 依存先 |
|-----------|------|--------|
| `app.py` | Streamlit UI・パイプライン呼び出し・結果表示 | ocr/pipeline, ocr/models, ocr/visualizer |
| `ocr/models.py` | ドメインモデル定義 | pydantic のみ |
| `ocr/pipeline.py` | Step1→2→3 のオーケストレーション | models, llm_client, calculator |
| `ocr/llm_client.py` | Gemini API 呼び出し（構造化出力 + セグメンテーション） | google-genai, models, prompts |
| `ocr/prompts.py` | プロンプトテンプレート管理 | なし |
| `ocr/calculator.py` | 金額補完・信頼度補正 | models のみ |
| `ocr/visualizer.py` | 画像にバウンディングボックス描画・信頼度色分け | PIL/Pillow, models |

---

## 4. データモデル

### PurchaseOrder（発注書）

```
PurchaseOrder
├── order_number        — 発注番号
├── order_date          — 発注日（YYYY-MM-DD）
├── delivery_date       — 納期（YYYY-MM-DD）
├── orderer             — 発注元情報
│   ├── company_name    — 会社名
│   ├── department      — 部署名
│   ├── contact_person  — 担当者名
│   ├── address         — 住所
│   ├── phone           — 電話番号
│   ├── fax             — FAX番号
│   └── email           — メールアドレス
├── items[]             — 品目明細（複数）
│   ├── item_number     — 品番/商品コード
│   ├── description     — 品名/商品説明
│   ├── quantity        — 数量
│   ├── unit            — 単位
│   ├── unit_price      — 単価
│   └── amount          — 金額
├── subtotal            — 小計
├── tax_amount          — 消費税額
├── total_amount        — 合計金額
├── payment_terms       — 支払条件
├── delivery_address    — 納品先住所
├── notes               — 備考
└── confidence_scores   — 各フィールドの信頼度マップ（high/medium/low）
```

### FieldSegment（セグメンテーション結果）

```
FieldSegment
├── field_name          — 対応するフィールド名（例: "order_number", "orderer.company_name"）
├── box_2d              — バウンディングボックス [y0, x0, y1, x1]（0-1000 正規化座標）
├── ocr_text            — セグメンテーション時に再読取したテキスト
├── verified            — Step 1 の値と画像上のテキストが一致するか（true/false）
└── confidence          — 信頼度（high/medium/low）
```

> mask は含めない。構造化出力と mask（巨大 base64）の併用は不安定（GitHub #1378）。
> 本プロジェクトは box_2d のみで十分。

### 信頼度と色分け

| 信頼度 | 意味 | ボックス色 | UI表現 |
|--------|------|-----------|--------|
| high | 高確信。検証でも一致 | 🔵 青 | そのまま。確認不要 |
| medium | 抽出できたが曖昧 | 🟡 黄 | 確認推奨 |
| low | 判読困難・検証で不一致 | 🔴 赤 | 要確認。太字ハイライト |

---

## 5. 処理フロー（2段階パイプライン）

```
ユーザーが発注書画像をアップロード（Streamlit file_uploader）
    │
    ▼
app.py: バリデーション（ファイルサイズ ≤ 20MB、画像 or PDF）
    │
    ▼
━━━ Step 1: OCR + 構造化抽出 ━━━━━━━━━━━━━━━━━━━━━━━━
    │
    │  モデル: gemini-2.5-pro
    │  入力: 発注書画像
    │  方式: response_json_schema で Pydantic モデルに沿った構造化出力
    │  プロンプト:
    │    「発注書画像から全フィールドを抽出し、各項目の信頼度を判定せよ」
    │  出力: PurchaseOrder + confidence_scores
    │
    ▼
━━━ Step 2: セグメンテーション + 検証 ━━━━━━━━━━━━━━━━
    │
    │  モデル: gemini-2.5-flash（thinking_budget=0 で精度向上）
    │  入力: 発注書画像 + Step 1 の OCR 結果
    │  方式: セグメンテーション用プロンプト（box_2d 形式で出力指示）
    │  プロンプト:
    │    「以下の OCR 結果の各フィールドについて、画像上の対応領域を
    │     バウンディングボックスで示せ。また、OCR 結果と画像上のテキスト
    │     が一致するか検証せよ」
    │  出力: FieldSegment[] (field_name, box_2d, verified, confidence)
    │
    │  ※ Step 1 で high だったが Step 2 で不一致 → confidence を low に引き下げ
    │  ※ Step 1 で medium だったが Step 2 で一致確認 → confidence を high に引き上げ
    │
    ▼
━━━ Step 3: バリデーション・補完 ━━━━━━━━━━━━━━━━━━━━
    │
    │  処理: calculator.py（LLM 不使用、純粋ロジック）
    │  ・金額整合性チェック（単価×数量＝金額、小計＋税＝合計）
    │  ・欠損値の算術的補完
    │  ・金額不整合 → 関連フィールドの信頼度を low に
    │
    ▼
━━━ 表示 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    │  visualizer.py:
    │  ・原本画像にバウンディングボックスを描画
    │  ・信頼度に応じた色分け（青=確認不要、黄=推奨、赤=要確認）
    │  ・ボックス横にフィールド名ラベル
    │
    │  app.py:
    │  ・左カラム: アノテーション付き原本画像
    │  ・右カラム: 構造化データ表（信頼度バッジ付き）
    │  ・ヘッダー: 「要確認項目: N件」サマリー
    │  ・タブ: 全文テキスト / Raw JSON
    │
    ▼
ユーザーが赤枠の箇所だけ原本と照合して確認
```

### なぜ 2段階か

| 観点 | 1段階（OCR+セグメンテーション同時） | 2段階（推奨） |
|------|----------------------------------|--------------|
| 出力安定性 | 1回の応答で複数形式が混在し不安定 | 各ステップが専用フォーマットで安定 |
| 検証機能 | なし | Step 2 で OCR 結果を画像と照合し再検証 |
| 信頼度精度 | LLM の自己申告のみ | LLM の2回の判断 + 算術チェックの3重検証 |
| デモの訴求 | 「1回で抽出」 | **「AIが2段階で検証している」＝過去のOCR問題への直接的な回答** |

---

## 6. 技術スタック

| カテゴリ | 技術 |
|----------|------|
| UI | Streamlit |
| データモデル | Pydantic v2 |
| LLM | google-genai（gemini-2.5-pro） |
| 画像処理 | Pillow（バウンディングボックス描画） |
| テスト | pytest |
| リンター | ruff |
| 環境変数 | python-dotenv |

---

## 7. Gemini API 仕様メモ

### SDK 情報（google-genai v1.66.0）

```python
from google import genai          # ← google-genai パッケージ
from google.genai import types    # ← 旧 google-generativeai は使わない
```

### Step 1: 構造化出力（OCR + 抽出）

```python
client = genai.Client(api_key=...)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[image, prompt_text],  # テキストは画像の後に置く
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=PurchaseOrder.model_json_schema(),
    ),
)
result = PurchaseOrder.model_validate_json(response.text)
```

### Step 2: セグメンテーション + 検証

```python
# FieldSegment に box_2d + カスタムフィールドを含めて response_json_schema で渡す
# mask は含めない（構造化出力との相性問題あり: GitHub #1378）
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=TypeAdapter(list[FieldSegment]).json_schema(),
    thinking_config=types.ThinkingConfig(thinking_budget=0),  # flash のみ有効
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[image, segmentation_prompt],
    config=config,
)
segments = TypeAdapter(list[FieldSegment]).validate_json(response.text)
```

### 出力形式

```json
[
  {
    "field_name": "order_number",
    "box_2d": [y0, x0, y1, x1],
    "ocr_text": "0101001865",
    "verified": true,
    "confidence": "high"
  }
]
```

- `box_2d`: 0-1000 正規化座標。ピクセル変換: `pixel = (normalized / 1000) * image_dimension`

### thinking_config 制約

| モデル | thinking_budget=0 | 有効範囲 |
|--------|-------------------|----------|
| `gemini-2.5-pro` | **使用不可** | 128〜32,768 |
| `gemini-2.5-flash` | 使用可能 | 0〜24,576 |

### Pydantic スキーマの注意点

- `Optional[str] = None` は OK
- `dict[str, ...]` は Gemini Developer API の `response_schema` では不可。`response_json_schema` を使う
- `str = "default"` のような非 None デフォルト値は `response_json_schema` に渡す前に落とすと安全

---

## 8. テスト戦略

### TDD サイクル

```
🔴 RED → 🟢 GREEN → 🔵 REFACTOR
```

### テスト対象

| テストファイル | 対象 | モック |
|--------------|------|--------|
| `test_models.py` | Pydantic モデルバリデーション | なし |
| `test_calculator.py` | 金額補完・信頼度補正 | なし |
| `test_prompts.py` | プロンプト生成 | なし |
| `test_visualizer.py` | バウンディングボックス描画・座標変換 | なし |
| `test_pipeline.py` | パイプラインオーケストレーション | llm_client をモック |

---

## 9. UI 設計

```
┌──────────────────────────────────────────────────────┐
│  🔍 AI-OCR Demo — 発注書読み取り                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  📊 要確認: 3件（🔴赤枠）/ 確認推奨: 2件（🟡黄枠）    │
├──────────────────────┬───────────────────────────────┤
│                      │                               │
│  📄 原本 + 検出結果   │  📋 抽出データ                 │
│  ┌────────────────┐  │                               │
│  │ ╔══ 🔵 ══╗     │  │  ▸ 発注元情報                  │
│  │ ║ PO-001  ║    │  │    会社名    ○○株式会社  🔵  │
│  │ ╚═════════╝    │  │    担当者    山田太郎    🟡  │
│  │ ┌── 🟡 ──┐     │  │    住所      東京都...   🔵  │
│  │ │ 山田太郎│     │  │                               │
│  │ └────────┘     │  │  ▸ 品目明細                    │
│  │ ╔══ 🔴 ══╗     │  │    品番  品名  数量  単価  金額│
│  │ ║ ???    ║     │  │    A-01  製品A  100  500  🔵 │
│  │ ╚═════════╝    │  │    B-02  製品B  ??   300  🔴 │
│  │                │  │                               │
│  └────────────────┘  │  ▸ 金額情報                    │
│                      │    小計     150,000      🔵  │
│  ⚙️ 設定             │    消費税    15,000      🔵  │
│  Step1: [gemini-2.5- │    合計     165,000      🔵  │
│    pro ▼]            │                               │
│  Step2: [gemini-2.5- │                               │
│    flash ▼]          │                               │
│  ☑ 金額自動補完      │                               │
│                      │  ▸ 全文テキスト                │
│  [🚀 解析開始]       │  ▸ Raw JSON                   │
│                      │  処理時間: 4.5秒              │
└──────────────────────┴───────────────────────────────┘
```

### ポイント

- **左カラム**: 原本画像に**バウンディングボックスをオーバーレイ描画**。青=OK、黄=推奨、赤=要確認
- **右カラム**: 構造化データ表。各行に信頼度バッジ。赤の行はハイライト
- **ヘッダー**: 要確認件数をサマリー表示。一目で「何件確認すればいいか」がわかる
- **連動**: 右カラムの赤項目が、左カラムの赤枠と対応していることが視覚的にわかる

---

## 10. デモシナリオ

### テストデータ（3パターン）

1. **印刷された標準的な発注書** — ほぼ全項目が青枠。「自動処理可能」をアピール
2. **手書きの発注書** — 一部黄・赤枠。「手書きでもここまで読める」をアピール
3. **フォーマットが異なる発注書** — テンプレートなしでも対応可能なことを示す

### デモストーリー

1. 「現状は手入力ですよね」→ 手書き発注書をアップロード
2. 数秒で画像にバウンディングボックスが表示される
3. **「青枠は確認不要。赤枠の3箇所だけ確認してください」** と説明
4. 右カラムの構造化データと左カラムの赤枠を照合するだけで確認完了
5. **「全件目視確認ではなく、AIが不確かな箇所だけ。確認工数は1/10になります」**
6. 異なるフォーマットでも同様に動作することを示す
7. 「本番化の際は Excel 連携・バッチ処理を実装します」

---

## 11. 本番化への発展

```
デモ（Streamlit + gemini-2.5-pro）
    ↓ 要件確定
本番（FastAPI + Next.js / Vercel）
    ├─ REST API 化（FastAPI）
    ├─ 認証・権限管理
    ├─ Excel / 業務システム連携
    ├─ バッチ処理（複数ファイル一括）
    ├─ 確認結果のフィードバックループ（精度向上）
    └─ 監査ログ・エラー通知
```
