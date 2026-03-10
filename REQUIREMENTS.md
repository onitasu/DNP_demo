# 要件定義書 — AI-OCR 発注書構造化データ抽出

> 背景・目的は DESIGN.md を参照。本ドキュメントは実装に必要なロジックの詳細を定義する。

---

## 1. データモデル詳細

### 1.1 ConfidenceLevel（信頼度）

3段階の列挙型。すべてのフィールドに付与される。

| 値 | 意味 | UI 色 |
|----|------|-------|
| `high` | 高確信。Step 2 検証でも一致 | 青 `#2196F3` |
| `medium` | 抽出できたが曖昧。手書きの判読難 等 | 黄 `#FFC107` |
| `low` | 判読困難、検証で不一致、金額不整合 | 赤 `#F44336` |

型: `Literal["high", "medium", "low"]`

### 1.2 Orderer（発注元情報）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| company_name | `Optional[str]` | No | 会社名 |
| department | `Optional[str]` | No | 部署名 |
| contact_person | `Optional[str]` | No | 担当者名 |
| address | `Optional[str]` | No | 住所 |
| phone | `Optional[str]` | No | 電話番号 |
| fax | `Optional[str]` | No | FAX番号 |
| email | `Optional[str]` | No | メールアドレス |

全フィールド `Optional`。発注書のフォーマットが不定のため、存在しないフィールドがある。
`= None` デフォルト値は使用可能。Gemini には `response_json_schema` 用に JSON Schema を整形して渡す。

### 1.3 OrderItem（品目明細）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| item_number | `Optional[str]` | No | 品番/商品コード |
| description | `Optional[str]` | No | 品名/商品説明 |
| quantity | `Optional[float]` | No | 数量 |
| unit | `Optional[str]` | No | 単位（個、本、kg 等） |
| unit_price | `Optional[float]` | No | 単価（円） |
| amount | `Optional[float]` | No | 金額（円） |

数量・単価・金額は `float` とする（小数点以下がある発注書も存在するため）。

### 1.4 PurchaseOrder（発注書）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| order_number | `Optional[str]` | No | 発注番号 |
| order_date | `Optional[str]` | No | 発注日（原文のまま。正規化しない） |
| delivery_date | `Optional[str]` | No | 納期（原文のまま） |
| orderer | `Optional[Orderer]` | No | 発注元情報 |
| items | `list[OrderItem]` | Yes | 品目明細。空リスト可 |
| subtotal | `Optional[float]` | No | 小計 |
| tax_amount | `Optional[float]` | No | 消費税額 |
| total_amount | `Optional[float]` | No | 合計金額 |
| payment_terms | `Optional[str]` | No | 支払条件 |
| delivery_address | `Optional[str]` | No | 納品先住所 |
| notes | `Optional[str]` | No | 備考 |
| confidence_scores | `dict[str, ConfidenceLevel]` | Yes | 各フィールドの信頼度マップ |

#### confidence_scores のキー命名規則

```
"order_number"               → トップレベルフィールド
"orderer.company_name"       → ネストフィールド（ドット区切り）
"items.0.description"        → 配列要素（インデックス付き）
"items.0.amount"             → 配列要素のフィールド
"subtotal"                   → 金額フィールド
```

#### 日付フィールドについて

- 日付は `str` 型で原文のまま格納する（「2024年3月15日」「3/15」「2024-03-15」等）
- LLM に正規化させない。手書きの場合、正規化の誤りが信頼度を下げる原因になる
- 日付の正規化は本番化フェーズで対応（バリデーションルール追加）

### 1.5 FieldSegment（セグメンテーション結果）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| field_name | `str` | Yes | 対応するフィールド名（confidence_scores と同じキー命名規則） |
| box_2d | `list[int]` | Yes | `[y_min, x_min, y_max, x_max]` 0-1000 正規化座標 |
| ocr_text | `Optional[str]` | No | セグメンテーション時に再読取したテキスト |
| verified | `bool` | Yes | Step 1 の値と画像上のテキストが一致するか |
| confidence | `ConfidenceLevel` | Yes | このフィールドの最終信頼度 |

### 1.6 PipelineResult（パイプライン最終結果）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| purchase_order | `PurchaseOrder` | 構造化データ（Step 3 補完済み） |
| segments | `list[FieldSegment]` | 全フィールドのセグメンテーション結果 |
| processing_time_ms | `int` | 総処理時間（ミリ秒） |
| step1_model | `str` | Step 1 で使用したモデル名 |
| step2_model | `str` | Step 2 で使用したモデル名 |

---

## 2. Step 1: OCR + 構造化抽出

### 2.1 入力

- 発注書画像（PIL.Image.Image）または PDF（bytes + mime_type）
- モデル名（UI で選択）

**対応入力フォーマット**（公式ドキュメント確認済み）:

| フォーマット | MIME | 備考 |
|------------|------|------|
| JPEG | image/jpeg | |
| PNG | image/png | |
| WebP | image/webp | |
| HEIC/HEIF | image/heic, image/heif | |
| PDF | application/pdf | 最大 50MB / 1000ページ。Part.from_bytes で直接渡せる |

BMP, GIF は公式ドキュメントに記載なし。

画像/PDF は `types.Part.from_bytes(data=bytes, mime_type=...)` で渡す。
20MB 以下ならインライン、超える場合は Files API 経由。

**前処理（app.py で実施）**:

1. **EXIF 回転補正（必須）**: 公式ドキュメントに「アップロード前に正しい向きに回転させること」と明記。
   `ImageOps.exif_transpose(image)` を適用してから API に渡す。
2. **解像度リサイズ（推奨）**: 長辺が 1536px を超える場合は 1536px にリサイズする。
   - 1536px 以内なら 4 タイル（1,032 トークン）で処理される（スイートスポット）
   - 1536px 超は 9 タイル以上に跳ね上がるがOCR精度向上は限定的
   - 384px 未満への縮小は OCR 精度低下につながるため禁止
3. **media_resolution**: 手書き発注書（画像）は `HIGH`（デフォルト）を使用。PDF のみ `MEDIUM` 検討。

### 2.2 API 呼び出し方式

Gemini Developer API では `response_schema` が OpenAPI subset で処理され、
`additionalProperties` を含むスキーマは SDK で拒否される。
そのため Step 1 は `response_json_schema` に PurchaseOrder の JSON Schema を渡す。

実装方針:
- `PurchaseOrder.model_json_schema()` をベースに Gemini の対応サブセットへ整形して `response_json_schema` に設定
- 応答は `response.text` を優先し、`PurchaseOrder.model_validate_json(...)` 相当で Pydantic に戻す
- `response.parsed` は補助的にのみ使い、型の最終保証はアプリ側で行う

**`confidence_scores` の `dict[str, ConfidenceLevel]` について**:
`confidence_scores` は JSON Schema 上 `additionalProperties` を使うため、
Gemini Developer API では `response_schema` ではなく `response_json_schema` が必須。

### 2.3 プロンプト方針

プロンプトに含める内容:

1. **役割定義**: 「あなたは発注書の OCR 専門家です」
2. **タスク指示**: 「画像から発注書の全フィールドを抽出してください」
3. **信頼度判定基準の明示**:
   - high: テキストが明瞭に読め、フォーマットも明確
   - medium: テキストは読めるが一部曖昧（手書きのくせ字、かすれ等）
   - low: 判読困難、または該当フィールドが画像上に存在するか不確か
4. **出力形式**: `response_json_schema` が制御するため、プロンプトでは JSON 形式を指定しない
5. **言語指示**: 「日本語の発注書です。フィールド値は原文のまま抽出してください」

### 2.4 出力

- `PurchaseOrder` インスタンス（confidence_scores 含む）
- LLM が抽出できなかったフィールドは `None`

### 2.5 エラーハンドリング

| ケース | 対応 |
|--------|------|
| API タイムアウト | 最大 2 回リトライ（指数バックオフ: 1秒 → 3秒） |
| response.text / response.parsed の片方しか取れない | `response.text` を優先して Pydantic で再検証。空なら `response.parsed` を検証 |
| API レート制限 (429) | 3 秒待機後リトライ。3回失敗でエラー |
| 画像が発注書でない | LLM が空の PurchaseOrder を返す想定。UI で「発注書が検出できませんでした」表示 |

---

## 3. Step 2: セグメンテーション + 検証

### 3.1 入力

- 発注書画像（PIL.Image.Image）
- Step 1 の PurchaseOrder（抽出済みフィールド値を含む）
- モデル名（UI で選択）

### 3.2 API 呼び出し方式

Step 2 も `response_json_schema` を使用する。
`list[FieldSegment]` 自体は `response_schema` でも表現できるが、
Step 1 / Step 2 の Structured Outputs 経路を統一し、Gemini Developer API と Vertex AI の差分を避ける。

Vertex AI 公式サンプル（bounding-box-detection）の `box_2d` パターンは採用するが、
Gemini Developer API では `response_json_schema` + アプリ側 Pydantic 検証を標準とする。

**mask フィールドは含めない。** mask を構造化出力に含めると巨大な base64 データが
スキーマ強制と競合し、500/503 エラーや無限ループが報告されている（GitHub #1378）。
このプロジェクトは box_2d のみで十分なので mask は不要。

thinking_config の設定ロジック:
- モデルが `gemini-2.5-flash` の場合: `thinking_budget=0` を設定
- モデルが `gemini-2.5-pro` の場合: `thinking_config` を省略（デフォルト動作）
- モデルが `gemini-3.x` の場合: `thinking_config` を省略（3.x では別パラメータ体系のため）

### 3.3 プロンプト方針

system_instruction に含める内容（Vertex AI 公式サンプルに倣う）:

```
Return bounding boxes as an array with labels.
Never return masks.
Each bounding box should use box_2d format: [y_min, x_min, y_max, x_max] normalized to 0-1000.
```

contents（ユーザープロンプト）に含める内容:

1. **Step 1 の抽出結果を全文掲載**: フィールド名と値のペアを一覧で渡す
2. **タスク指示**:
   - 各フィールドについて、画像上の対応領域をバウンディングボックスで示す
   - 画像上のテキストを再度読み取り、Step 1 の値と一致するか検証する
3. **出力形式**: `response_json_schema` が制御するため、プロンプトでは JSON 形式を指定しない
4. **verified の判定基準**:
   - `true`: 画像上のテキストと Step 1 の値が実質的に一致（表記揺れは許容）
   - `false`: 明らかに異なる、または画像上にテキストが見つからない

### 3.4 出力

- `list[FieldSegment]`（`response.parsed` で直接取得）

### 3.5 検証（verify）の定義

「一致」の判定は LLM に委ねる。厳密な文字列一致ではなく、意味的一致を期待する。

例:
- Step 1: `"100個"` / 画像: `"100 個"` → verified=true（表記揺れ）
- Step 1: `"山田太郎"` / 画像: `"山田大郎"` → verified=false（漢字の誤読）
- Step 1: `"50,000"` / 画像: `"50000"` → verified=true（カンマの有無）
- Step 1: `"2024-03-15"` / 画像: `"3/15"` → verified=true（同一日付の表記違い）

### 3.6 エラーハンドリング

| ケース | 対応 |
|--------|------|
| response.parsed が None | response.text から手動パースを試みる（```json ラッパーの除去含む）。失敗時はエラー |
| box_2d が 0-1000 範囲外 | 0 と 1000 でクリップ |
| field_name が Step 1 に存在しない | 無視（ログ出力） |
| Step 1 のフィールドに対応するセグメントがない | confidence を medium に設定（検証できなかったため） |

---

## 4. 信頼度マージロジック

Step 1（LLM の自己申告）と Step 2（画像との照合検証）を統合して最終信頼度を決定する。

### 4.1 マージテーブル

| Step 1 confidence | Step 2 verified | → 最終 confidence | 理由 |
|-------------------|-----------------|-------------------|------|
| high | true | **high** | 両ステップで確信あり |
| high | false | **low** | LLM は確信していたが画像と不一致。誤読の可能性 |
| medium | true | **high** | 曖昧だったが画像照合で確認できた |
| medium | false | **low** | 曖昧かつ画像と不一致 |
| low | true | **medium** | 判読困難だったが画像照合では一致。慎重に medium |
| low | false | **low** | 両ステップで確信なし |
| (任意) | (セグメントなし) | **Step 1 のまま** | 検証できなかった。引き上げも引き下げもしない |

### 4.2 マージの実行場所

`pipeline.py` の Step 2 完了後に実行。calculator.py の前。

### 4.3 マージのロジック概要

1. Step 1 の confidence_scores をベースにする
2. Step 2 の各 FieldSegment について:
   - field_name で confidence_scores のキーを照合
   - 上記テーブルに基づいて confidence を更新
3. Step 2 で返されなかったフィールドは Step 1 の値を維持
4. 更新後の confidence_scores を PurchaseOrder に反映
5. FieldSegment の confidence にも最終値を反映

---

## 5. Step 3: 金額バリデーション・補完（calculator.py）

LLM を使用しない純粋なロジック。

### 5.1 品目明細の検算

各 OrderItem について、3値（quantity, unit_price, amount）の整合性を確認する。

**ルール A: 3値すべて存在する場合**

```
expected = quantity * unit_price
tolerance = max(expected * 0.01, 1.0)    # 1% または 1円 の大きい方

if |amount - expected| <= tolerance:
    → 整合。confidence 変更なし
else:
    → 不整合。items.{i}.quantity, items.{i}.unit_price, items.{i}.amount
      すべての confidence を low に設定
```

許容誤差を設ける理由: 手書きの場合、税込/税抜の混在や端数処理の違いがある。

**ルール B: 2値存在・1値欠損の場合**

```
quantity と unit_price あり、amount なし → amount = quantity * unit_price を補完
quantity と amount あり、unit_price なし → unit_price = amount / quantity を補完
unit_price と amount あり、quantity なし → quantity = amount / unit_price を補完
```

補完した値の confidence は `medium` に設定する（算術的に正しいが、原本にない値のため）。

**ルール C: 1値以下しかない場合**

→ 補完しない。confidence 変更なし。

### 5.2 小計の検算

```
expected_subtotal = sum(item.amount for item in items if item.amount is not None)
```

**ルール D: subtotal が存在する場合**

```
tolerance = max(expected_subtotal * 0.01, 1.0)

if |subtotal - expected_subtotal| <= tolerance:
    → 整合。confidence 変更なし
else:
    → 不整合。"subtotal" の confidence を low に設定
```

**ルール E: subtotal が欠損、items の amount がすべて存在する場合**

```
subtotal = expected_subtotal を補完
confidence_scores["subtotal"] = "medium"
```

### 5.3 合計金額の検算

3値（subtotal, tax_amount, total_amount）の関係:
```
subtotal + tax_amount = total_amount
```

**ルール F: 3値すべて存在する場合**

```
tolerance = max(total_amount * 0.01, 1.0)

if |total_amount - (subtotal + tax_amount)| <= tolerance:
    → 整合。confidence 変更なし
else:
    → 不整合。"subtotal", "tax_amount", "total_amount"
      すべての confidence を low に設定
```

**ルール G: 2値存在・1値欠損の場合**

```
subtotal + tax_amount あり → total_amount = subtotal + tax_amount
subtotal + total_amount あり → tax_amount = total_amount - subtotal
tax_amount + total_amount あり → subtotal = total_amount - tax_amount
```

補完した値の confidence は `medium` に設定する。

**ルール H: 1値以下しかない場合**

→ 補完しない。

### 5.4 補完の実行順序

1. 品目明細の検算・補完（ルール A → B → C）
2. 小計の検算・補完（ルール D → E）
3. 合計金額の検算・補完（ルール F → G → H）

順序が重要: 品目の amount を補完してから小計を検算する。

### 5.5 confidence の上書きルール

calculator.py は confidence を **low 方向にのみ変更する**（high/medium → low）。
または、補完値に対して `medium` を設定する。
calculator.py が confidence を high に引き上げることはない。

---

## 6. 座標変換とバウンディングボックス描画（visualizer.py）

### 6.1 座標変換

Gemini の box_2d は 0-1000 正規化座標。ピクセル座標への変換:

```
pixel_y_min = (box_2d[0] / 1000) * image_height
pixel_x_min = (box_2d[1] / 1000) * image_width
pixel_y_max = (box_2d[2] / 1000) * image_height
pixel_x_max = (box_2d[3] / 1000) * image_width
```

座標のクリップ: 変換後の値が画像サイズを超える場合は画像境界にクリップする。

### 6.2 描画仕様

| 要素 | 仕様 |
|------|------|
| ボックス枠 | 矩形。角丸なし |
| 枠の太さ | 3px |
| 枠の色 | confidence に応じた色（6.3 参照） |
| 半透明塗り | ボックス内部を枠の色で 20% 透過で塗る |
| ラベル | ボックスの左上外側にフィールド名を表示 |
| ラベルフォント | デフォルトフォント。サイズ 14px 相当 |
| ラベル背景 | 枠の色で塗り、白文字 |

### 6.3 色定義

| ConfidenceLevel | 枠色 (RGB) | 用途 |
|-----------------|-----------|------|
| high | `(33, 150, 243)` / #2196F3 | 青。確認不要 |
| medium | `(255, 193, 7)` / #FFC107 | 黄。確認推奨 |
| low | `(244, 67, 54)` / #F44336 | 赤。要確認 |

### 6.4 入出力

- 入力: 原本画像（PIL.Image.Image）, `list[FieldSegment]`
- 出力: アノテーション付き画像（PIL.Image.Image）。原本は変更しない（コピーに描画）

### 6.5 ボックスの重なり対策

複数ボックスが重なる場合:
- 半透明塗りのため自然に重なる（特別な処理不要）
- ラベルが重なる場合は、低信頼度のラベルを上に描画する（赤が最前面）

描画順序: high → medium → low の順に描画（low が最後＝最前面）

---

## 7. UI 仕様（app.py / Streamlit）

### 7.1 レイアウト

```
┌─ サイドバー ──────────┐  ┌─ メインエリア ──────────────────────┐
│                        │  │                                      │
│ 📄 ファイルアップロード  │  │ ヘッダー: タイトル + 要確認サマリー    │
│  file_uploader         │  │                                      │
│                        │  │ ┌─ 左カラム ──┐ ┌─ 右カラム ────────┐│
│ ⚙️ 設定                │  │ │ アノテーション │ │ 構造化データ表     ││
│  Step 1 モデル選択      │  │ │ 付き原本画像  │ │ (信頼度バッジ付き) ││
│  Step 2 モデル選択      │  │ │              │ │                  ││
│  ☑ 金額自動補完        │  │ └──────────────┘ └──────────────────┘│
│                        │  │                                      │
│ [🚀 解析開始]          │  │ タブ: 全文テキスト / Raw JSON         │
│                        │  │                                      │
│ 処理時間表示           │  │ メタ情報（使用モデル、処理時間）       │
└────────────────────────┘  └──────────────────────────────────────┘
```

### 7.2 サイドバー

**ファイルアップロード**:
- `st.file_uploader` で画像/PDF を受付
- 許可 MIME: `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`, `application/pdf`
  （BMP, GIF は Gemini 公式ドキュメントに記載なし）
- サイズ上限: 20MB（Gemini API のインライン上限。PDF は Files API 経由で 50MB まで可）

**モデル選択**:
- Step 1 モデル: `st.selectbox` で選択
- Step 2 モデル: `st.selectbox` で選択
- 選択肢リスト（ハードコードで定義）:
  ```
  "gemini-2.5-pro"
  "gemini-2.5-flash"
  "gemini-2.5-flash-lite"
  "gemini-3-flash"
  "gemini-3.1-pro-preview"
  ```
- デフォルト: Step 1 = `gemini-2.5-pro`, Step 2 = `gemini-2.5-flash`
- API から利用可能なモデルを動的取得する必要はない（デモ用途のため）

**金額自動補完**:
- `st.checkbox`。デフォルト ON
- OFF にすると Step 3 の calculator.py の補完ロジックをスキップ（検算のみ実行）

**解析開始ボタン**:
- ファイルがアップロードされている場合のみ有効
- 処理中は `st.spinner` でローディング表示

### 7.3 メインエリア: ヘッダー

解析完了後に表示:
```
📊 要確認: {low_count}件（🔴赤枠）/ 確認推奨: {medium_count}件（🟡黄枠）/ OK: {high_count}件（🔵青枠）
```

### 7.4 メインエリア: 左カラム（画像）

- 解析前: アップロードされた原本画像をそのまま表示
- 解析後: visualizer.py で描画したアノテーション付き画像を表示
- `st.image` で表示。`use_container_width=True`

### 7.5 メインエリア: 右カラム（構造化データ）

解析完了後に表示。セクションに分けて expander で折りたたみ可能にする。

**セクション構成**:

1. **発注基本情報**: order_number, order_date, delivery_date, payment_terms
2. **発注元情報**: orderer 内の全フィールド
3. **品目明細**: items のテーブル表示
4. **金額情報**: subtotal, tax_amount, total_amount
5. **その他**: delivery_address, notes

各フィールドの表示形式:
```
{フィールド名}    {値}    {信頼度バッジ}
```

信頼度バッジ:
- high: 🔵 (目立たない)
- medium: 🟡
- low: 🔴 **太字で値を強調**

品目明細はテーブル (`st.dataframe` または `st.table`) で表示。
各セルに信頼度に応じた背景色を付ける（可能な範囲で。Streamlit の制約あり）。

### 7.6 メインエリア: タブ

- **全文テキスト**: PurchaseOrder の全フィールドをプレーンテキストで表示
- **Raw JSON**: PurchaseOrder を `model_dump_json(indent=2)` で表示（`st.code` でシンタックスハイライト）

### 7.7 処理中の表示

```python
with st.spinner("Step 1: OCR + 構造化抽出中..."):
    # Step 1 実行
with st.spinner("Step 2: セグメンテーション + 検証中..."):
    # Step 2 実行
with st.spinner("Step 3: 金額バリデーション中..."):
    # Step 3 実行
```

各 Step の完了時にプログレスを更新。ユーザーが「今何をしているか」わかるようにする。

---

## 8. モデル選択と thinking_config ロジック

### 8.1 モデル別の設定

| モデル | thinking_config | 構造化出力 | box_2d 対応 | mask 対応 |
|--------|----------------|---------------------|-------------|-----------|
| gemini-2.5-pro | 省略（デフォルト。最小 128） | あり | あり | あり |
| gemini-2.5-flash | thinking_budget=0 | あり | あり | あり |
| gemini-2.5-flash-lite | 省略 | あり | 要検証 | 要検証 |
| gemini-3-flash | 省略 | あり | あり（公式例あり） | **なし** |
| gemini-3.1-pro-preview | 省略 | あり | あり（推定） | **なし** |

### 8.2 llm_client.py での分岐ロジック

Step 2 の config 構築時:

```
if model == "gemini-2.5-flash":
    thinking_config = ThinkingConfig(thinking_budget=0)
else:
    thinking_config = None  # 省略
```

Step 1 は構造化出力のため thinking_config は常に省略（不要なため）。

---

## 9. エラーハンドリング方針

### 9.1 リトライ

| エラー種別 | リトライ回数 | 待機時間 |
|-----------|------------|----------|
| API タイムアウト | 2回 | 1秒, 3秒（指数バックオフ） |
| レート制限 (429) | 3回 | 3秒, 6秒, 12秒 |
| サーバーエラー (500/503) | 2回 | 2秒, 4秒 |

### 9.2 UI でのエラー表示

- API エラー: `st.error("Gemini API エラー: {詳細}")` で表示。処理中断
- 部分的エラー（Step 2 失敗）: Step 1 の結果のみ表示。セグメンテーションなしで画像は原本のまま
- バリデーションエラー（JSON パース失敗等）: `st.warning` で警告表示し、可能な範囲で結果表示

### 9.3 グレースフルデグラデーション

パイプラインの各 Step は独立して失敗しても、前の Step までの結果を表示する:

```
Step 1 成功、Step 2 失敗 → 構造化データは表示。画像はバウンディングボックスなし
Step 1 成功、Step 2 成功、Step 3 失敗 → 金額補完なしで表示（検算エラーはログ）
Step 1 失敗 → エラー表示。以降の Step は実行しない
```

---

## 10. 環境設定

### 10.1 環境変数

`.env` ファイルに配置:

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `GEMINI_API_KEY` | Yes | — | Gemini API キー |

モデル名は環境変数ではなく UI のサイドバーで選択する。

### 10.2 定数

アプリ内でハードコードする値（設定ファイル不要。デモのため）:

| 定数 | 値 | 説明 |
|------|-----|------|
| MAX_FILE_SIZE_MB | 20 | アップロード上限 |
| MAX_RETRIES | 3 | API リトライ最大回数 |
| AMOUNT_TOLERANCE_RATIO | 0.01 | 金額整合性の許容誤差（1%） |
| AMOUNT_TOLERANCE_MIN | 1.0 | 金額整合性の最小許容誤差（1円） |
| BOX_LINE_WIDTH | 3 | バウンディングボックスの枠太さ |
| BOX_FILL_ALPHA | 51 | ボックス内塗りの透過度（0-255。51 ≈ 20%） |
| LABEL_FONT_SIZE | 14 | ラベルのフォントサイズ |

---

## 11. テスト方針

DESIGN.md セクション 8 に準拠。追加の観点:

### 11.1 calculator.py のテストケース

| テスト | 入力 | 期待結果 |
|--------|------|----------|
| 品目検算: 整合 | qty=100, price=500, amount=50000 | confidence 変更なし |
| 品目検算: 不整合 | qty=100, price=500, amount=60000 | 3フィールドとも low |
| 品目検算: 許容誤差内 | qty=3, price=333, amount=1000 | 整合扱い（999 vs 1000、誤差 0.1%） |
| 品目補完: amount 欠損 | qty=100, price=500, amount=None | amount=50000, confidence=medium |
| 品目補完: 1値のみ | qty=100, price=None, amount=None | 補完なし |
| 小計検算: 整合 | items=[50000, 30000], subtotal=80000 | confidence 変更なし |
| 小計検算: 不整合 | items=[50000, 30000], subtotal=90000 | subtotal の confidence=low |
| 合計補完: tax 欠損 | subtotal=80000, tax=None, total=88000 | tax=8000, confidence=medium |
| 全値なし | subtotal=None, tax=None, total=None | 何もしない |

### 11.2 信頼度マージのテストケース

| Step 1 | Step 2 verified | 期待結果 |
|--------|-----------------|----------|
| high + true | | high |
| high + false | | low |
| medium + true | | high |
| medium + false | | low |
| low + true | | medium |
| low + false | | low |
| high + セグメントなし | | high（変更なし） |

---

## 12. 未決定事項・検証項目

| # | 項目 | 優先度 | 方針 |
|---|------|--------|------|
| 1 | `dict[str, ConfidenceLevel]` を Gemini Developer API でどう扱うか | 高 | `response_json_schema` を使う。`response_schema` は `additionalProperties` で失敗 |
| 2 | gemini-3-flash-preview で box_2d が実際に返るか | 中 | 実装後にモデル切替で検証 |
| 3 | 品目明細が多い場合（20行以上）のセグメンテーション精度 | 低 | デモ用サンプルで検証 |
| 4 | 日本語フォントの Pillow 描画（ラベル表示） | 中 | システムフォント検索 or IPAフォント同梱 |
| 5 | `response_json_schema` + `thinking_budget=0` の実 API 挙動 | 中 | Step 2 の実呼び出しで継続確認 |

### 解決済み

| # | 項目 | 結論 |
|---|------|------|
| ~~A~~ | ~~PDF 入力の対応方法~~ | **対応済み。** `Part.from_bytes(data=bytes, mime_type="application/pdf")` で直接渡せる（公式確認済み） |
| ~~B~~ | ~~box_2d に構造化出力が使えるか~~ | **使える。** Vertex AI 公式サンプルの box_2d 形式を `response_json_schema` に移植可能 |
| ~~C~~ | ~~カスタムフィールド（verified等）を追加できるか~~ | **できる。** `FieldSegment` の JSON Schema に含めて返させる。mask だけは含めない |
| ~~D~~ | ~~JSON パースの信頼性~~ | **アプリ側で担保する。** `response.text` / `response.parsed` を Pydantic で再検証する |
