"""Shared test fixtures."""

import pytest
from PIL import Image

from ocr.models import FieldSegment, OrderItem, PurchaseOrder


@pytest.fixture
def make_item():
    """Factory for OrderItem with sensible defaults."""

    def _make(
        *,
        item_number: str | None = None,
        description: str | None = None,
        quantity: float | None = None,
        unit: str | None = None,
        unit_price: float | None = None,
        amount: float | None = None,
    ) -> OrderItem:
        return OrderItem(
            item_number=item_number,
            description=description,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            amount=amount,
        )

    return _make


@pytest.fixture
def dummy_image() -> Image.Image:
    """テスト用の 100x100 白画像を返す。"""
    return Image.new("RGB", (100, 100), color=(255, 255, 255))


@pytest.fixture
def sample_order() -> PurchaseOrder:
    """サンプル PurchaseOrder を返す。Step 1 の出力を模擬。"""
    return PurchaseOrder(
        order_number="PO-001",
        order_date="2024-03-15",
        orderer=None,
        items=[
            OrderItem(
                item_number="A-01",
                description="製品A",
                quantity=100,
                unit="個",
                unit_price=500,
                amount=50000,
            ),
        ],
        subtotal=50000,
        tax_amount=5000,
        total_amount=55000,
        confidence_scores={
            "order_number": "high",
            "order_date": "high",
            "items.0.description": "medium",
            "items.0.quantity": "high",
            "items.0.unit_price": "high",
            "items.0.amount": "high",
            "subtotal": "high",
            "tax_amount": "high",
            "total_amount": "high",
        },
    )


@pytest.fixture
def sample_segments() -> list[FieldSegment]:
    """サンプル list[FieldSegment] を返す。Step 2 の出力を模擬。"""
    return [
        FieldSegment(
            field_name="order_number",
            box_2d=[50, 100, 100, 300],
            ocr_text="PO-001",
            verified=True,
            confidence="high",
        ),
        FieldSegment(
            field_name="order_date",
            box_2d=[50, 400, 100, 600],
            ocr_text="2024-03-15",
            verified=True,
            confidence="high",
        ),
        FieldSegment(
            field_name="items.0.description",
            box_2d=[200, 100, 250, 400],
            ocr_text="製品A",
            verified=True,
            confidence="medium",
        ),
    ]


@pytest.fixture
def make_order():
    """Factory for PurchaseOrder with minimal required fields."""

    def _make(
        *,
        items: list[OrderItem] | None = None,
        subtotal: float | None = None,
        tax_amount: float | None = None,
        total_amount: float | None = None,
        confidence_scores: dict[str, str] | None = None,
        **kwargs,
    ) -> PurchaseOrder:
        return PurchaseOrder(
            items=items or [],
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            confidence_scores=confidence_scores or {},
            **kwargs,
        )

    return _make
