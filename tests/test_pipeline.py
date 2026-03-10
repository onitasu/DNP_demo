"""Tests for ocr/pipeline.py — RED phase (TDD).

pipeline.py does not exist yet. All tests are expected to FAIL.
"""

from unittest.mock import MagicMock, patch

from PIL import Image

from ocr.models import (
    ConfidenceLevel,
    FieldSegment,
    PipelineResult,
    PurchaseOrder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_order_with_confidence(
    field_name: str, confidence: ConfidenceLevel
) -> PurchaseOrder:
    """指定フィールドの confidence だけを持つ最小限の PurchaseOrder を作る。"""
    return PurchaseOrder(
        order_number="PO-001" if field_name == "order_number" else None,
        items=[],
        confidence_scores={field_name: confidence},
    )


def _make_segment(
    field_name: str,
    verified: bool,
    confidence: ConfidenceLevel = "high",
) -> FieldSegment:
    """テスト用 FieldSegment を作る。"""
    return FieldSegment(
        field_name=field_name,
        box_2d=[0, 0, 100, 100],
        ocr_text="dummy",
        verified=verified,
        confidence=confidence,
    )


# ===========================================================================
# TestConfidenceMerge -- merge_confidence 関数の単体テスト
# ===========================================================================


class TestConfidenceMerge:
    """REQUIREMENTS.md section 4.1 の信頼度マージテーブルを検証する。"""

    def test_high_verified_stays_high(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "high")
        segments = [_make_segment("order_number", verified=True)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "high"

    def test_high_unverified_becomes_low(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "high")
        segments = [_make_segment("order_number", verified=False)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "low"

    def test_medium_verified_becomes_high(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "medium")
        segments = [_make_segment("order_number", verified=True)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "high"

    def test_medium_unverified_becomes_low(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "medium")
        segments = [_make_segment("order_number", verified=False)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "low"

    def test_low_verified_becomes_medium(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "low")
        segments = [_make_segment("order_number", verified=True)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "medium"

    def test_low_unverified_stays_low(self) -> None:
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "low")
        segments = [_make_segment("order_number", verified=False)]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "low"

    def test_no_segment_keeps_step1_confidence(self) -> None:
        """セグメントが存在しないフィールドは Step 1 の confidence を維持する。"""
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "high")
        segments: list[FieldSegment] = []  # セグメントなし

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "high"

    def test_segment_confidence_updated(self) -> None:
        """FieldSegment.confidence が最終マージ結果に更新される。"""
        from ocr.pipeline import merge_confidence

        order = _make_order_with_confidence("order_number", "medium")
        segments = [_make_segment("order_number", verified=True, confidence="medium")]

        merged_order, merged_segments = merge_confidence(order, segments)

        # medium + verified=True -> high なので FieldSegment.confidence も high
        assert merged_segments[0].confidence == "high"

    def test_multiple_fields(self) -> None:
        """複数フィールドが独立してマージされる。"""
        from ocr.pipeline import merge_confidence

        order = PurchaseOrder(
            order_number="PO-001",
            order_date="2024-03-15",
            items=[],
            confidence_scores={
                "order_number": "high",
                "order_date": "medium",
            },
        )
        segments = [
            _make_segment("order_number", verified=False),  # high + false -> low
            _make_segment("order_date", verified=True),  # medium + true -> high
        ]

        merged_order, merged_segments = merge_confidence(order, segments)

        assert merged_order.confidence_scores["order_number"] == "low"
        assert merged_order.confidence_scores["order_date"] == "high"


# ===========================================================================
# TestRunPipeline -- パイプライン全体のテスト（LLM をモック）
# ===========================================================================


class TestRunPipeline:
    """run_pipeline の統合テスト。LLM 呼び出しはすべてモック。"""

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_returns_pipeline_result(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        result = run_pipeline(
            image=dummy_image,
            api_key="test-key",
        )

        assert isinstance(result, PipelineResult)
        assert result.purchase_order is not None
        assert isinstance(result.segments, list)

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_step1_called(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        run_pipeline(image=dummy_image, api_key="test-key")

        mock_extract_order.assert_called_once()

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_step2_called(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        run_pipeline(image=dummy_image, api_key="test-key")

        mock_extract_segments.assert_called_once()

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_step1_model_in_result(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        result = run_pipeline(
            image=dummy_image,
            api_key="test-key",
            step1_model="gemini-2.5-pro",
        )

        assert result.step1_model == "gemini-2.5-pro"

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_step2_model_in_result(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        result = run_pipeline(
            image=dummy_image,
            api_key="test-key",
            step2_model="gemini-2.5-flash",
        )

        assert result.step2_model == "gemini-2.5-flash"

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_processing_time_ms_positive(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        result = run_pipeline(image=dummy_image, api_key="test-key")

        assert isinstance(result.processing_time_ms, int)
        assert result.processing_time_ms >= 0

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_calculator_called_when_enabled(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments
        mock_validate.return_value = sample_order

        run_pipeline(
            image=dummy_image,
            api_key="test-key",
            enable_calculator=True,
        )

        mock_validate.assert_called_once()

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_calculator_not_called_when_disabled(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
        sample_segments: list[FieldSegment],
    ) -> None:
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.return_value = sample_segments

        run_pipeline(
            image=dummy_image,
            api_key="test-key",
            enable_calculator=False,
        )

        mock_validate.assert_not_called()

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_confidence_merge_applied(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
    ) -> None:
        """high + verified=False -> low にマージされることを検証。"""
        from ocr.pipeline import run_pipeline

        order = PurchaseOrder(
            order_number="PO-001",
            items=[],
            confidence_scores={"order_number": "high"},
        )
        segments = [
            FieldSegment(
                field_name="order_number",
                box_2d=[50, 100, 100, 300],
                ocr_text="PO-002",  # 不一致
                verified=False,
                confidence="high",
            ),
        ]

        mock_extract_order.return_value = order
        mock_extract_segments.return_value = segments
        # validate_and_complete はマージ後の order をそのまま返す
        mock_validate.side_effect = lambda o: o

        result = run_pipeline(image=dummy_image, api_key="test-key")

        # high + false -> low
        assert result.purchase_order.confidence_scores["order_number"] == "low"

    @patch("ocr.pipeline.genai")
    @patch("ocr.pipeline.validate_and_complete")
    @patch("ocr.pipeline.extract_segments")
    @patch("ocr.pipeline.extract_purchase_order")
    def test_step2_failure_graceful_degradation(
        self,
        mock_extract_order: MagicMock,
        mock_extract_segments: MagicMock,
        mock_validate: MagicMock,
        mock_genai: MagicMock,
        dummy_image: Image.Image,
        sample_order: PurchaseOrder,
    ) -> None:
        """Step 2 が例外を送出しても PipelineResult を返す（segments=[]）。"""
        from ocr.pipeline import run_pipeline

        mock_extract_order.return_value = sample_order
        mock_extract_segments.side_effect = RuntimeError("Step 2 failed")
        mock_validate.return_value = sample_order

        result = run_pipeline(image=dummy_image, api_key="test-key")

        assert isinstance(result, PipelineResult)
        assert result.segments == []
        # Step 1 の confidence がそのまま維持される
        assert result.purchase_order.confidence_scores == sample_order.confidence_scores
