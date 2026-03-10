"""Tests for ocr/visualizer.py — bounding box drawing on images.

RED phase: these tests define the expected interface and behavior
of visualizer.py before it is implemented.
"""

from PIL import Image

from ocr.models import FieldSegment
from ocr.visualizer import draw_bounding_boxes, get_color, normalize_to_pixel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_segment(
    *,
    field_name: str = "order_number",
    box_2d: list[int] | None = None,
    ocr_text: str | None = "PO-001",
    verified: bool = True,
    confidence: str = "high",
) -> FieldSegment:
    """Create a FieldSegment with sensible defaults."""
    return FieldSegment(
        field_name=field_name,
        box_2d=box_2d or [100, 200, 300, 400],
        ocr_text=ocr_text,
        verified=verified,
        confidence=confidence,
    )


def _white_image(width: int = 500, height: int = 400) -> Image.Image:
    """Create a plain white RGB image for testing."""
    return Image.new("RGB", (width, height), color=(255, 255, 255))


# ===========================================================================
# TestNormalizeToPixel
# ===========================================================================


class TestNormalizeToPixel:
    """Tests for normalize_to_pixel(box_2d, image_width, image_height).

    The function converts box_2d [y0, x0, y1, x1] (0-1000 normalized)
    into pixel coordinates (x_min, y_min, x_max, y_max).
    """

    def test_basic_conversion_square_image(self):
        """1000x1000 image, box_2d=[0,0,500,500] -> (0,0,500,500)."""
        result = normalize_to_pixel([0, 0, 500, 500], 1000, 1000)
        assert result == (0, 0, 500, 500)

    def test_different_width_and_height(self):
        """200x100 image, box_2d=[0,0,1000,1000] -> full image (0,0,200,100)."""
        result = normalize_to_pixel([0, 0, 1000, 1000], 200, 100)
        assert result == (0, 0, 200, 100)

    def test_result_is_integers(self):
        """Pixel coordinates must be int, not float."""
        result = normalize_to_pixel([333, 333, 666, 666], 100, 100)
        assert all(isinstance(v, int) for v in result), (
            f"Expected all int, got {[type(v) for v in result]}"
        )

    def test_clip_values_exceeding_bounds(self):
        """box_2d values > 1000 should be clipped to image boundaries."""
        result = normalize_to_pixel([0, 0, 1200, 1500], 500, 400)
        x_min, y_min, x_max, y_max = result
        assert x_max <= 500, f"x_max {x_max} exceeds image width 500"
        assert y_max <= 400, f"y_max {y_max} exceeds image height 400"

    def test_clip_negative_values(self):
        """box_2d values < 0 should be clipped to 0."""
        result = normalize_to_pixel([-100, -50, 500, 500], 1000, 1000)
        x_min, y_min, x_max, y_max = result
        assert x_min >= 0, f"x_min {x_min} is negative"
        assert y_min >= 0, f"y_min {y_min} is negative"

    def test_coordinate_order_y0_x0_y1_x1(self):
        """box_2d=[100,200,300,400] means y0=100,x0=200,y1=300,x1=400.

        For a 1000x1000 image:
          pixel_y_min = 100 * 1000 / 1000 = 100
          pixel_x_min = 200 * 1000 / 1000 = 200
          pixel_y_max = 300 * 1000 / 1000 = 300
          pixel_x_max = 400 * 1000 / 1000 = 400

        Return order is (x_min, y_min, x_max, y_max).
        """
        result = normalize_to_pixel([100, 200, 300, 400], 1000, 1000)
        assert result == (200, 100, 400, 300)

    def test_non_square_image_scales_independently(self):
        """Width and height scale independently.

        box_2d=[500, 500, 1000, 1000], image 200x100:
          pixel_y_min = 500/1000 * 100 = 50
          pixel_x_min = 500/1000 * 200 = 100
          pixel_y_max = 1000/1000 * 100 = 100
          pixel_x_max = 1000/1000 * 200 = 200
        -> (100, 50, 200, 100)
        """
        result = normalize_to_pixel([500, 500, 1000, 1000], 200, 100)
        assert result == (100, 50, 200, 100)


# ===========================================================================
# TestGetColor
# ===========================================================================


class TestGetColor:
    """Tests for get_color(confidence) -> RGB tuple."""

    def test_high_returns_blue(self):
        assert get_color("high") == (33, 150, 243)

    def test_medium_returns_yellow(self):
        assert get_color("medium") == (255, 193, 7)

    def test_low_returns_red(self):
        assert get_color("low") == (244, 67, 54)


# ===========================================================================
# TestDrawBoundingBoxes
# ===========================================================================


class TestDrawBoundingBoxes:
    """Tests for draw_bounding_boxes(image, segments) -> Image.Image."""

    def test_original_image_not_modified(self):
        """The input image must not be mutated."""
        img = _white_image()
        original_data = list(img.getdata())
        segments = [_make_segment()]

        draw_bounding_boxes(img, segments)

        assert list(img.getdata()) == original_data

    def test_returns_pil_image(self):
        """Return value must be a PIL.Image.Image."""
        img = _white_image()
        result = draw_bounding_boxes(img, [_make_segment()])
        assert isinstance(result, Image.Image)

    def test_returns_rgb_mode(self):
        """Output image should be in RGB mode."""
        img = _white_image()
        result = draw_bounding_boxes(img, [_make_segment()])
        assert result.mode == "RGB"

    def test_preserves_image_size(self):
        """Output image must have the same dimensions as input."""
        img = _white_image(width=800, height=600)
        result = draw_bounding_boxes(img, [_make_segment()])
        assert result.size == (800, 600)

    def test_empty_segments_no_error(self):
        """An empty segment list should produce a valid image without error."""
        img = _white_image()
        result = draw_bounding_boxes(img, [])
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_multiple_segments_no_error(self):
        """Multiple segments should all be processed without error."""
        img = _white_image()
        segments = [
            _make_segment(
                field_name="order_number", box_2d=[0, 0, 200, 200], confidence="high"
            ),
            _make_segment(
                field_name="orderer.company_name",
                box_2d=[300, 300, 500, 500],
                confidence="medium",
            ),
            _make_segment(
                field_name="items.0.amount",
                box_2d=[600, 600, 800, 800],
                confidence="low",
            ),
        ]
        result = draw_bounding_boxes(img, segments)
        assert isinstance(result, Image.Image)

    def test_all_confidence_levels_no_error(self):
        """Each confidence level (high, medium, low) must be handled."""
        img = _white_image()
        for level in ("high", "medium", "low"):
            segment = _make_segment(confidence=level)
            result = draw_bounding_boxes(img, [segment])
            assert isinstance(result, Image.Image), f"Failed for confidence={level}"

    def test_drawing_changes_pixels(self):
        """After drawing at least one segment, the image should differ from blank."""
        img = _white_image(width=1000, height=1000)
        original_data = list(img.getdata())
        segment = _make_segment(box_2d=[100, 100, 900, 900], confidence="low")

        result = draw_bounding_boxes(img, [segment])

        result_data = list(result.getdata())
        assert result_data != original_data, "Expected drawn image to differ from blank"

    def test_rgba_input_returns_rgb(self):
        """If input is RGBA, output should still be RGB."""
        img = Image.new("RGBA", (500, 400), color=(255, 255, 255, 255))
        result = draw_bounding_boxes(img, [_make_segment()])
        assert result.mode == "RGB"

    def test_draw_order_low_on_top(self):
        """Low-confidence boxes should be drawn last (on top).

        We verify by drawing overlapping boxes: a high box first, then a low
        box at the same location. The center pixel should match the low color,
        not the high color.
        """
        img = _white_image(width=1000, height=1000)
        segments = [
            _make_segment(
                field_name="a", box_2d=[400, 400, 600, 600], confidence="high"
            ),
            _make_segment(
                field_name="b", box_2d=[400, 400, 600, 600], confidence="low"
            ),
        ]

        result = draw_bounding_boxes(img, segments)

        # The center of the box region (pixel 500, 500) should have been
        # filled with the low-confidence color's semi-transparent overlay,
        # not the high-confidence one.
        center_pixel = result.getpixel((500, 500))
        high_color = (33, 150, 243)
        low_color = (244, 67, 54)

        # The pixel won't be exactly the box color (it's blended with white
        # at 20% opacity), but it should be closer to the low color than high.
        def color_distance(c1, c2):
            return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

        dist_to_low = color_distance(center_pixel[:3], low_color)
        dist_to_high = color_distance(center_pixel[:3], high_color)
        assert dist_to_low < dist_to_high, (
            f"Expected low color on top. Pixel={center_pixel}, "
            f"dist_to_low={dist_to_low:.1f}, dist_to_high={dist_to_high:.1f}"
        )

    def test_selected_field_gets_extra_highlight(self):
        """Selected field should receive an additional black outline."""
        img = _white_image(width=1000, height=1000)
        segment = _make_segment(
            field_name="order_number",
            box_2d=[200, 200, 800, 800],
            confidence="high",
        )

        result = draw_bounding_boxes(
            img,
            [segment],
            selected_field_name="order_number",
        )

        assert result.getpixel((198, 198)) == (0, 0, 0)
