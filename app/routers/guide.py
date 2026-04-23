from fastapi import APIRouter, Depends, UploadFile

from app.deps import require_api_key
from app.schemas.common import OcrMeta
from app.schemas.guide import GuideOcrResponse
from app.services import ocr_engine
from app.services.extractors import guide as guide_extractor
from app.utils.file_validator import validate_and_read

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(require_api_key)])


@router.post("/guide", response_model=GuideOcrResponse)
async def ocr_guide(file: UploadFile) -> GuideOcrResponse:
    """
    OCR + extracción de guías de remisión (SUNAT).

    Optimizado para funcionar con fotos de celular (preprocesado OpenCV
    automático: deskew + denoise + threshold adaptativo).
    """
    content, mimetype = await validate_and_read(file)

    result = ocr_engine.run_ocr_on_file(content=content, mimetype=mimetype)
    fields, warnings = guide_extractor.extract(result.text)

    return GuideOcrResponse(
        fields=fields,
        raw_text=result.text,
        meta=OcrMeta(
            engine=result.engine,
            confidence=result.confidence,
            page_count=result.page_count,
            processing_ms=result.processing_ms,
            raw_text_length=len(result.text),
            preprocessed=result.preprocessed,
        ),
        warnings=warnings,
    )
