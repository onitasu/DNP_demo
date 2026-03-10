"""Tests for tabular result view helpers."""

from ocr.models import FieldSegment, PurchaseOrder
from ocr.result_table import build_result_rows


class TestBuildResultRows:
    def test_builds_rows_with_segment_metadata(
        self,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        rows = build_result_rows(sample_order, sample_segments)

        order_number_row = next(
            row for row in rows if row["field_key"] == "order_number"
        )

        assert order_number_row["section"] == "発注基本情報"
        assert order_number_row["label"] == "発注番号"
        assert order_number_row["value"] == "PO-001"
        assert order_number_row["confidence"] == "high"
        assert order_number_row["confidence_label"] == "OK"
        assert order_number_row["verified"] == "一致"
        assert order_number_row["ocr_text"] == "PO-001"

    def test_marks_missing_segment_as_not_detected(
        self,
        sample_order: PurchaseOrder,
    ) -> None:
        rows = build_result_rows(sample_order, [])

        subtotal_row = next(row for row in rows if row["field_key"] == "subtotal")

        assert subtotal_row["verified"] == "未検出"
        assert subtotal_row["ocr_text"] == "—"

    def test_includes_item_rows_with_stable_order(
        self,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        rows = build_result_rows(sample_order, sample_segments)
        keys = [row["field_key"] for row in rows]

        assert keys.index("items.0.description") < keys.index("items.0.quantity")
        assert keys.index("items.0.quantity") < keys.index("items.0.amount")
