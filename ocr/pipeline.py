"""2段階パイプライン: OCR → セグメンテーション → バリデーション。"""

from __future__ import annotations

import time
from typing import Union

from PIL import Image
from google import genai

from ocr.calculator import validate_and_complete
from ocr.llm_client import extract_purchase_order, extract_segments
from ocr.models import ConfidenceLevel, FieldSegment, PipelineResult, PurchaseOrder

_MERGE_TABLE: dict[tuple[ConfidenceLevel, bool], ConfidenceLevel] = {
    ("high", True): "high",
    ("high", False): "low",
    ("medium", True): "high",
    ("medium", False): "low",
    ("low", True): "medium",
    ("low", False): "low",
}


def merge_confidence(
    purchase_order: PurchaseOrder,
    segments: list[FieldSegment],
) -> tuple[PurchaseOrder, list[FieldSegment]]:
    """Step 1 と Step 2 の信頼度をマージする。

    REQUIREMENTS.md §4.1 のマージテーブルに基づく。
    セグメントが存在しないフィールドは Step 1 の値を維持。
    """
    # field_name -> FieldSegment のマップ
    segment_map: dict[str, FieldSegment] = {s.field_name: s for s in segments}

    updated_scores = dict(purchase_order.confidence_scores)
    updated_segments: list[FieldSegment] = []

    for field_name, step1_confidence in purchase_order.confidence_scores.items():
        if field_name in segment_map:
            seg = segment_map[field_name]
            final = _MERGE_TABLE.get((step1_confidence, seg.verified), step1_confidence)
            updated_scores[field_name] = final
            # FieldSegment.confidence も最終値に更新
            seg_data = seg.model_dump()
            seg_data["confidence"] = final
            updated_segments.append(FieldSegment(**seg_data))
        # セグメントがないフィールドは Step 1 の値を維持（変更なし）

    # セグメントに存在するが confidence_scores にないフィールドも追加
    for seg in segments:
        if seg.field_name not in purchase_order.confidence_scores:
            updated_segments.append(seg)

    order_data = purchase_order.model_dump()
    order_data["confidence_scores"] = updated_scores
    updated_order = PurchaseOrder(**order_data)

    return updated_order, updated_segments


def run_pipeline(
    image: Union[Image.Image, bytes],
    api_key: str,
    step1_model: str = "gemini-2.5-pro",
    step2_model: str = "gemini-2.5-flash",
    enable_calculator: bool = True,
    mime_type: str = "image/png",
) -> PipelineResult:
    """発注書画像から構造化データを抽出するパイプライン。

    Args:
        image: PIL.Image.Image または画像 bytes
        api_key: Gemini API キー
        step1_model: Step 1 で使用するモデル名
        step2_model: Step 2 で使用するモデル名
        enable_calculator: True のとき金額バリデーション・補完を実行
        mime_type: bytes 入力時の MIME タイプ

    Returns:
        PipelineResult（構造化データ + セグメント + 処理時間）
    """
    start_ms = int(time.time() * 1000)

    client = genai.Client(api_key=api_key)

    # Step 1: OCR + 構造化抽出
    order = extract_purchase_order(
        client=client,
        image=image,
        mime_type=mime_type,
        model=step1_model,
    )

    # Step 2: セグメンテーション + 検証（失敗してもグレースフルデグラデーション）
    try:
        segments = extract_segments(
            client=client,
            image=image,
            order=order,
            mime_type=mime_type,
            model=step2_model,
        )
    except Exception:
        segments = []

    # 信頼度マージ（Step 1 × Step 2）
    if segments:
        order, segments = merge_confidence(order, segments)

    # Step 3: 金額バリデーション・補完
    if enable_calculator:
        order = validate_and_complete(order)

    end_ms = int(time.time() * 1000)

    return PipelineResult(
        purchase_order=order,
        segments=segments,
        processing_time_ms=end_ms - start_ms,
        step1_model=step1_model,
        step2_model=step2_model,
    )
