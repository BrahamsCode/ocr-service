from pydantic import BaseModel, Field


class OcrMeta(BaseModel):
    """Metadatos del procesamiento OCR — útil para que el cliente decida si confiar."""

    engine: str = Field(description="Motor OCR usado: tesseract | vision | textract")
    confidence: float = Field(ge=0.0, le=100.0, description="Confianza promedio 0-100")
    page_count: int = Field(ge=1, description="Páginas procesadas")
    processing_ms: int = Field(ge=0, description="Tiempo total en ms")
    raw_text_length: int = Field(ge=0)
    preprocessed: bool = Field(description="Si se aplicó preprocesamiento OpenCV")


class OcrErrorResponse(BaseModel):
    detail: str
    code: str | None = None
