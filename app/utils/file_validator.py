from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


async def validate_and_read(file: UploadFile) -> tuple[bytes, str]:
    """
    Valida tipo MIME y tamaño, devuelve (contenido, mimetype).
    Lanza HTTPException 400 / 413 si falla.
    """
    settings = get_settings()

    mimetype = (file.content_type or "").lower()
    if mimetype not in settings.allowed_mimetypes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tipo de archivo no soportado: {mimetype}. "
                f"Permitidos: {', '.join(settings.allowed_mimetypes)}"
            ),
        )

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo supera el límite de {settings.max_upload_mb} MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    return content, mimetype
