import logging
import mimetypes
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import get_llm_model, get_llm_provider, load_env
from .models import LLMProvider, OCRResponse
from .ocr import run_ocr_pipeline

load_env()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI-OCR Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "application/pdf",
}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB


def guess_mime_type(file: UploadFile) -> str:
    if file.content_type:
        return file.content_type
    guessed, _ = mimetypes.guess_type(file.filename or "")
    return guessed or "application/octet-stream"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/ocr", response_model=OCRResponse)
async def ocr(
    file: UploadFile = File(..., description="画像またはPDFファイル"),
    calculate_missing: bool = Query(True, description="金額補完を実行するか"),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="ファイルが空です")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="ファイルサイズが大きすぎます (最大10MB)")

    mime_type = guess_mime_type(file)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"未対応のファイルタイプです: {mime_type}")

    try:
        provider = LLMProvider(get_llm_provider())
        model = get_llm_model()
        result = await run_ocr_pipeline(
            content_bytes=content,
            mime_type=mime_type,
            file_name=Path(file.filename or "uploaded").name,
            provider=provider,
            model=model,
            do_calculate=calculate_missing,
        )
        return result
    except ValueError as exc:
        logger.exception("Validation error in OCR pipeline")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - 実行時の外部APIエラー
        logger.exception("OCR pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
async def root():
    return {"message": "AI-OCR backend is running", "routes": ["/health", "/api/ocr"]}
