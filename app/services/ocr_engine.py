"""
Wrapper de Tesseract — abstraído detrás de una interfaz para poder sumar
Google Vision / AWS Textract como fallback en una segunda iteración sin
tocar los routers ni extractores.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass

import pytesseract
from PIL import Image

from app.config import get_settings
from app.services import image_preprocessor
from app.services import pdf_processor


@dataclass
class OcrResult:
    text: str
    pages: list[str]
    confidence: float
    page_count: int
    processing_ms: int
    engine: str
    preprocessed: bool


def run_ocr_on_file(content: bytes, mimetype: str, preprocess: bool | None = None) -> OcrResult:
    """
    Punto de entrada único:
      - PDFs: primero intenta extraer capa de texto; si no hay, OCR página por página
      - Imágenes: OCR directo, con preprocesado opcional
    """
    settings = get_settings()
    do_preprocess = settings.preprocess_enabled if preprocess is None else preprocess
    start = time.perf_counter()

    if mimetype == "application/pdf":
        if pdf_processor.pdf_has_text_layer(content):
            pages = pdf_processor.extract_text_layer(content)
            return _build_result(
                pages=pages,
                confidence=99.0,
                preprocessed=False,
                engine="pdf-text-layer",
                start=start,
            )

        images = pdf_processor.pdf_to_images(content)
    else:
        images = [Image.open(io.BytesIO(content))]

    pages: list[str] = []
    confidences: list[float] = []

    for img in images:
        processed = image_preprocessor.preprocess(img) if do_preprocess else img
        text, conf = _ocr_single_image(processed)
        pages.append(text)
        confidences.append(conf)

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return _build_result(
        pages=pages,
        confidence=avg_confidence,
        preprocessed=do_preprocess,
        engine="tesseract",
        start=start,
    )


def _ocr_single_image(image: Image.Image) -> tuple[str, float]:
    """Ejecuta Tesseract y devuelve (texto, confianza promedio)."""
    settings = get_settings()
    tesseract_config = f"--oem {settings.tesseract_oem} --psm {settings.tesseract_psm}"

    text = pytesseract.image_to_string(image, lang=settings.tesseract_lang, config=tesseract_config)

    # Tesseract reporta confianza por palabra; promediamos las > 0 (las -1 son blanks)
    try:
        data = pytesseract.image_to_data(
            image,
            lang=settings.tesseract_lang,
            config=tesseract_config,
            output_type=pytesseract.Output.DICT,
        )
        confidences = [float(c) for c in data["conf"] if c not in ("-1", -1, "")]
        avg = sum(confidences) / len(confidences) if confidences else 0.0
    except Exception:
        avg = 0.0

    return text, avg


def _build_result(
    pages: list[str],
    confidence: float,
    preprocessed: bool,
    engine: str,
    start: float,
) -> OcrResult:
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    full_text = "\n\n".join(pages)
    return OcrResult(
        text=full_text,
        pages=pages,
        confidence=round(confidence, 2),
        page_count=len(pages),
        processing_ms=elapsed_ms,
        engine=engine,
        preprocessed=preprocessed,
    )
