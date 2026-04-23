"""
Convierte PDFs a imágenes página por página.

Usa PyMuPDF (fitz) como motor principal — más rápido y no requiere poppler externo.
Si un PDF ya tiene capa de texto extraíble, la retorna directamente sin OCR.
"""

from __future__ import annotations

import fitz
from PIL import Image

from app.config import get_settings


def extract_text_layer(pdf_bytes: bytes) -> list[str]:
    """Extrae texto embebido del PDF si existe (PDFs generados digitalmente)."""
    pages_text: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pages_text.append(page.get_text("text") or "")
    return pages_text


def pdf_has_text_layer(pdf_bytes: bytes, min_chars_per_page: int = 50) -> bool:
    """True si todas las páginas tienen texto extraíble (no es un escaneo)."""
    pages = extract_text_layer(pdf_bytes)
    if not pages:
        return False
    return all(len(p.strip()) >= min_chars_per_page for p in pages)


def pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    """Renderiza cada página como PIL.Image en la resolución configurada."""
    settings = get_settings()
    images: list[Image.Image] = []
    zoom = settings.pdf_dpi / 72.0  # 72 dpi es la base de PDF

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages_to_process = min(len(doc), settings.pdf_max_pages)
        matrix = fitz.Matrix(zoom, zoom)

        for i in range(pages_to_process):
            page = doc[i]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)

    return images
