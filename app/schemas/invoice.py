from pydantic import BaseModel, Field

from app.schemas.common import OcrMeta


class InvoiceFields(BaseModel):
    """Campos extraídos de una factura peruana (SUNAT)."""

    document_number: str | None = Field(None, description="Ej: F001-00000123")
    document_type: str | None = Field(None, description="FACTURA | BOLETA | NC | GUIA")
    issue_date: str | None = Field(None, description="YYYY-MM-DD")
    ruc_emisor: str | None = Field(None, description="11 dígitos")
    razon_social_emisor: str | None = None
    ruc_cliente: str | None = None
    razon_social_cliente: str | None = None
    subtotal: float | None = None
    igv: float | None = None
    total: float | None = None
    currency: str | None = Field(None, description="PEN | USD")

    # Vehículo (si aplica)
    vin: str | None = None
    motor: str | None = None
    marca: str | None = None
    modelo: str | None = None
    year_model: int | None = None
    color: str | None = None
    placa: str | None = None


class InvoiceOcrResponse(BaseModel):
    fields: InvoiceFields
    raw_text: str
    meta: OcrMeta
    warnings: list[str] = []
