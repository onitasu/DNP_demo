"""Pydanticモデルと共通設定。"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    google = "google"
    openai = "openai"


class StructuredOutputConfig(BaseModel):
    provider: LLMProvider
    model: str
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    retries: int = 3
    delay_sec: float = 2.0


class TranscriptionResult(BaseModel):
    """ステップ1: 文字起こし結果"""

    full_text: str = Field(..., description="領収書全体の文字起こしテキスト")
    document_type: Optional[str] = Field(None, description="文書種別")


class ReceiptInfo(BaseModel):
    """ステップ2: 領収書から抽出された情報"""

    # 基本情報
    store_name: Optional[str] = Field(None, description="店舗名・会社名")
    store_address: Optional[str] = Field(None, description="店舗住所")
    store_phone: Optional[str] = Field(None, description="店舗電話番号")

    # 金額関連
    total_amount: Optional[str] = Field(None, description="合計金額")
    tax_rate: Optional[str] = Field(None, description="税率（%）")
    tax_amount: Optional[str] = Field(None, description="消費税額")
    subtotal_amount: Optional[str] = Field(None, description="税抜金額")

    # 日時情報
    issue_date: Optional[str] = Field(None, description="発行日（YYYY-MM-DD形式）")
    issue_time: Optional[str] = Field(None, description="発行時刻（HH:MM形式）")

    # 識別情報
    receipt_number: Optional[str] = Field(None, description="レシート番号・伝票番号")
    invoice_number: Optional[str] = Field(None, description="インボイス番号（T番号）")

    # 支払・商品情報
    payment_method: Optional[str] = Field(None, description="支払方法")
    items_summary: Optional[str] = Field(None, description="購入商品の概要")


class OCRResponse(BaseModel):
    provider: LLMProvider
    model: str
    transcription: TranscriptionResult
    receipt_info: ReceiptInfo
    calculated_receipt_info: ReceiptInfo
    duration_ms: int


__all__ = [
    "LLMProvider",
    "StructuredOutputConfig",
    "TranscriptionResult",
    "ReceiptInfo",
    "OCRResponse",
]
