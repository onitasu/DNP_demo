"""OCRパイプライン実装。"""
import asyncio
import base64
import logging
import time
from typing import Any, Optional, Type

from .config import default_model
from .models import (
    LLMProvider,
    ReceiptInfo,
    StructuredOutputConfig,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)

# Optional imports
try:  # pragma: no cover - ランタイムの有無で分岐
    from google import genai
    from google.genai import types as genai_types
except Exception:  # pragma: no cover
    genai = None
    genai_types = None

try:  # pragma: no cover
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

_GOOGLE_CLIENT = None
_OPENAI_CLIENT = None


def get_google_client():
    global _GOOGLE_CLIENT
    if _GOOGLE_CLIENT is None:
        if genai is None:
            raise RuntimeError("google-genai がインストールされていません。`pip install google-genai`")
        import os

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません。")
        _GOOGLE_CLIENT = genai.Client(api_key=api_key)
    return _GOOGLE_CLIENT


def get_openai_client():
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        if OpenAI is None:
            raise RuntimeError("openai パッケージが見つかりません。`pip install openai`")
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("環境変数 OPENAI_API_KEY が設定されていません。")
        _OPENAI_CLIENT = OpenAI()
    return _OPENAI_CLIENT


def with_retries(func, max_retries: int, delay_sec: float, label: str) -> Any:
    attempt = 0
    last_exc = None
    while attempt < max_retries:
        try:
            attempt += 1
            logger.info("%s attempt %s/%s", label, attempt, max_retries)
            return func()
        except Exception as exc:  # pragma: no cover - 実行時ログ
            last_exc = exc
            logger.warning("%s failed attempt %s: %r", label, attempt, exc)
            if attempt < max_retries:
                time.sleep(delay_sec)
    logger.error("%s all %s attempts failed", label, max_retries)
    raise last_exc


def build_content_google(page_bytes: Optional[bytes], mime_type: Optional[str]):
    if page_bytes is None:
        return None
    if genai_types is None:
        raise RuntimeError("google-genai types の読み込みに失敗しました。")
    return genai_types.Part.from_bytes(data=page_bytes, mime_type=mime_type or "application/octet-stream")


def build_content_openai(page_bytes: Optional[bytes], file_name: Optional[str], mime_type: Optional[str]):
    if page_bytes is None:
        return None
    mt = (mime_type or "application/octet-stream").lower()
    b64 = base64.b64encode(page_bytes).decode("utf-8")
    data_url = f"data:{mt};base64,{b64}"
    if mt == "application/pdf":
        return {"type": "input_file", "filename": file_name or "input.pdf", "file_data": data_url}
    if mt.startswith("image/"):
        return {"type": "input_image", "image_url": data_url}
    return {"type": "input_file", "filename": file_name or "input.bin", "file_data": data_url}


def generate_structured_output(
    config: StructuredOutputConfig,
    prompt: str,
    response_schema: Type,
    *,
    content_bytes: Optional[bytes] = None,
    mime_type: Optional[str] = None,
    file_name: Optional[str] = None,
):
    provider = config.provider.value if isinstance(config.provider, LLMProvider) else config.provider

    if provider == LLMProvider.google.value:
        client = get_google_client()
        content_part = build_content_google(content_bytes, mime_type)
        contents = []
        if content_part is not None:
            contents.append(content_part)
        contents.append(prompt)

        def _call():
            return client.models.generate_content(
                model=config.model,
                contents=contents,
                config={"response_mime_type": "application/json", "response_schema": response_schema},
            )

        resp = with_retries(_call, config.retries, config.delay_sec, label="google-genai")
        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            raise RuntimeError("google-genai: parsed レスポンスが取得できませんでした。")
        return parsed

    if provider == LLMProvider.openai.value:
        client = get_openai_client()
        user_inputs = []
        content_obj = build_content_openai(content_bytes, file_name, mime_type)
        if content_obj is not None:
            user_inputs.append(content_obj)
        user_inputs.append({"type": "input_text", "text": prompt})

        def _call():
            return client.responses.parse(
                model=config.model,
                max_output_tokens=config.max_output_tokens,
                temperature=config.temperature,
                input=[{"role": "user", "content": user_inputs}],
                text_format=response_schema,
            )

        resp = with_retries(_call, config.retries, config.delay_sec, label="openai")
        parsed = getattr(resp, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("openai: output_parsed が取得できませんでした。")
        return parsed

    raise ValueError(f"Unsupported provider: {config.provider}")


TRANSCRIPTION_PROMPT = """あなたは領収書専用のOCRエンジンです。
入力された領収書画像から文字を読み取り、全体のテキストを正確に抽出してください。
また位置や構造も含めて抽出してください。

【重要】
- 文字が不鮮明でも可能な限り推定して抽出
- 全体のテキストを漏れなく抽出
- 日本語の文字認識に特に注意を払う"""

EXTRACTION_PROMPT = """以下の領収書テキストから必要な情報を抽出してください。

【抽出項目】
- 店舗名、住所、電話番号
- 合計金額、税率、消費税額、税抜金額
- 発行日（YYYY-MM-DD形式）、発行時刻（HH:MM形式）
- レシート番号、インボイス番号
- 支払方法、商品概要

【抽出指針】
- 見つからない項目は null に設定
- 金額は数値のみ（¥マークや,は除去）
- 日付は統一形式で

【領収書テキスト】
{text}

上記から情報を抽出してください。"""


def step1_transcription(
    config: StructuredOutputConfig,
    content_bytes: bytes,
    mime_type: str,
    file_name: Optional[str] = None,
) -> TranscriptionResult:
    return generate_structured_output(
        config=config,
        prompt=TRANSCRIPTION_PROMPT,
        response_schema=TranscriptionResult,
        content_bytes=content_bytes,
        mime_type=mime_type,
        file_name=file_name,
    )


def step2_extraction(config: StructuredOutputConfig, transcription: TranscriptionResult) -> ReceiptInfo:
    formatted_prompt = EXTRACTION_PROMPT.format(text=transcription.full_text)
    return generate_structured_output(
        config=config,
        prompt=formatted_prompt,
        response_schema=ReceiptInfo,
        content_bytes=None,
        mime_type=None,
        file_name=None,
    )


def calculate_missing_amounts(receipt_info: ReceiptInfo) -> ReceiptInfo:
    has_total = receipt_info.total_amount is not None
    has_tax_rate = receipt_info.tax_rate is not None
    has_tax_amount = receipt_info.tax_amount is not None
    has_subtotal = receipt_info.subtotal_amount is not None

    if has_total and has_tax_rate and has_tax_amount and has_subtotal:
        return receipt_info
    if not has_total or not has_tax_rate:
        return receipt_info

    try:
        total_str = receipt_info.total_amount.replace(",", "").replace("¥", "").replace("円", "").strip()
        tax_rate_str = receipt_info.tax_rate.replace("%", "").strip()
        total_amount = float(total_str)
        tax_rate = float(tax_rate_str) / 100

        if not has_tax_amount:
            calculated_tax = total_amount * tax_rate / (1 + tax_rate)
            receipt_info.tax_amount = str(int(round(calculated_tax)))

        if not has_subtotal:
            tax_amount_num = float(
                receipt_info.tax_amount.replace(",", "").replace("¥", "").replace("円", "").strip()
            )
            calculated_subtotal = total_amount - tax_amount_num
            receipt_info.subtotal_amount = str(int(round(calculated_subtotal)))
    except (ValueError, AttributeError):
        return receipt_info

    return receipt_info


async def run_ocr_pipeline(
    *,
    content_bytes: bytes,
    mime_type: str,
    file_name: Optional[str],
    provider: LLMProvider,
    model: Optional[str],
    do_calculate: bool = True,
):
    config = StructuredOutputConfig(
        provider=provider,
        model=model or default_model(provider.value),
        max_output_tokens=4000 if provider == LLMProvider.openai else None,
        temperature=0.1 if provider == LLMProvider.openai else None,
        retries=3,
        delay_sec=2.0,
    )

    started = time.perf_counter()
    transcription = await asyncio.to_thread(
        step1_transcription, config, content_bytes, mime_type, file_name
    )
    receipt_info = await asyncio.to_thread(step2_extraction, config, transcription)
    calculated = calculate_missing_amounts(receipt_info.model_copy(deep=True)) if do_calculate else receipt_info
    duration_ms = int((time.perf_counter() - started) * 1000)

    return {
        "provider": provider,
        "model": config.model,
        "transcription": transcription,
        "receipt_info": receipt_info,
        "calculated_receipt_info": calculated,
        "duration_ms": duration_ms,
    }


__all__ = [
    "run_ocr_pipeline",
    "step1_transcription",
    "step2_extraction",
    "calculate_missing_amounts",
]
