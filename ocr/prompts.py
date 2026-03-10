from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ocr.models import PurchaseOrder


def build_ocr_prompt() -> str:
    """Step 1 (OCR + 構造化抽出) 用プロンプトを返す。"""
    return """あなたは発注書の OCR 専門家です。

画像から発注書の全フィールドを抽出してください。
これは日本語の発注書です。フィールド値は原文のまま抽出してください（正規化・変換しないこと）。

各フィールドの信頼度（confidence）を以下の基準で判定してください：
- high: テキストが明瞭に読め、フォーマットも明確
- medium: テキストは読めるが一部曖昧（手書きのくせ字、かすれ等）
- low: 判読困難、または該当フィールドが画像上に存在するか不確か

confidence_scores には各フィールドのキーと信頼度を記録してください。
ネストフィールドは "orderer.company_name" のようにドット区切りで、
配列要素は "items.0.description" のようにインデックス付きで記録してください。
"""


def build_segmentation_system_instruction() -> str:
    """Step 2 (セグメンテーション + 検証) 用 system_instruction を返す。"""
    return """Return bounding boxes as an array with labels.
Never return masks.
Each bounding box should use box_2d format: [y_min, x_min, y_max, x_max] normalized to 0-1000.
"""


def build_segmentation_prompt(order: "PurchaseOrder") -> str:
    """Step 2 用ユーザープロンプトを返す（Step 1 の抽出結果を埋め込む）。"""
    lines: list[str] = []
    lines.append("以下は Step 1 の OCR 抽出結果です：\n")

    def _add(key: str, value: object) -> None:
        if value is not None:
            lines.append(f"  {key}: {value}")

    _add("order_number", order.order_number)
    _add("order_date", order.order_date)
    _add("delivery_date", order.delivery_date)
    _add("payment_terms", order.payment_terms)
    _add("delivery_address", order.delivery_address)
    _add("notes", order.notes)
    _add("subtotal", order.subtotal)
    _add("tax_amount", order.tax_amount)
    _add("total_amount", order.total_amount)

    if order.orderer:
        o = order.orderer
        _add("orderer.company_name", o.company_name)
        _add("orderer.department", o.department)
        _add("orderer.contact_person", o.contact_person)
        _add("orderer.address", o.address)
        _add("orderer.phone", o.phone)
        _add("orderer.fax", o.fax)
        _add("orderer.email", o.email)

    for i, item in enumerate(order.items):
        _add(f"items.{i}.item_number", item.item_number)
        _add(f"items.{i}.description", item.description)
        _add(f"items.{i}.quantity", item.quantity)
        _add(f"items.{i}.unit", item.unit)
        _add(f"items.{i}.unit_price", item.unit_price)
        _add(f"items.{i}.amount", item.amount)

    lines.append("")
    lines.append(
        "上記の各フィールドについて、画像上の対応領域を box_2d バウンディングボックスで示してください。"
    )
    lines.append(
        "また、画像上のテキストを再度読み取り、OCR 結果と一致するか verified で検証してください。"
    )
    lines.append("")
    lines.append("verified の判定基準：")
    lines.append(
        "  true: 画像上のテキストと OCR 結果が実質的に一致（表記揺れ・カンマの有無等は許容）"
    )
    lines.append("  false: 明らかに異なる、または画像上にテキストが見つからない")

    return "\n".join(lines)
