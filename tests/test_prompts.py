"""Tests for ocr/prompts.py — RED phase.

ocr/prompts.py does not exist yet. All tests should FAIL on import.
"""

import pytest

from ocr.models import OrderItem, Orderer, PurchaseOrder
from ocr.prompts import (
    build_ocr_prompt,
    build_segmentation_prompt,
    build_segmentation_system_instruction,
)


# ---------------------------------------------------------------------------
# build_ocr_prompt
# ---------------------------------------------------------------------------
class TestBuildOcrPrompt:
    """Step 1 OCR prompt generation."""

    def test_returns_nonempty_string(self):
        result = build_ocr_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_purchase_order_keyword(self):
        result = build_ocr_prompt()
        assert "発注書" in result

    def test_contains_ocr_or_extraction_keyword(self):
        result = build_ocr_prompt()
        assert "OCR" in result or "抽出" in result

    def test_contains_confidence_levels(self):
        result = build_ocr_prompt()
        assert "high" in result
        assert "medium" in result
        assert "low" in result

    def test_contains_language_instruction(self):
        result = build_ocr_prompt()
        assert "原文" in result or "日本語" in result

    def test_idempotent(self):
        """Calling multiple times returns the same result."""
        first = build_ocr_prompt()
        second = build_ocr_prompt()
        assert first == second


# ---------------------------------------------------------------------------
# build_segmentation_system_instruction
# ---------------------------------------------------------------------------
class TestBuildSegmentationSystemInstruction:
    """Step 2 system instruction for segmentation."""

    def test_returns_nonempty_string(self):
        result = build_segmentation_system_instruction()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_box_2d(self):
        result = build_segmentation_system_instruction()
        assert "box_2d" in result

    def test_prohibits_masks(self):
        result = build_segmentation_system_instruction()
        lower = result.lower()
        assert "never return masks" in lower or "mask" in lower

    def test_contains_coordinate_system(self):
        result = build_segmentation_system_instruction()
        assert "y_min" in result or "0-1000" in result


# ---------------------------------------------------------------------------
# build_segmentation_prompt
# ---------------------------------------------------------------------------
class TestBuildSegmentationPrompt:
    """Step 2 user prompt that embeds Step 1 extraction results."""

    @pytest.fixture
    def sample_order(self) -> PurchaseOrder:
        """A PurchaseOrder with representative field values."""
        return PurchaseOrder(
            order_number="PO-2024-001",
            order_date="2024年3月15日",
            delivery_date="2024年4月15日",
            orderer=Orderer(
                company_name="テスト株式会社",
                department="購買部",
                contact_person="山田太郎",
            ),
            items=[
                OrderItem(
                    item_number="A-001",
                    description="テスト製品A",
                    quantity=100,
                    unit="個",
                    unit_price=500,
                    amount=50000,
                ),
                OrderItem(
                    item_number="B-002",
                    description="テスト製品B",
                    quantity=50,
                    unit="本",
                    unit_price=1000,
                    amount=50000,
                ),
            ],
            subtotal=100000,
            tax_amount=10000,
            total_amount=110000,
            confidence_scores={
                "order_number": "high",
                "orderer.company_name": "high",
                "items.0.description": "medium",
                "items.1.description": "low",
            },
        )

    @pytest.fixture
    def minimal_order(self) -> PurchaseOrder:
        """A PurchaseOrder with only required fields (empty items, no optional)."""
        return PurchaseOrder(
            items=[],
            confidence_scores={},
        )

    @pytest.fixture
    def order_with_nones(self) -> PurchaseOrder:
        """A PurchaseOrder where most optional fields are None."""
        return PurchaseOrder(
            order_number="PO-999",
            orderer=Orderer(company_name="株式会社なし商事"),
            items=[
                OrderItem(description="品目のみ"),
            ],
            confidence_scores={"order_number": "high"},
        )

    def test_contains_order_number(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert "PO-2024-001" in result

    def test_contains_company_name(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert "テスト株式会社" in result

    def test_contains_item_description(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert "テスト製品A" in result
        assert "テスト製品B" in result

    def test_contains_bounding_box_reference(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert "バウンディングボックス" in result or "box_2d" in result

    def test_contains_verification_instruction(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert "verified" in result or "一致" in result

    def test_contains_notation_variation_instruction(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        lower = result.lower()
        assert "表記揺れ" in result or "true" in lower or "false" in lower

    def test_handles_none_fields_without_error(self, order_with_nones: PurchaseOrder):
        """None optional fields should not cause exceptions."""
        result = build_segmentation_prompt(order_with_nones)
        assert isinstance(result, str)
        assert len(result) > 0
        # The present fields should still appear
        assert "PO-999" in result
        assert "株式会社なし商事" in result

    def test_handles_empty_items_without_error(self, minimal_order: PurchaseOrder):
        """An order with zero items should not raise."""
        result = build_segmentation_prompt(minimal_order)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self, sample_order: PurchaseOrder):
        result = build_segmentation_prompt(sample_order)
        assert isinstance(result, str)
