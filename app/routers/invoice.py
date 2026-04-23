from fastapi import APIRouter, Depends, UploadFile

from app.deps import require_api_key
from app.schemas.common import OcrMeta
from app.schemas.invoice import InvoiceOcrResponse
from app.services import ocr_engine
from app.services.extractors import invoice as invoice_extractor
from app.utils.file_validator import validate_and_read

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(require_api_key)])


@router.post("/invoice", response_model=InvoiceOcrResponse)
async def ocr_invoice(file: UploadFile) -> InvoiceOcrResponse:
    """
    OCR + extracción estructurada de facturas peruanas (SUNAT).

    Acepta PDF o imagen (JPG/PNG/WEBP/TIFF). Si el PDF tiene capa de texto,
    se salta Tesseract y se usa esa capa directamente.
    """
    content, mimetype = await validate_and_read(file)

    result = ocr_engine.run_ocr_on_file(content=content, mimetype=mimetype)
    fields, warnings = invoice_extractor.extract(result.text)

    return InvoiceOcrResponse(
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
