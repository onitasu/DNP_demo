"""Helpers for rendering extraction results in tabular form."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ocr.models import ConfidenceLevel, FieldSegment, PurchaseOrder

_CONFIDENCE_LABELS: dict[ConfidenceLevel, str] = {
    "high": "OK",
    "medium": "確認推奨",
    "low": "要確認",
}


def _stringify_value(value: object) -> str:
    return "—" if value is None else str(value)


def _verified_label(segment: FieldSegment | None) -> str:
    if segment is None:
        return "未検出"
    return "一致" if segment.verified else "不一致"


def _append_row(
    rows: list[dict[str, Any]],
    *,
    section: str,
    label: str,
    field_key: str,
    value: object,
    confidence: ConfidenceLevel,
    segment_map: dict[str, FieldSegment],
) -> None:
    segment = segment_map.get(field_key)
    rows.append(
        {
            "section": section,
            "label": label,
            "field_key": field_key,
            "value": _stringify_value(value),
            "confidence": confidence,
            "confidence_label": _CONFIDENCE_LABELS[confidence],
            "verified": _verified_label(segment),
            "ocr_text": _stringify_value(segment.ocr_text if segment else None),
        }
    )


def build_result_rows(
    order: PurchaseOrder,
    segments: Iterable[FieldSegment],
) -> list[dict[str, Any]]:
    """PurchaseOrder と segments を表示用の表行に変換する。"""
    rows: list[dict[str, Any]] = []
    segment_map = {segment.field_name: segment for segment in segments}
    scores = order.confidence_scores

    def append(section: str, label: str, field_key: str, value: object) -> None:
        _append_row(
            rows,
            section=section,
            label=label,
            field_key=field_key,
            value=value,
            confidence=scores.get(field_key, "medium"),
            segment_map=segment_map,
        )

    append("発注基本情報", "発注番号", "order_number", order.order_number)
    append("発注基本情報", "発注日", "order_date", order.order_date)
    append("発注基本情報", "納期", "delivery_date", order.delivery_date)
    append("発注基本情報", "支払条件", "payment_terms", order.payment_terms)

    orderer = order.orderer
    append(
        "発注元情報",
        "会社名",
        "orderer.company_name",
        orderer.company_name if orderer else None,
    )
    append(
        "発注元情報",
        "部署名",
        "orderer.department",
        orderer.department if orderer else None,
    )
    append(
        "発注元情報",
        "担当者",
        "orderer.contact_person",
        orderer.contact_person if orderer else None,
    )
    append(
        "発注元情報",
        "住所",
        "orderer.address",
        orderer.address if orderer else None,
    )
    append("発注元情報", "電話", "orderer.phone", orderer.phone if orderer else None)
    append("発注元情報", "FAX", "orderer.fax", orderer.fax if orderer else None)
    append("発注元情報", "メール", "orderer.email", orderer.email if orderer else None)

    for index, item in enumerate(order.items):
        section = f"品目明細 {index + 1}"
        append(section, "品番", f"items.{index}.item_number", item.item_number)
        append(section, "品名", f"items.{index}.description", item.description)
        append(section, "数量", f"items.{index}.quantity", item.quantity)
        append(section, "単位", f"items.{index}.unit", item.unit)
        append(section, "単価", f"items.{index}.unit_price", item.unit_price)
        append(section, "金額", f"items.{index}.amount", item.amount)

    append("金額情報", "小計", "subtotal", order.subtotal)
    append("金額情報", "消費税", "tax_amount", order.tax_amount)
    append("金額情報", "合計", "total_amount", order.total_amount)
    append("その他", "納品先", "delivery_address", order.delivery_address)
    append("その他", "備考", "notes", order.notes)

    return rows
