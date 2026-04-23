from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.deps import require_api_key
from app.schemas.xml import XmlParseResponse
from app.services import xml_parser

router = APIRouter(prefix="/parse", tags=["xml"], dependencies=[Depends(require_api_key)])


@router.post("/xml", response_model=XmlParseResponse)
async def parse_xml(file: UploadFile) -> XmlParseResponse:
    """
    Parser de CPE SUNAT en XML UBL 2.1.

    Acepta:
      - Factura (Invoice, type 01)
      - Boleta  (Invoice, type 03)
      - Nota de crédito (CreditNote, type 07)
      - Nota de débito (DebitNote, type 08)
      - Guía de remisión (DespatchAdvice, types 09 remitente y 31 transportista)

    Ventaja vs /ocr/*: 100% de precisión, ~1 ms, sin Tesseract.
    SUNAT entrega siempre el XML junto al PDF en el CPE electrónico.
    """
    mimetype = (file.content_type or "").lower()
    if mimetype not in {"application/xml", "text/xml", "application/octet-stream"} and not (
        file.filename or ""
    ).lower().endswith(".xml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no soportado para XML: {mimetype}. Esperado application/xml",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo XML está vacío.",
        )

    try:
        result = xml_parser.parse(content)
    except xml_parser.XmlParseError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    return XmlParseResponse(
        document_type=result.document_type,
        fields=result.fields,
        items=result.items,
        warnings=result.warnings,
    )
