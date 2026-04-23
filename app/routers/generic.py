from fastapi import APIRouter, Depends, UploadFile

from app.deps import require_api_key
from app.schemas.common import OcrMeta
from app.schemas.generic import GenericTextResponse
from app.services import ocr_engine
from app.utils.file_validator import validate_and_read

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(require_api_key)])


@router.post("/text", response_model=GenericTextResponse)
async def ocr_text(file: UploadFile) -> GenericTextResponse:
    """OCR genérico — devuelve texto crudo sin extracción estructurada."""
    content, mimetype = await validate_and_read(file)

    result = ocr_engine.run_ocr_on_file(content=content, mimetype=mimetype)

    return GenericTextResponse(
        text=result.text,
        pages=result.pages,
        meta=OcrMeta(
            engine=result.engine,
            confidence=result.confidence,
            page_count=result.page_count,
            processing_ms=result.processing_ms,
            raw_text_length=len(result.text),
            preprocessed=result.preprocessed,
        ),
    )
