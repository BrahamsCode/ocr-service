from pydantic import BaseModel, Field

from app.schemas.common import OcrMeta


class GuideFields(BaseModel):
    """Campos extraídos de una guía de remisión (Perú SUNAT) o foto de guía."""

    tipo_guia: str | None = Field(None, description="REMITENTE | TRANSPORTISTA")
    guide_series: str | None = Field(None, description="Ej: T001, EG03")
    guide_number: str | None = Field(None, description="Ej: 00001234")
    issue_date: str | None = Field(None, description="YYYY-MM-DD")
    issue_time: str | None = Field(None, description="HH:MM (24h) si está disponible")
    transfer_start_date: str | None = None

    ruc_emisor: str | None = None
    razon_social_emisor: str | None = None
    ruc_destinatario: str | None = None
    razon_social_destinatario: str | None = None
    ruc_remitente: str | None = Field(None, description="En guía-transportista, el remitente original")
    razon_social_remitente: str | None = None

    # Transporte
    mtc: str | None = Field(None, description="Número MTC del transportista")
    placa: str | None = Field(None, description="Placa del vehículo principal")
    placa_secundaria: str | None = Field(None, description="Placa del vehículo secundario (si aplica)")
    licencia_conductor: str | None = None
    dni_conductor: str | None = None
    nombre_conductor: str | None = None

    # Traslado
    direccion_partida: str | None = None
    direccion_llegada: str | None = None
    peso_bruto_kg: float | None = None
    peso_unidad_medida: str | None = Field(None, description="KGM | TNE | etc")
    motivo_traslado: str | None = None
    documento_relacionado: str | None = Field(None, description="Serie-número de otra guía/factura referida")

    # Vehículo (si la guía transporta una unidad automotriz)
    vin: str | None = None
    motor: str | None = None


class GuideOcrResponse(BaseModel):
    fields: GuideFields
    raw_text: str
    meta: OcrMeta
    warnings: list[str] = []
