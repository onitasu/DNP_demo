"""Tests for ocr.calculator — TDD RED phase.

ocr/calculator.py does not exist yet. All tests should fail with ImportError.
"""

import copy

from ocr.calculator import validate_and_complete


# ---------------------------------------------------------------------------
# Rule A: Item validation — all 3 values present
# ---------------------------------------------------------------------------


class TestRuleA_ItemValidation:
    """quantity * unit_price == amount check (with tolerance)."""

    def test_item_consistent_no_confidence_change(self, make_order, make_item):
        """qty=100, price=500, amount=50000 -> confidence unchanged."""
        item = make_item(quantity=100, unit_price=500, amount=50000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "high"
        assert result.confidence_scores["items.0.unit_price"] == "high"
        assert result.confidence_scores["items.0.amount"] == "high"

    def test_item_inconsistent_all_low(self, make_order, make_item):
        """qty=100, price=500, amount=60000 -> all 3 fields low."""
        item = make_item(quantity=100, unit_price=500, amount=60000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "low"
        assert result.confidence_scores["items.0.unit_price"] == "low"
        assert result.confidence_scores["items.0.amount"] == "low"

    def test_item_within_tolerance(self, make_order, make_item):
        """qty=3, price=333, amount=1000 -> consistent (999 vs 1000, 0.1% diff)."""
        item = make_item(quantity=3, unit_price=333, amount=1000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "high"
        assert result.confidence_scores["items.0.unit_price"] == "high"
        assert result.confidence_scores["items.0.amount"] == "high"

    def test_item_at_tolerance_boundary(self, make_order, make_item):
        """Exactly at 1% tolerance boundary -> consistent."""
        # expected = 100 * 100 = 10000, tolerance = max(10000*0.01, 1) = 100
        # amount = 10100 -> |10100 - 10000| = 100 == tolerance -> consistent
        item = make_item(quantity=100, unit_price=100, amount=10100)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "high"
        assert result.confidence_scores["items.0.unit_price"] == "high"
        assert result.confidence_scores["items.0.amount"] == "high"

    def test_item_just_over_tolerance(self, make_order, make_item):
        """Just over 1% tolerance -> inconsistent."""
        # expected = 100 * 100 = 10000, tolerance = 100
        # amount = 10101 -> |10101 - 10000| = 101 > 100 -> inconsistent
        item = make_item(quantity=100, unit_price=100, amount=10101)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "low"
        assert result.confidence_scores["items.0.unit_price"] == "low"
        assert result.confidence_scores["items.0.amount"] == "low"

    def test_multiple_items_independent(self, make_order, make_item):
        """Each item is validated independently."""
        item_ok = make_item(quantity=10, unit_price=100, amount=1000)
        item_bad = make_item(quantity=10, unit_price=100, amount=2000)
        order = make_order(
            items=[item_ok, item_bad],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
                "items.1.quantity": "high",
                "items.1.unit_price": "high",
                "items.1.amount": "high",
            },
        )

        result = validate_and_complete(order)

        # First item: consistent
        assert result.confidence_scores["items.0.quantity"] == "high"
        assert result.confidence_scores["items.0.amount"] == "high"
        # Second item: inconsistent
        assert result.confidence_scores["items.1.quantity"] == "low"
        assert result.confidence_scores["items.1.amount"] == "low"


# ---------------------------------------------------------------------------
# Rule B: Item completion — 2 of 3 values present
# ---------------------------------------------------------------------------


class TestRuleB_ItemCompletion:
    """Missing 1 of 3 item values -> compute and set confidence=medium."""

    def test_complete_missing_amount(self, make_order, make_item):
        """qty=100, price=500, amount=None -> amount=50000, confidence=medium."""
        item = make_item(quantity=100, unit_price=500)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.items[0].amount == 50000
        assert result.confidence_scores["items.0.amount"] == "medium"

    def test_complete_missing_unit_price(self, make_order, make_item):
        """qty=100, amount=50000, unit_price=None -> unit_price=500."""
        item = make_item(quantity=100, amount=50000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.items[0].unit_price == 500
        assert result.confidence_scores["items.0.unit_price"] == "medium"

    def test_complete_missing_quantity(self, make_order, make_item):
        """unit_price=500, amount=50000, quantity=None -> quantity=100."""
        item = make_item(unit_price=500, amount=50000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.unit_price": "high",
                "items.0.amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.items[0].quantity == 100
        assert result.confidence_scores["items.0.quantity"] == "medium"


# ---------------------------------------------------------------------------
# Rule C: Item — 1 value or less
# ---------------------------------------------------------------------------


class TestRuleC_ItemNoCompletion:
    """1 value or fewer -> no completion."""

    def test_only_quantity(self, make_order, make_item):
        """qty=100, others None -> no change."""
        item = make_item(quantity=100)
        order = make_order(
            items=[item],
            confidence_scores={"items.0.quantity": "high"},
        )

        result = validate_and_complete(order)

        assert result.items[0].unit_price is None
        assert result.items[0].amount is None

    def test_two_missing(self, make_order, make_item):
        """qty=100, price=None, amount=None -> no completion."""
        item = make_item(quantity=100)
        order = make_order(
            items=[item],
            confidence_scores={"items.0.quantity": "high"},
        )

        result = validate_and_complete(order)

        assert result.items[0].unit_price is None
        assert result.items[0].amount is None

    def test_all_none(self, make_order, make_item):
        """All three None -> no change."""
        item = make_item()
        order = make_order(items=[item], confidence_scores={})

        result = validate_and_complete(order)

        assert result.items[0].quantity is None
        assert result.items[0].unit_price is None
        assert result.items[0].amount is None

    def test_empty_items_list(self, make_order):
        """No items at all -> no error."""
        order = make_order(items=[], confidence_scores={})

        result = validate_and_complete(order)

        assert result.items == []


# ---------------------------------------------------------------------------
# Rule D: Subtotal validation — subtotal exists
# ---------------------------------------------------------------------------


class TestRuleD_SubtotalValidation:
    """subtotal vs sum(item.amount) check."""

    def test_subtotal_consistent(self, make_order, make_item):
        """items=[50000, 30000], subtotal=80000 -> no change."""
        items = [
            make_item(quantity=100, unit_price=500, amount=50000),
            make_item(quantity=100, unit_price=300, amount=30000),
        ]
        order = make_order(
            items=items,
            subtotal=80000,
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.0.amount": "high",
                "items.1.quantity": "high",
                "items.1.unit_price": "high",
                "items.1.amount": "high",
                "subtotal": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["subtotal"] == "high"

    def test_subtotal_inconsistent(self, make_order, make_item):
        """items=[50000, 30000], subtotal=90000 -> subtotal confidence=low."""
        items = [
            make_item(amount=50000),
            make_item(amount=30000),
        ]
        order = make_order(
            items=items,
            subtotal=90000,
            confidence_scores={"subtotal": "high"},
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["subtotal"] == "low"

    def test_subtotal_with_partial_item_amounts(self, make_order, make_item):
        """Some items have amount=None. Sum only non-None amounts."""
        items = [
            make_item(amount=50000),
            make_item(amount=None),  # skipped
            make_item(amount=30000),
        ]
        order = make_order(
            items=items,
            subtotal=80000,
            confidence_scores={"subtotal": "high"},
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["subtotal"] == "high"


# ---------------------------------------------------------------------------
# Rule E: Subtotal completion — subtotal missing
# ---------------------------------------------------------------------------


class TestRuleE_SubtotalCompletion:
    """subtotal=None + items have amounts -> compute subtotal."""

    def test_complete_subtotal(self, make_order, make_item):
        """subtotal=None, items have amounts -> subtotal = sum."""
        items = [
            make_item(amount=50000),
            make_item(amount=30000),
        ]
        order = make_order(
            items=items,
            confidence_scores={},
        )

        result = validate_and_complete(order)

        assert result.subtotal == 80000
        assert result.confidence_scores["subtotal"] == "medium"

    def test_no_completion_if_no_items_have_amount(self, make_order, make_item):
        """subtotal=None, all item amounts None -> no completion."""
        items = [make_item(quantity=10), make_item(quantity=20)]
        order = make_order(
            items=items,
            confidence_scores={},
        )

        result = validate_and_complete(order)

        assert result.subtotal is None


# ---------------------------------------------------------------------------
# Rule F: Total validation — all 3 total values present
# ---------------------------------------------------------------------------


class TestRuleF_TotalValidation:
    """subtotal + tax_amount == total_amount check."""

    def test_total_consistent(self, make_order):
        """subtotal + tax = total -> no change."""
        order = make_order(
            subtotal=80000,
            tax_amount=8000,
            total_amount=88000,
            confidence_scores={
                "subtotal": "high",
                "tax_amount": "high",
                "total_amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["subtotal"] == "high"
        assert result.confidence_scores["tax_amount"] == "high"
        assert result.confidence_scores["total_amount"] == "high"

    def test_total_inconsistent(self, make_order):
        """subtotal + tax != total -> all 3 low."""
        order = make_order(
            subtotal=80000,
            tax_amount=8000,
            total_amount=100000,
            confidence_scores={
                "subtotal": "high",
                "tax_amount": "high",
                "total_amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["subtotal"] == "low"
        assert result.confidence_scores["tax_amount"] == "low"
        assert result.confidence_scores["total_amount"] == "low"


# ---------------------------------------------------------------------------
# Rule G: Total completion — 2 of 3 values present
# ---------------------------------------------------------------------------


class TestRuleG_TotalCompletion:
    """Missing 1 of 3 total values -> compute and set confidence=medium."""

    def test_complete_missing_tax(self, make_order):
        """subtotal=80000, tax=None, total=88000 -> tax=8000, confidence=medium."""
        order = make_order(
            subtotal=80000,
            tax_amount=None,
            total_amount=88000,
            confidence_scores={
                "subtotal": "high",
                "total_amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.tax_amount == 8000
        assert result.confidence_scores["tax_amount"] == "medium"

    def test_complete_missing_subtotal(self, make_order):
        """subtotal=None, tax=8000, total=88000 -> subtotal=80000."""
        order = make_order(
            subtotal=None,
            tax_amount=8000,
            total_amount=88000,
            confidence_scores={
                "tax_amount": "high",
                "total_amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.subtotal == 80000
        assert result.confidence_scores["subtotal"] == "medium"

    def test_complete_missing_total(self, make_order):
        """subtotal=80000, tax=8000, total=None -> total=88000."""
        order = make_order(
            subtotal=80000,
            tax_amount=8000,
            total_amount=None,
            confidence_scores={
                "subtotal": "high",
                "tax_amount": "high",
            },
        )

        result = validate_and_complete(order)

        assert result.total_amount == 88000
        assert result.confidence_scores["total_amount"] == "medium"


# ---------------------------------------------------------------------------
# Rule H: Total — 1 value or less
# ---------------------------------------------------------------------------


class TestRuleH_TotalNoCompletion:
    """1 value or fewer -> no completion."""

    def test_all_none(self, make_order):
        """subtotal=None, tax=None, total=None -> no change."""
        order = make_order(
            subtotal=None,
            tax_amount=None,
            total_amount=None,
            confidence_scores={},
        )

        result = validate_and_complete(order)

        assert result.subtotal is None
        assert result.tax_amount is None
        assert result.total_amount is None

    def test_only_total(self, make_order):
        """Only total_amount present -> no completion."""
        order = make_order(
            total_amount=88000,
            confidence_scores={"total_amount": "high"},
        )

        result = validate_and_complete(order)

        assert result.subtotal is None
        assert result.tax_amount is None
        assert result.total_amount == 88000


# ---------------------------------------------------------------------------
# Execution order: item completion feeds into subtotal calculation
# ---------------------------------------------------------------------------


class TestExecutionOrder:
    """Items are completed before subtotal is computed."""

    def test_item_amount_completed_then_subtotal_computed(self, make_order, make_item):
        """Item amount is missing -> completed -> subtotal uses completed value."""
        items = [
            make_item(quantity=100, unit_price=500),  # amount=None -> 50000
            make_item(amount=30000),
        ]
        order = make_order(
            items=items,
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
                "items.1.amount": "high",
            },
        )

        result = validate_and_complete(order)

        # Item 0 amount should be completed
        assert result.items[0].amount == 50000
        # Subtotal should include the completed amount
        assert result.subtotal == 80000
        assert result.confidence_scores["subtotal"] == "medium"


# ---------------------------------------------------------------------------
# Confidence rules: only downgrade or set medium for computed values
# ---------------------------------------------------------------------------


class TestConfidenceRules:
    """Calculator never upgrades confidence to high."""

    def test_no_upgrade_to_high(self, make_order, make_item):
        """medium confidence is not upgraded to high by calculator."""
        item = make_item(quantity=100, unit_price=500, amount=50000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "medium",
                "items.0.unit_price": "medium",
                "items.0.amount": "medium",
            },
        )

        result = validate_and_complete(order)

        # Even though calculation is consistent, medium stays medium
        assert result.confidence_scores["items.0.quantity"] == "medium"
        assert result.confidence_scores["items.0.unit_price"] == "medium"
        assert result.confidence_scores["items.0.amount"] == "medium"

    def test_downgrade_from_medium_to_low(self, make_order, make_item):
        """medium confidence is downgraded to low on inconsistency."""
        item = make_item(quantity=100, unit_price=500, amount=60000)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "medium",
                "items.0.unit_price": "medium",
                "items.0.amount": "medium",
            },
        )

        result = validate_and_complete(order)

        assert result.confidence_scores["items.0.quantity"] == "low"
        assert result.confidence_scores["items.0.unit_price"] == "low"
        assert result.confidence_scores["items.0.amount"] == "low"


# ---------------------------------------------------------------------------
# Immutability: original order must not be modified
# ---------------------------------------------------------------------------


class TestImmutability:
    """validate_and_complete must return a new PurchaseOrder."""

    def test_original_order_unchanged(self, make_order, make_item):
        """Original PurchaseOrder is not mutated."""
        item = make_item(quantity=100, unit_price=500)
        order = make_order(
            items=[item],
            confidence_scores={
                "items.0.quantity": "high",
                "items.0.unit_price": "high",
            },
        )

        original_item_amount = order.items[0].amount
        original_subtotal = order.subtotal
        original_scores = copy.deepcopy(order.confidence_scores)

        result = validate_and_complete(order)

        # Result should have changes
        assert result.items[0].amount == 50000

        # Original must be untouched
        assert order.items[0].amount == original_item_amount
        assert order.subtotal == original_subtotal
        assert order.confidence_scores == original_scores

    def test_returns_new_instance(self, make_order):
        """Return value is a different object."""
        order = make_order(confidence_scores={})

        result = validate_and_complete(order)

        assert result is not order
