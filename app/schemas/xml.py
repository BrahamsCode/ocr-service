from typing import Any

from pydantic import BaseModel, Field


class XmlParseResponse(BaseModel):
    """Respuesta del parser XML UBL SUNAT (100% estructurado, sin OCR)."""

    document_type: str = Field(description="FACTURA | BOLETA | NOTA_CREDITO | NOTA_DEBITO | GUIA_REMISION")
    fields: dict[str, Any] = Field(description="Campos extraídos estructurados")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Líneas de detalle")
    warnings: list[str] = Field(default_factory=list)
    source: str = Field(default="xml-ubl", description="Indica que vino del XML, no de OCR")
