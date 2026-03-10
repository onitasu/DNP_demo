"""AI-OCR デモアプリ — 発注書構造化データ抽出。"""

from __future__ import annotations

import io
import os

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps

from ocr.models import ConfidenceLevel, PipelineResult, PurchaseOrder
from ocr.pipeline import run_pipeline
from ocr.visualizer import draw_bounding_boxes

load_dotenv()

# ── 定数 ──────────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB = 20
MAX_LONG_SIDE_PX = 1536
MIN_LONG_SIDE_PX = 384

STEP1_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
    "gemini-3.1-pro-preview",
]
STEP2_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
    "gemini-3.1-pro-preview",
]

_CONFIDENCE_BADGE = {"high": "🔵", "medium": "🟡", "low": "🔴"}
_CONFIDENCE_COLOR = {"high": "#2196F3", "medium": "#FFC107", "low": "#F44336"}


# ── ヘルパー ──────────────────────────────────────────────────────────────────


def _preprocess_image(pil_image: Image.Image) -> Image.Image:
    """EXIF 回転補正 + 長辺リサイズ（1536px 以内）。"""
    img = ImageOps.exif_transpose(pil_image).convert("RGB")
    w, h = img.size
    long_side = max(w, h)
    if long_side > MAX_LONG_SIDE_PX:
        scale = MAX_LONG_SIDE_PX / long_side
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def _count_by_confidence(order: PurchaseOrder) -> dict[ConfidenceLevel, int]:
    counts: dict[ConfidenceLevel, int] = {"high": 0, "medium": 0, "low": 0}
    for level in order.confidence_scores.values():
        counts[level] += 1
    return counts


def _badge(field: str, scores: dict[str, ConfidenceLevel]) -> str:
    level = scores.get(field, "medium")
    return _CONFIDENCE_BADGE[level]


def _field_row(
    label: str, value: object, key: str, scores: dict[str, ConfidenceLevel]
) -> None:
    level = scores.get(key, "medium")
    badge = _CONFIDENCE_BADGE[level]
    val_str = str(value) if value is not None else "—"
    if level == "low":
        st.markdown(
            f"**{label}** &nbsp; **{val_str}** &nbsp; {badge}", unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"**{label}** &nbsp; {val_str} &nbsp; {badge}", unsafe_allow_html=True
        )


# ── UI ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI-OCR Demo — 発注書読み取り", layout="wide")
st.title("AI-OCR Demo — 発注書読み取り")

# ─ サイドバー ─
with st.sidebar:
    st.header("設定")

    uploaded = st.file_uploader(
        "発注書をアップロード",
        type=["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"],
        help="最大 20MB。JPEG / PNG / WebP / HEIC / PDF に対応。",
    )

    step1_model = st.selectbox("Step 1 モデル（OCR + 抽出）", STEP1_MODELS, index=0)
    step2_model = st.selectbox(
        "Step 2 モデル（セグメンテーション）", STEP2_MODELS, index=0
    )
    enable_calc = st.checkbox("金額自動補完", value=True)

    run_btn = st.button("🚀 解析開始", disabled=(uploaded is None), type="primary")

    if "result" in st.session_state and st.session_state.result is not None:
        r: PipelineResult = st.session_state.result
        st.divider()
        st.caption(f"処理時間: {r.processing_time_ms / 1000:.1f} 秒")
        st.caption(f"Step 1: {r.step1_model}")
        st.caption(f"Step 2: {r.step2_model}")

# ─ メインエリア ─
left_col, right_col = st.columns([1, 1])

# ─ 解析実行 ─
if run_btn and uploaded is not None:
    file_bytes = uploaded.read()

    # サイズチェック
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"ファイルサイズが {MAX_FILE_SIZE_MB}MB を超えています。")
        st.stop()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("GEMINI_API_KEY が設定されていません。.env に記載してください。")
        st.stop()

    # PDF かどうかで分岐
    is_pdf = uploaded.type == "application/pdf" or uploaded.name.endswith(".pdf")

    if is_pdf:
        preview_image = None
        process_image = file_bytes
        mime_type = "application/pdf"
    else:
        pil_raw = Image.open(io.BytesIO(file_bytes))
        process_image = _preprocess_image(pil_raw)
        preview_image = process_image
        mime_type = "image/png"

    # Step 1
    progress = st.progress(0, text="Step 1: OCR + 構造化抽出中...")
    try:
        with st.spinner("Step 1: OCR + 構造化抽出中..."):
            # pipeline は bytes または Image を受け付ける
            result = run_pipeline(
                image=process_image,
                api_key=api_key,
                step1_model=step1_model,
                step2_model=step2_model,
                enable_calculator=enable_calc,
                mime_type=mime_type,
            )
        progress.progress(100, text="完了")
        st.session_state.result = result
        st.session_state.preview_image = preview_image
    except Exception as e:
        st.error(f"Gemini API エラー: {e}")
        st.stop()

# ─ 結果表示 ─
result: PipelineResult | None = st.session_state.get("result")
preview_image: Image.Image | None = st.session_state.get("preview_image")

if result is not None:
    order = result.purchase_order
    scores = order.confidence_scores
    counts = _count_by_confidence(order)

    # ヘッダー: サマリー
    st.markdown(
        f"📊 **要確認: {counts['low']}件**（🔴赤枠）"
        f" / 確認推奨: {counts['medium']}件（🟡黄枠）"
        f" / OK: {counts['high']}件（🔵青枠）"
    )
    st.divider()

with left_col:
    st.subheader("原本 + 検出結果")
    if uploaded is not None:
        if result is not None and preview_image is not None and result.segments:
            annotated = draw_bounding_boxes(preview_image, result.segments)
            st.image(annotated, use_container_width=True)
        elif preview_image is not None:
            st.image(preview_image, use_container_width=True)
        else:
            st.info("PDF はプレビューできません。")
    else:
        st.info("左のサイドバーからファイルをアップロードしてください。")

with right_col:
    st.subheader("抽出データ")
    if result is None:
        st.info("解析実行後に結果が表示されます。")
    else:
        order = result.purchase_order
        scores = order.confidence_scores

        with st.expander("発注基本情報", expanded=True):
            _field_row("発注番号", order.order_number, "order_number", scores)
            _field_row("発注日", order.order_date, "order_date", scores)
            _field_row("納期", order.delivery_date, "delivery_date", scores)
            _field_row("支払条件", order.payment_terms, "payment_terms", scores)

        with st.expander("発注元情報", expanded=True):
            if order.orderer:
                o = order.orderer
                _field_row("会社名", o.company_name, "orderer.company_name", scores)
                _field_row("部署名", o.department, "orderer.department", scores)
                _field_row("担当者", o.contact_person, "orderer.contact_person", scores)
                _field_row("住所", o.address, "orderer.address", scores)
                _field_row("電話", o.phone, "orderer.phone", scores)
                _field_row("FAX", o.fax, "orderer.fax", scores)
                _field_row("メール", o.email, "orderer.email", scores)
            else:
                st.caption("発注元情報なし")

        with st.expander("品目明細", expanded=True):
            if order.items:
                for i, item in enumerate(order.items):
                    st.markdown(f"**品目 {i + 1}**")
                    _field_row(
                        "品番", item.item_number, f"items.{i}.item_number", scores
                    )
                    _field_row(
                        "品名", item.description, f"items.{i}.description", scores
                    )
                    _field_row("数量", item.quantity, f"items.{i}.quantity", scores)
                    _field_row("単位", item.unit, f"items.{i}.unit", scores)
                    _field_row("単価", item.unit_price, f"items.{i}.unit_price", scores)
                    _field_row("金額", item.amount, f"items.{i}.amount", scores)
                    if i < len(order.items) - 1:
                        st.divider()
            else:
                st.caption("品目なし")

        with st.expander("金額情報", expanded=True):
            _field_row("小計", order.subtotal, "subtotal", scores)
            _field_row("消費税", order.tax_amount, "tax_amount", scores)
            _field_row("合計", order.total_amount, "total_amount", scores)

        with st.expander("その他"):
            _field_row("納品先", order.delivery_address, "delivery_address", scores)
            _field_row("備考", order.notes, "notes", scores)

        tab_text, tab_json = st.tabs(["全文テキスト", "Raw JSON"])
        with tab_text:
            st.text(order.model_dump_json(indent=2))
        with tab_json:
            st.code(order.model_dump_json(indent=2), language="json")
