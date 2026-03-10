from typing import Optional

from ocr.models import ConfidenceLevel, OrderItem, PurchaseOrder

AMOUNT_TOLERANCE_RATIO = 0.01
AMOUNT_TOLERANCE_MIN = 1.0


def _tolerance(expected: float) -> float:
    return max(abs(expected) * AMOUNT_TOLERANCE_RATIO, AMOUNT_TOLERANCE_MIN)


def _is_within_tolerance(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= _tolerance(expected)


def _validate_and_complete_items(
    items: list[OrderItem],
    confidence_scores: dict[str, ConfidenceLevel],
    index: int,
) -> tuple[OrderItem, dict[str, ConfidenceLevel]]:
    q = items[index].quantity
    p = items[index].unit_price
    a = items[index].amount
    scores = dict(confidence_scores)
    item_data = items[index].model_dump()

    q_key = f"items.{index}.quantity"
    p_key = f"items.{index}.unit_price"
    a_key = f"items.{index}.amount"

    non_none = sum(v is not None for v in [q, p, a])

    if non_none == 3:
        # Rule A: validate
        expected = q * p  # type: ignore[operator]
        if not _is_within_tolerance(a, expected):  # type: ignore[arg-type]
            scores[q_key] = "low"
            scores[p_key] = "low"
            scores[a_key] = "low"
    elif non_none == 2:
        # Rule B: complete
        if q is not None and p is not None and a is None:
            item_data["amount"] = q * p
            scores[a_key] = "medium"
        elif q is not None and a is not None and p is None:
            item_data["unit_price"] = a / q
            scores[p_key] = "medium"
        elif p is not None and a is not None and q is None:
            item_data["quantity"] = a / p
            scores[q_key] = "medium"
    # Rule C: non_none <= 1 → do nothing

    return OrderItem(**item_data), scores


def validate_and_complete(order: PurchaseOrder) -> PurchaseOrder:
    """金額バリデーション・補完を行い、更新された PurchaseOrder を返す。"""
    scores: dict[str, ConfidenceLevel] = dict(order.confidence_scores)
    items = list(order.items)

    # Step 1: 品目明細（Rules A / B / C）
    new_items: list[OrderItem] = []
    for i, item in enumerate(items):
        updated_item, scores = _validate_and_complete_items(items, scores, i)
        new_items.append(updated_item)

    # Step 2: 小計（Rules D / E）
    item_amounts = [item.amount for item in new_items if item.amount is not None]
    expected_subtotal: Optional[float] = sum(item_amounts) if item_amounts else None

    subtotal = order.subtotal
    if subtotal is not None and expected_subtotal is not None:
        # Rule D: validate
        if not _is_within_tolerance(subtotal, expected_subtotal):
            scores["subtotal"] = "low"
    elif subtotal is None and expected_subtotal is not None:
        # Rule E: complete
        subtotal = expected_subtotal
        scores["subtotal"] = "medium"

    # Step 3: 合計（Rules F / G / H）
    tax = order.tax_amount
    total = order.total_amount

    present = [v for v in [subtotal, tax, total] if v is not None]
    if len(present) == 3:
        # Rule F: validate
        expected_total = subtotal + tax  # type: ignore[operator]
        if not _is_within_tolerance(total, expected_total):  # type: ignore[arg-type]
            scores["subtotal"] = "low"
            scores["tax_amount"] = "low"
            scores["total_amount"] = "low"
    elif len(present) == 2:
        # Rule G: complete
        if subtotal is not None and tax is not None and total is None:
            total = subtotal + tax
            scores["total_amount"] = "medium"
        elif subtotal is not None and total is not None and tax is None:
            tax = total - subtotal
            scores["tax_amount"] = "medium"
        elif tax is not None and total is not None and subtotal is None:
            subtotal = total - tax
            scores["subtotal"] = "medium"
    # Rule H: len(present) <= 1 → do nothing

    order_data = order.model_dump()
    order_data["items"] = [item.model_dump() for item in new_items]
    order_data["subtotal"] = subtotal
    order_data["tax_amount"] = tax
    order_data["total_amount"] = total
    order_data["confidence_scores"] = scores

    return PurchaseOrder(**order_data)
