"""Gemini API クライアント。構造化出力 + セグメンテーションの2段階呼び出しを担当。"""

from __future__ import annotations

import re
import time
from typing import Any, Union

from PIL import Image
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, TypeAdapter

from ocr.models import FieldSegment, PurchaseOrder
from ocr.prompts import (
    build_ocr_prompt,
    build_segmentation_prompt,
    build_segmentation_system_instruction,
)

# リトライ設定
_RETRY_STATUS_CODES = {429, 500, 503}
_RETRY_DELAYS = [1.0, 3.0, 6.0]
_SUPPORTED_RESPONSE_JSON_SCHEMA_KEYS = {
    "$anchor",
    "$defs",
    "$id",
    "$ref",
    "additionalProperties",
    "anyOf",
    "description",
    "enum",
    "format",
    "items",
    "maxItems",
    "maximum",
    "minItems",
    "minimum",
    "oneOf",
    "prefixItems",
    "properties",
    "propertyOrdering",
    "required",
    "title",
    "type",
}
_PURCHASE_ORDER_ADAPTER = TypeAdapter(PurchaseOrder)
_FIELD_SEGMENTS_ADAPTER = TypeAdapter(list[FieldSegment])


def _build_response_json_schema(schema_type: type[BaseModel] | Any) -> dict[str, Any]:
    """Gemini response_json_schema 互換の JSON Schema を返す。"""
    if isinstance(schema_type, type) and issubclass(schema_type, BaseModel):
        raw_schema = schema_type.model_json_schema()
    else:
        raw_schema = TypeAdapter(schema_type).json_schema()
    return _sanitize_response_json_schema(raw_schema)


def _sanitize_response_json_schema(node: Any) -> Any:
    """Pydantic の JSON Schema を Gemini のサブセットへ整形する。"""
    if isinstance(node, dict):
        sanitized: dict[str, Any] = {}
        for key, value in node.items():
            if key not in _SUPPORTED_RESPONSE_JSON_SCHEMA_KEYS:
                continue
            if key in {"$defs", "properties"}:
                sanitized[key] = {
                    name: _sanitize_response_json_schema(child)
                    for name, child in value.items()
                }
                continue
            if key in {"anyOf", "oneOf", "prefixItems"}:
                sanitized[key] = [
                    _sanitize_response_json_schema(item) for item in value
                ]
                continue
            if key in {"additionalProperties", "items"} and isinstance(value, dict):
                sanitized[key] = _sanitize_response_json_schema(value)
                continue
            sanitized[key] = value

        if "properties" in sanitized and "propertyOrdering" not in sanitized:
            sanitized["propertyOrdering"] = list(sanitized["properties"].keys())

        return sanitized

    if isinstance(node, list):
        return [_sanitize_response_json_schema(item) for item in node]

    return node


def _extract_json_text(response: Any) -> str:
    """Gemini 応答から JSON テキストを抽出する。"""
    text = (response.text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    return re.sub(r"\s*```$", "", text)


def _parse_json_response(response: Any, adapter: TypeAdapter[Any]) -> Any:
    """Gemini の JSON 応答を Pydantic で検証して返す。"""
    text = _extract_json_text(response)
    if text:
        return adapter.validate_json(text)
    if response.parsed is not None:
        return adapter.validate_python(response.parsed)
    raise ValueError("Gemini response did not contain JSON output.")


_PURCHASE_ORDER_RESPONSE_JSON_SCHEMA = _build_response_json_schema(PurchaseOrder)
_FIELD_SEGMENTS_RESPONSE_JSON_SCHEMA = _build_response_json_schema(list[FieldSegment])


def _build_thinking_config(model: str) -> types.ThinkingConfig | None:
    """モデルに応じた thinking_config を返す。"""
    if "gemini-2.5-flash" in model:
        return types.ThinkingConfig(thinking_budget=0)
    # gemini-3.x は thinking_level を使う（thinking_budget は非推奨）
    if "gemini-3" in model:
        return None  # 3.x では省略（デフォルト動作）
    # gemini-2.5-pro などは thinking_config を省略
    return None


def _call_with_retry(
    client: genai.Client,
    model: str,
    contents: list,
    config: types.GenerateContentConfig,
    max_retries: int = 3,
):
    """リトライ付きで generate_content を呼ぶ。"""
    delays = _RETRY_DELAYS[:max_retries]
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except genai_errors.ClientError as e:
            last_error = e
            if e.code == 429 and attempt < max_retries:
                wait = delays[min(attempt, len(delays) - 1)]
                time.sleep(wait)
                continue
            raise
        except genai_errors.ServerError as e:
            last_error = e
            if e.code in (500, 503) and attempt < max_retries:
                wait = delays[min(attempt, len(delays) - 1)]
                time.sleep(wait)
                continue
            raise

    raise last_error  # type: ignore[misc]


def extract_purchase_order(
    client: genai.Client,
    image: Union[Image.Image, bytes],
    mime_type: str = "image/png",
    model: str = "gemini-2.5-pro",
) -> PurchaseOrder:
    """Step 1: 発注書画像から構造化データを抽出する。

    Args:
        client: genai.Client インスタンス
        image: PIL.Image.Image または画像 bytes
        mime_type: bytes を渡す場合の MIME タイプ
        model: 使用するモデル名

    Returns:
        PurchaseOrder インスタンス（confidence_scores 含む）
    """
    if isinstance(image, bytes):
        image_part = types.Part.from_bytes(data=image, mime_type=mime_type)
    else:
        image_part = image

    prompt = build_ocr_prompt()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=_PURCHASE_ORDER_RESPONSE_JSON_SCHEMA,
    )

    response = _call_with_retry(
        client=client,
        model=model,
        contents=[image_part, prompt],
        config=config,
    )

    return _parse_json_response(response, _PURCHASE_ORDER_ADAPTER)


def extract_segments(
    client: genai.Client,
    image: Union[Image.Image, bytes],
    order: PurchaseOrder,
    mime_type: str = "image/png",
    model: str = "gemini-2.5-flash",
) -> list[FieldSegment]:
    """Step 2: セグメンテーション + 検証を行う。

    Args:
        client: genai.Client インスタンス
        image: PIL.Image.Image または画像 bytes
        order: Step 1 で抽出した PurchaseOrder
        mime_type: bytes を渡す場合の MIME タイプ
        model: 使用するモデル名

    Returns:
        list[FieldSegment]（box_2d + verified + confidence 含む）
    """
    if isinstance(image, bytes):
        image_part = types.Part.from_bytes(data=image, mime_type=mime_type)
    else:
        image_part = image

    system_instruction = build_segmentation_system_instruction()
    prompt = build_segmentation_prompt(order)

    thinking_config = _build_thinking_config(model)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_json_schema=_FIELD_SEGMENTS_RESPONSE_JSON_SCHEMA,
        **({"thinking_config": thinking_config} if thinking_config is not None else {}),
    )

    response = _call_with_retry(
        client=client,
        model=model,
        contents=[image_part, prompt],
        config=config,
    )

    return _parse_json_response(response, _FIELD_SEGMENTS_ADAPTER)
