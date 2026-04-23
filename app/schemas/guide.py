from pydantic import BaseModel, Field

from app.schemas.common import OcrMeta


class GuideFields(BaseModel):
    """Campos extraídos de una guía de remisión (Perú SUNAT) o foto de guía."""

    guide_series: str | None = Field(None, description="Ej: T001")
    guide_number: str | None = Field(None, description="Ej: 00001234")
    issue_date: str | None = Field(None, description="YYYY-MM-DD")
    transfer_start_date: str | None = None

    ruc_emisor: str | None = None
    razon_social_emisor: str | None = None
    ruc_destinatario: str | None = None
    razon_social_destinatario: str | None = None

    placa: str | None = Field(None, description="Placa del vehículo transportador")
    licencia_conductor: str | None = None

    direccion_partida: str | None = None
    direccion_llegada: str | None = None

    peso_bruto_kg: float | None = None
    motivo_traslado: str | None = None

    # Vehículo (si es guía de una unidad automotriz)
    vin: str | None = None
    motor: str | None = None


class GuideOcrResponse(BaseModel):
    fields: GuideFields
    raw_text: str
    meta: OcrMeta
    warnings: list[str] = []
