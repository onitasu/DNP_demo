"""Tests for ocr/models.py -- TDD RED phase.

ocr/models.py does not exist yet. All tests should fail with ImportError.
"""

import pytest
from pydantic import ValidationError

from ocr.models import (
    FieldSegment,
    OrderItem,
    Orderer,
    PipelineResult,
    PurchaseOrder,
)


# ---------------------------------------------------------------------------
# 1. ConfidenceLevel
# ---------------------------------------------------------------------------
class TestConfidenceLevel:
    """ConfidenceLevel is Literal["high", "medium", "low"]."""

    @pytest.mark.parametrize("value", ["high", "medium", "low"])
    def test_valid_values(self, value: str) -> None:
        """Valid confidence levels should be accepted in a FieldSegment."""
        segment = FieldSegment(
            field_name="order_number",
            box_2d=[0, 0, 100, 100],
            verified=True,
            confidence=value,
        )
        assert segment.confidence == value

    def test_invalid_value_rejected(self) -> None:
        """An invalid confidence level should raise ValidationError."""
        with pytest.raises(ValidationError):
            FieldSegment(
                field_name="order_number",
                box_2d=[0, 0, 100, 100],
                verified=True,
                confidence="invalid",
            )


# ---------------------------------------------------------------------------
# 2. Orderer
# ---------------------------------------------------------------------------
class TestOrderer:
    """Orderer: all fields Optional, no default values required."""

    def test_all_fields_omitted(self) -> None:
        """Orderer can be instantiated with no arguments."""
        orderer = Orderer()
        assert orderer.company_name is None
        assert orderer.department is None
        assert orderer.contact_person is None
        assert orderer.address is None
        assert orderer.phone is None
        assert orderer.fax is None
        assert orderer.email is None

    def test_company_name_stored(self) -> None:
        orderer = Orderer(company_name="株式会社テスト")
        assert orderer.company_name == "株式会社テスト"

    def test_all_fields_populated(self) -> None:
        orderer = Orderer(
            company_name="ABC Corp",
            department="営業部",
            contact_person="山田太郎",
            address="東京都千代田区1-1-1",
            phone="03-1234-5678",
            fax="03-1234-5679",
            email="yamada@example.com",
        )
        assert orderer.company_name == "ABC Corp"
        assert orderer.department == "営業部"
        assert orderer.contact_person == "山田太郎"
        assert orderer.address == "東京都千代田区1-1-1"
        assert orderer.phone == "03-1234-5678"
        assert orderer.fax == "03-1234-5679"
        assert orderer.email == "yamada@example.com"


# ---------------------------------------------------------------------------
# 3. OrderItem
# ---------------------------------------------------------------------------
class TestOrderItem:
    """OrderItem: all fields Optional. Numeric fields are float."""

    def test_all_fields_omitted(self) -> None:
        item = OrderItem()
        assert item.item_number is None
        assert item.description is None
        assert item.quantity is None
        assert item.unit is None
        assert item.unit_price is None
        assert item.amount is None

    def test_numeric_fields_stored_as_float(self) -> None:
        item = OrderItem(quantity=10.5, unit_price=200.0, amount=2100.0)
        assert item.quantity == 10.5
        assert item.unit_price == 200.0
        assert item.amount == 2100.0

    def test_int_input_coerced_to_float(self) -> None:
        """int values should be accepted and stored as float."""
        item = OrderItem(quantity=100, unit_price=500, amount=50000)
        assert isinstance(item.quantity, float)
        assert isinstance(item.unit_price, float)
        assert isinstance(item.amount, float)
        assert item.quantity == 100.0
        assert item.unit_price == 500.0
        assert item.amount == 50000.0

    def test_string_fields(self) -> None:
        item = OrderItem(item_number="A-001", description="製品A", unit="個")
        assert item.item_number == "A-001"
        assert item.description == "製品A"
        assert item.unit == "個"


# ---------------------------------------------------------------------------
# 4. PurchaseOrder
# ---------------------------------------------------------------------------
class TestPurchaseOrder:
    """PurchaseOrder: items and confidence_scores are required."""

    def test_minimal_valid_instance(self) -> None:
        """Empty items list and empty confidence_scores should be valid."""
        order = PurchaseOrder(items=[], confidence_scores={})
        assert order.items == []
        assert order.confidence_scores == {}
        assert order.order_number is None
        assert order.order_date is None
        assert order.delivery_date is None
        assert order.orderer is None
        assert order.subtotal is None
        assert order.tax_amount is None
        assert order.total_amount is None
        assert order.payment_terms is None
        assert order.delivery_address is None
        assert order.notes is None

    def test_confidence_scores_valid_values(self) -> None:
        order = PurchaseOrder(
            items=[],
            confidence_scores={"order_number": "high", "subtotal": "medium"},
        )
        assert order.confidence_scores["order_number"] == "high"
        assert order.confidence_scores["subtotal"] == "medium"

    def test_confidence_scores_invalid_value_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseOrder(
                items=[],
                confidence_scores={"order_number": "invalid"},
            )

    def test_multiple_items(self) -> None:
        items = [
            OrderItem(description="製品A", quantity=10, unit_price=100, amount=1000),
            OrderItem(description="製品B", quantity=5, unit_price=200, amount=1000),
        ]
        order = PurchaseOrder(items=items, confidence_scores={})
        assert len(order.items) == 2
        assert order.items[0].description == "製品A"
        assert order.items[1].description == "製品B"

    def test_nested_orderer(self) -> None:
        orderer = Orderer(company_name="テスト株式会社", contact_person="田中一郎")
        order = PurchaseOrder(
            items=[],
            confidence_scores={},
            orderer=orderer,
        )
        assert order.orderer is not None
        assert order.orderer.company_name == "テスト株式会社"
        assert order.orderer.contact_person == "田中一郎"

    def test_dot_notation_keys_in_confidence_scores(self) -> None:
        """Dot-notation keys for nested and indexed fields should work."""
        scores = {
            "order_number": "high",
            "orderer.company_name": "medium",
            "items.0.amount": "low",
            "items.1.description": "high",
        }
        order = PurchaseOrder(items=[], confidence_scores=scores)
        assert order.confidence_scores["orderer.company_name"] == "medium"
        assert order.confidence_scores["items.0.amount"] == "low"

    def test_items_required(self) -> None:
        """Omitting items should raise ValidationError."""
        with pytest.raises(ValidationError):
            PurchaseOrder(confidence_scores={})

    def test_confidence_scores_required(self) -> None:
        """Omitting confidence_scores should raise ValidationError."""
        with pytest.raises(ValidationError):
            PurchaseOrder(items=[])

    def test_full_instance(self) -> None:
        """A fully populated PurchaseOrder should be valid."""
        order = PurchaseOrder(
            order_number="PO-2024-001",
            order_date="2024年3月15日",
            delivery_date="2024年4月1日",
            orderer=Orderer(company_name="発注元株式会社"),
            items=[
                OrderItem(
                    item_number="A-001",
                    description="部品A",
                    quantity=100,
                    unit="個",
                    unit_price=500,
                    amount=50000,
                ),
            ],
            subtotal=50000.0,
            tax_amount=5000.0,
            total_amount=55000.0,
            payment_terms="月末締め翌月末払い",
            delivery_address="東京都港区1-2-3",
            notes="至急対応願います",
            confidence_scores={
                "order_number": "high",
                "order_date": "high",
                "orderer.company_name": "medium",
                "items.0.amount": "high",
                "subtotal": "high",
                "tax_amount": "medium",
                "total_amount": "high",
            },
        )
        assert order.order_number == "PO-2024-001"
        assert order.subtotal == 50000.0
        assert len(order.items) == 1
        assert order.confidence_scores["tax_amount"] == "medium"


# ---------------------------------------------------------------------------
# 5. FieldSegment
# ---------------------------------------------------------------------------
class TestFieldSegment:
    """FieldSegment: field_name, box_2d, verified, confidence are required."""

    def test_valid_instance(self) -> None:
        seg = FieldSegment(
            field_name="order_number",
            box_2d=[100, 200, 300, 400],
            verified=True,
            confidence="high",
        )
        assert seg.field_name == "order_number"
        assert seg.box_2d == [100, 200, 300, 400]
        assert seg.verified is True
        assert seg.confidence == "high"
        assert seg.ocr_text is None

    def test_with_ocr_text(self) -> None:
        seg = FieldSegment(
            field_name="orderer.company_name",
            box_2d=[50, 60, 150, 300],
            ocr_text="株式会社テスト",
            verified=True,
            confidence="medium",
        )
        assert seg.ocr_text == "株式会社テスト"

    def test_field_name_required(self) -> None:
        with pytest.raises(ValidationError):
            FieldSegment(
                box_2d=[0, 0, 100, 100],
                verified=True,
                confidence="high",
            )

    def test_box_2d_required(self) -> None:
        with pytest.raises(ValidationError):
            FieldSegment(
                field_name="order_number",
                verified=True,
                confidence="high",
            )

    def test_verified_required(self) -> None:
        with pytest.raises(ValidationError):
            FieldSegment(
                field_name="order_number",
                box_2d=[0, 0, 100, 100],
                confidence="high",
            )

    def test_confidence_required(self) -> None:
        with pytest.raises(ValidationError):
            FieldSegment(
                field_name="order_number",
                box_2d=[0, 0, 100, 100],
                verified=True,
            )

    def test_ocr_text_optional(self) -> None:
        """ocr_text can be omitted without error."""
        seg = FieldSegment(
            field_name="subtotal",
            box_2d=[500, 600, 700, 800],
            verified=False,
            confidence="low",
        )
        assert seg.ocr_text is None


# ---------------------------------------------------------------------------
# 6. PipelineResult
# ---------------------------------------------------------------------------
class TestPipelineResult:
    """PipelineResult: all fields required."""

    def test_full_instance(self) -> None:
        order = PurchaseOrder(
            items=[OrderItem(description="テスト品")],
            confidence_scores={"items.0.description": "high"},
        )
        segment = FieldSegment(
            field_name="items.0.description",
            box_2d=[100, 100, 200, 200],
            ocr_text="テスト品",
            verified=True,
            confidence="high",
        )
        result = PipelineResult(
            purchase_order=order,
            segments=[segment],
            processing_time_ms=4500,
            step1_model="gemini-2.5-pro",
            step2_model="gemini-2.5-flash",
        )
        assert result.purchase_order.items[0].description == "テスト品"
        assert len(result.segments) == 1
        assert result.processing_time_ms == 4500
        assert result.step1_model == "gemini-2.5-pro"
        assert result.step2_model == "gemini-2.5-flash"

    def test_empty_segments(self) -> None:
        order = PurchaseOrder(items=[], confidence_scores={})
        result = PipelineResult(
            purchase_order=order,
            segments=[],
            processing_time_ms=1000,
            step1_model="gemini-2.5-pro",
            step2_model="gemini-2.5-flash",
        )
        assert result.segments == []

    def test_purchase_order_required(self) -> None:
        with pytest.raises(ValidationError):
            PipelineResult(
                segments=[],
                processing_time_ms=1000,
                step1_model="gemini-2.5-pro",
                step2_model="gemini-2.5-flash",
            )

    def test_segments_required(self) -> None:
        with pytest.raises(ValidationError):
            PipelineResult(
                purchase_order=PurchaseOrder(items=[], confidence_scores={}),
                processing_time_ms=1000,
                step1_model="gemini-2.5-pro",
                step2_model="gemini-2.5-flash",
            )

    def test_processing_time_ms_required(self) -> None:
        with pytest.raises(ValidationError):
            PipelineResult(
                purchase_order=PurchaseOrder(items=[], confidence_scores={}),
                segments=[],
                step1_model="gemini-2.5-pro",
                step2_model="gemini-2.5-flash",
            )

    def test_step1_model_required(self) -> None:
        with pytest.raises(ValidationError):
            PipelineResult(
                purchase_order=PurchaseOrder(items=[], confidence_scores={}),
                segments=[],
                processing_time_ms=1000,
                step2_model="gemini-2.5-flash",
            )

    def test_step2_model_required(self) -> None:
        with pytest.raises(ValidationError):
            PipelineResult(
                purchase_order=PurchaseOrder(items=[], confidence_scores={}),
                segments=[],
                processing_time_ms=1000,
                step1_model="gemini-2.5-pro",
            )
