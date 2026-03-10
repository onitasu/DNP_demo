from PIL import Image, ImageDraw, ImageFont

from ocr.models import ConfidenceLevel, FieldSegment

BOX_LINE_WIDTH = 3
BOX_FILL_ALPHA = 51  # ~20% 透過
LABEL_FONT_SIZE = 14

_COLORS: dict[ConfidenceLevel, tuple[int, int, int]] = {
    "high": (33, 150, 243),
    "medium": (255, 193, 7),
    "low": (244, 67, 54),
}

_DRAW_ORDER: list[ConfidenceLevel] = ["high", "medium", "low"]


def get_color(confidence: ConfidenceLevel) -> tuple[int, int, int]:
    """信頼度に対応する RGB カラーを返す。"""
    return _COLORS[confidence]


def normalize_to_pixel(
    box_2d: list[int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """box_2d [y0, x0, y1, x1] (0-1000) を (x_min, y_min, x_max, y_max) ピクセル座標に変換。"""
    y0, x0, y1, x1 = box_2d
    x_min = int(max(0, min(x0, 1000)) / 1000 * image_width)
    y_min = int(max(0, min(y0, 1000)) / 1000 * image_height)
    x_max = int(max(0, min(x1, 1000)) / 1000 * image_width)
    y_max = int(max(0, min(y1, 1000)) / 1000 * image_height)
    return x_min, y_min, x_max, y_max


def draw_bounding_boxes(
    image: Image.Image,
    segments: list[FieldSegment],
) -> Image.Image:
    """原本のコピーにバウンディングボックスを描画して返す。"""
    result = image.convert("RGB").copy()
    w, h = result.size

    # high → medium → low の順で描画（low が最前面）
    ordered = sorted(
        segments,
        key=lambda s: _DRAW_ORDER.index(s.confidence),
    )

    # 半透明塗り用レイヤー
    overlay = result.copy()
    overlay_draw = ImageDraw.Draw(overlay)

    draw = ImageDraw.Draw(result)

    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE
        )
    except (OSError, IOError):
        font = ImageFont.load_default()

    for seg in ordered:
        color = get_color(seg.confidence)
        x_min, y_min, x_max, y_max = normalize_to_pixel(seg.box_2d, w, h)

        # 半透明塗り
        overlay_draw.rectangle([x_min, y_min, x_max, y_max], fill=color)

    # overlay を alpha ブレンド
    result = Image.blend(result, overlay, alpha=BOX_FILL_ALPHA / 255)
    draw = ImageDraw.Draw(result)

    for seg in ordered:
        color = get_color(seg.confidence)
        x_min, y_min, x_max, y_max = normalize_to_pixel(seg.box_2d, w, h)

        # 枠線
        draw.rectangle(
            [x_min, y_min, x_max, y_max],
            outline=color,
            width=BOX_LINE_WIDTH,
        )

        # ラベル
        label = seg.field_name
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        label_x = x_min
        label_y = max(0, y_min - text_h - 4)

        draw.rectangle(
            [label_x, label_y, label_x + text_w + 4, label_y + text_h + 4],
            fill=color,
        )
        draw.text((label_x + 2, label_y + 2), label, fill=(255, 255, 255), font=font)

    return result
