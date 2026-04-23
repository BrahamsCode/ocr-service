"""
Preprocesamiento de imágenes para mejorar precisión OCR.

Optimizado para dos escenarios:
  1) Documentos escaneados (alta resolución, texto negro sobre fondo claro)
  2) Fotos de celular a guías (sombras, desalineación, baja resolución)
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def preprocess(image: Image.Image) -> Image.Image:
    """Aplica pipeline de preprocesado: grayscale → deskew → denoise → adaptive threshold."""
    cv_img = np.array(image.convert("RGB"))
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = _deskew(gray)
    gray = _denoise(gray)
    binary = _adaptive_threshold(gray)

    return Image.fromarray(binary)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Corrige la inclinación del documento (común en fotos de celular)."""
    coords = np.column_stack(np.where(gray < 127))
    if len(coords) == 0:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    # minAreaRect devuelve ángulos entre -90 y 0; normalizar
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # No rotar si el ángulo es despreciable (evita añadir ruido)
    if abs(angle) < 0.5:
        return gray

    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _denoise(gray: np.ndarray) -> np.ndarray:
    """Reduce ruido preservando bordes del texto."""
    return cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)


def _adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Binariza con umbral adaptativo (mejor que Otsu para iluminación desigual)."""
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15,
    )
