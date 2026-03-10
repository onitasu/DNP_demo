from typing import Literal, Optional

from pydantic import BaseModel

ConfidenceLevel = Literal["high", "medium", "low"]


class Orderer(BaseModel):
    company_name: Optional[str] = None
    department: Optional[str] = None
    contact_person: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None


class OrderItem(BaseModel):
    item_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class PurchaseOrder(BaseModel):
    order_number: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    orderer: Optional[Orderer] = None
    items: list[OrderItem]
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    payment_terms: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    confidence_scores: dict[str, ConfidenceLevel]


class FieldSegment(BaseModel):
    field_name: str
    box_2d: list[int]
    ocr_text: Optional[str] = None
    verified: bool
    confidence: ConfidenceLevel


class PipelineResult(BaseModel):
    purchase_order: PurchaseOrder
    segments: list[FieldSegment]
    processing_time_ms: int
    step1_model: str
    step2_model: str
