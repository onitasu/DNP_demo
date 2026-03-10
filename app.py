"""AI-OCR デモアプリ — 発注書構造化データ抽出。"""

from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps

from ocr.models import ConfidenceLevel, PipelineResult, PurchaseOrder
from ocr.pipeline import run_pipeline
from ocr.result_table import build_result_rows
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


def _build_result_dataframe(result: PipelineResult) -> pd.DataFrame:
    rows = build_result_rows(result.purchase_order, result.segments)
    return pd.DataFrame(
        [
            {
                "区分": row["section"],
                "項目": row["label"],
                "抽出値": row["value"],
                "信頼性": row["confidence_label"],
                "field_key": row["field_key"],
            }
            for row in rows
        ]
    )


def _style_result_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    visible_df = df.drop(columns=["field_key"])
    styles = pd.DataFrame("", index=visible_df.index, columns=visible_df.columns)

    low_mask = (df["信頼性"] == "要確認") & (df["抽出値"] != "—")
    medium_mask = (df["信頼性"] == "確認推奨") & (df["抽出値"] != "—")

    styles.loc[low_mask, "抽出値"] = "color: #c62828; font-weight: 700;"
    styles.loc[low_mask, "信頼性"] = "color: #c62828; font-weight: 700;"
    styles.loc[medium_mask, "抽出値"] = "color: #111111; font-weight: 700;"
    styles.loc[medium_mask, "信頼性"] = "color: #111111; font-weight: 700;"

    return visible_df.style.apply(lambda _: styles, axis=None)


def _get_gemini_api_key() -> str:
    secret_value = st.secrets.get("GEMINI_API_KEY", "")
    if isinstance(secret_value, str) and secret_value:
        return secret_value
    return os.environ.get("GEMINI_API_KEY", "")


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

# ─ 解析実行 ─
if run_btn and uploaded is not None:
    file_bytes = uploaded.read()

    # サイズチェック
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"ファイルサイズが {MAX_FILE_SIZE_MB}MB を超えています。")
        st.stop()

    api_key = _get_gemini_api_key()
    if not api_key:
        st.error(
            "GEMINI_API_KEY が設定されていません。.env または Streamlit secrets に設定してください。"
        )
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
    counts = _count_by_confidence(order)

    st.markdown(
        f"**要確認:** {counts['low']}件"
        f" / **確認推奨:** {counts['medium']}件"
        f" / **OK:** {counts['high']}件"
    )
    st.divider()

data_col, image_col = st.columns([1.15, 0.85])

if result is None:
    with data_col:
        st.subheader("抽出データ一覧")
        st.info("解析実行後に結果が表示されます。")
    with image_col:
        st.subheader("原本 + 検出結果")
        st.info("左のサイドバーからファイルをアップロードしてください。")
else:
    result_df = _build_result_dataframe(result)
    selected_field_name: str | None = None

    with data_col:
        st.subheader("抽出データ一覧")
        selection = st.dataframe(
            _style_result_dataframe(result_df),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="result_table",
            column_config={
                "区分": st.column_config.TextColumn(width="medium"),
                "項目": st.column_config.TextColumn(width="small"),
                "抽出値": st.column_config.TextColumn(width="medium"),
                "信頼性": st.column_config.TextColumn(width="small"),
            },
        )

        selected_rows = selection.selection.rows
        if selected_rows:
            selected_row = result_df.iloc[selected_rows[0]]
            selected_field_name = str(selected_row["field_key"])
            st.caption(
                f"選択中: {selected_row['区分']} / {selected_row['項目']} / {selected_row['抽出値']}"
            )
        else:
            st.caption("表の行を選ぶと、画像上の枠を黒太枠で強調表示します。")

    with image_col:
        st.subheader("原本 + 検出結果")
        if uploaded is not None:
            if result.segments and preview_image is not None:
                annotated = draw_bounding_boxes(
                    preview_image,
                    result.segments,
                    selected_field_name=selected_field_name,
                )
                st.image(annotated, use_container_width=True)
            elif preview_image is not None:
                st.image(preview_image, use_container_width=True)
            else:
                st.info("PDF はプレビューできません。")
        else:
            st.info("左のサイドバーからファイルをアップロードしてください。")

    with st.expander("詳細データ", expanded=False):
        tab_text, tab_json = st.tabs(["全文テキスト", "Raw JSON"])
        with tab_text:
            st.text(order.model_dump_json(indent=2))
        with tab_json:
            st.code(order.model_dump_json(indent=2), language="json")
