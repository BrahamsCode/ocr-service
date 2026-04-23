import shutil

import pytesseract
from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    tesseract_path = shutil.which("tesseract")
    tesseract_ok = tesseract_path is not None

    version: str | None = None
    langs: list[str] = []
    if tesseract_ok:
        try:
            version = str(pytesseract.get_tesseract_version())
            langs = list(pytesseract.get_languages(config=""))
        except Exception:
            tesseract_ok = False

    return {
        "status": "ok" if tesseract_ok else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "tesseract": {
            "available": tesseract_ok,
            "path": tesseract_path,
            "version": version,
            "languages": langs,
        },
    }
