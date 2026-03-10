"""Tests for Gemini client configuration and JSON parsing."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ocr.llm_client import extract_purchase_order, extract_segments
from ocr.models import FieldSegment, PurchaseOrder


def _schema_contains_key(node: object, key: str) -> bool:
    if isinstance(node, dict):
        if key in node:
            return True
        return any(_schema_contains_key(value, key) for value in node.values())
    if isinstance(node, list):
        return any(_schema_contains_key(value, key) for value in node)
    return False


class TestExtractPurchaseOrder:
    def test_uses_response_json_schema_for_purchase_order(
        self,
        dummy_image,
        sample_order: PurchaseOrder,
    ) -> None:
        response = SimpleNamespace(
            text=sample_order.model_dump_json(),
            parsed=None,
        )

        with patch("ocr.llm_client._call_with_retry", return_value=response) as call:
            result = extract_purchase_order(
                client=MagicMock(),
                image=dummy_image,
            )

        config = call.call_args.kwargs["config"]
        schema = config.response_json_schema

        assert config.response_schema is None
        assert schema is not None
        assert schema["type"] == "object"
        assert schema["properties"]["confidence_scores"]["additionalProperties"][
            "enum"
        ] == ["high", "medium", "low"]
        assert not _schema_contains_key(schema, "default")
        assert result == sample_order


class TestExtractSegments:
    def test_uses_response_json_schema_for_segments(
        self,
        dummy_image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        response = SimpleNamespace(
            text=json.dumps([segment.model_dump() for segment in sample_segments]),
            parsed=None,
        )

        with patch("ocr.llm_client._call_with_retry", return_value=response) as call:
            result = extract_segments(
                client=MagicMock(),
                image=dummy_image,
                order=sample_order,
            )

        config = call.call_args.kwargs["config"]
        schema = config.response_json_schema

        assert config.response_schema is None
        assert schema is not None
        assert schema["type"] == "array"
        assert config.thinking_config is not None
        assert config.thinking_config.thinking_budget == 0
        assert not _schema_contains_key(schema, "default")
        assert result == sample_segments
