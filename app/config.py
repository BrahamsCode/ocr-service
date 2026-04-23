from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "OCR Service"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    api_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["http://localhost", "http://localhost:8080"]
    rate_limit_per_minute: int = 30

    # File constraints
    max_upload_mb: int = 20
    allowed_mimetypes: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/tiff",
    ]

    # OCR
    tesseract_lang: str = "spa+eng"
    tesseract_psm: int = 6  # 6 = Assume uniform block of text
    tesseract_oem: int = 3  # 3 = Default (LSTM + legacy)

    # PDF → image
    pdf_dpi: int = 250
    pdf_max_pages: int = 10

    # Preprocessing toggle (useful to A/B test)
    preprocess_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
