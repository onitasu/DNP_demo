# 技術メモ — google-genai SDK & Gemini API

> API 調査日: 2026-03-10

## SDK 情報

| 項目 | 値 |
|------|-----|
| パッケージ名 | `google-genai` (PyPI) |
| 最新バージョン | 1.66.0 (2026-03-04) |
| インポート | `from google import genai` / `from google.genai import types` |
| 旧パッケージ | `google-generativeai` — **非推奨。使わない** |

## モデル一覧

### 安定版（本番推奨）

| モデル ID | 用途 |
|-----------|------|
| `gemini-2.5-pro` | 最高精度。OCR + 構造化抽出、セグメンテーション |
| `gemini-2.5-flash` | 低レイテンシ。thinking_budget=0 が使える唯一のモデル |
| `gemini-2.5-flash-lite` | 最速・最低コスト |

### プレビュー版（デモでは使用可）

- `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite-preview`, `gemini-3-flash`
- すべてプレビュー。最短2週間で廃止リスク（`gemini-3-pro-preview` は 2026/03/09 廃止済み）
- デモ用途なら許容可能。本番化時は安定版に切り替える前提

### Gemini 3.x のセグメンテーション制約

公式（https://ai.google.dev/gemini-api/docs/gemini-3）：
> "Image segmentation capabilities (returning pixel-level masks for objects)
> are not supported in Gemini 3 Pro or Gemini 3 Flash."

- **mask（ピクセルレベルマスク）**: Gemini 3 では非対応
- **box_2d（バウンディングボックス）**: image-understanding ドキュメントのコード例で
  `gemini-3-flash-preview` が使われており、対応している可能性あり
- 本プロジェクトの主目的は box_2d なので Gemini 3.x も選択肢に入る

### セグメンテーション精度比較

- **公式推奨**: `gemini-2.5-flash` + `thinking_budget=0`（Google Developers Blog）
- **定量比較データ**: 未公開。モデル間のセグメンテーション精度ベンチマークは存在しない
- **コスト差**: 2.5-pro は 2.5-flash の約 18 倍（出力 $10 vs $0.60/M tokens）
- **方針**: UI でモデル切替可能にし、実際の発注書で検証する

## 構造化出力パターン

```python
from google import genai
from google.genai import types
from pydantic import BaseModel

client = genai.Client(api_key="...")

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[image, prompt_text],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=PydanticModel.model_json_schema(),
    ),
)
result = PydanticModel.model_validate_json(response.text)
```

### Pydantic スキーマの注意点

- `Optional[str] = None` は OK
- `dict[str, ...]` は Gemini Developer API の `response_schema` だと `additionalProperties` で失敗する
- `response_json_schema` を使う場合は `default` など未対応キーワードを落として渡すと安全

## 画像入力パターン

```python
from PIL import Image

# PIL Image を直接渡す（20MB 未満）
im = Image.open("order.png")
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[im, prompt_text],  # テキストは画像の後に置く
)

# bytes から Part を作成
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        prompt_text,
    ],
)
```

## セグメンテーション / バウンディングボックス

- `box_2d`: `[y0, x0, y1, x1]` 0-1000 正規化座標
- ピクセル変換: `pixel = (normalized / 1000) * image_dimension`
- `mask`: base64 PNG（バウンディングボックスサイズにリサイズ後 127 で二値化）

## thinking_config 制約

| モデル | thinking_budget=0 | 有効範囲 |
|--------|-------------------|----------|
| `gemini-2.5-pro` | **使用不可** | 128〜32,768 |
| `gemini-2.5-flash` | 使用可能 | 0〜24,576 |

**重要**: セグメンテーション Step で `thinking_budget=0` を使うなら、
Step 2 のみ `gemini-2.5-flash` に切り替えるか、`thinking_config` を省略する。

## セグメンテーション呼び出し例

```python
response = client.models.generate_content(
    model="gemini-2.5-flash",  # thinking_budget=0 を使う場合は flash
    contents=[image, segmentation_prompt],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
)
```

## 画像入力の最適化

> ソース: https://ai.google.dev/gemini-api/docs/image-understanding
> ソース: https://ai.google.dev/gemini-api/docs/tokens
> ソース: https://ai.google.dev/gemini-api/docs/document-processing
> ソース: https://ai.google.dev/gemini-api/docs/vision

### 対応フォーマット

| フォーマット | MIME タイプ | 備考 |
|-------------|-----------|------|
| JPEG | `image/jpeg` | 写真・スキャン画像に最適 |
| PNG | `image/png` | テキスト多い文書に最適（可逆圧縮） |
| WebP | `image/webp` | 対応しているが積極的な理由なし |
| HEIC/HEIF | `image/heic` | iOS 撮影画像 |
| PDF | `application/pdf` | 直接対応。画像変換不要 |

- BMP、GIF は公式ドキュメントに記載なし（非推奨）
- **推奨**: スキャン文書は **PNG**（可逆圧縮でテキストエッジが劣化しない）、写真撮影は **JPEG q≥90**

### 画像トークンコスト（タイリング方式）

公式（https://ai.google.dev/gemini-api/docs/tokens）：

- **384px 以下**: 固定 258 トークン（リサイズなし）
- **384px 超**: タイルに分割。各タイル = 258 トークン

**タイル数の計算式**:
```
crop_unit = floor(min(width, height) / 1.5)
tiles = ceil(width / crop_unit) × ceil(height / crop_unit)
tokens = tiles × 258
```

**実用上のサイズとトークンコスト**:

| 画像サイズ | タイル数 | トークン |
|-----------|---------|---------|
| 384×384 以下 | 1 | 258 |
| 768×768 | 4 | 1,032 |
| 1024×1024 | 4 | 1,032 |
| 1536×1536 | 4 | 1,032 |
| 2048×2048 | 9 | 2,322 |
| 3072×3072 | 16 | 4,128 |

**スイートスポット: 1024〜1536px**。768px と同じ 4 タイル（1,032 トークン）で、より高い解像度を活用できる。

### 解像度の推奨設定

- **発注書スキャン画像**: 長辺 **1024〜1536px** に事前リサイズ推奨
  - 1536px 超はトークンコストが跳ね上がる（9 タイル以上）が精度向上は限定的
  - 384px 未満まで縮小すると OCR 精度が低下
- **元画像が高解像度（3000px+）の場合**: アップロード前にリサイズすることでコスト削減
- API 側でも自動リサイズされるが、事前リサイズでアップロード時間を短縮

### media_resolution パラメータ

公式（https://ai.google.dev/gemini-api/docs/image-understanding）：

```python
config = types.GenerateContentConfig(
    media_resolution=types.MediaResolution.MEDIUM,  # or HIGH
)
```

| 値 | 用途 | トークン |
|----|------|---------|
| `MEDIUM` | PDF OCR、テキスト中心の文書 | 低め |
| `HIGH` | 画像スキャン、手書き、細かい文字 | 高め（デフォルト） |

- **本プロジェクト**: 手書き発注書を扱うため `HIGH`（デフォルト）を使用
- PDF 入力時のみ `MEDIUM` で十分な可能性あり（要検証）

### PDF 入力

公式（https://ai.google.dev/gemini-api/docs/document-processing）：

- `Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")` で直接入力可能
- 画像への事前変換は**不要**
- 制約: **最大 50MB / 1,000 ページ**
- 各ページは **最大 3072×3072** にスケーリング、**最小 768×768** にアップスケーリング
- **1 ページ = 258 トークン固定**（画像のタイリング方式とは異なる）

```python
with open("order.pdf", "rb") as f:
    pdf_bytes = f.read()

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        prompt_text,
    ],
)
```

### 前処理の要件

公式（https://ai.google.dev/gemini-api/docs/image-understanding）：

> "Rotate images to the correct orientation before uploading."

- **回転補正は必須**。Gemini は自動回転検出を行わない
- EXIF Orientation タグがある場合は `ImageOps.exif_transpose()` で正位置に変換してから送信
- スキャナーの傾き補正（deskew）は API 側で不要（軽微な傾きは許容される）

```python
from PIL import Image, ImageOps

im = Image.open("scan.jpg")
im = ImageOps.exif_transpose(im)  # EXIF 回転補正
```
