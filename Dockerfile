FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias del sistema:
#   - tesseract-ocr + tesseract-ocr-spa + tesseract-ocr-eng  → motor OCR
#   - poppler-utils  → fallback por si pdf2image lo necesita
#   - libgl1 / libglib2.0-0  → libs runtime de OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-spa \
      tesseract-ocr-eng \
      poppler-utils \
      libgl1 \
      libglib2.0-0 \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY pyproject.toml ./

# Ejecutar como usuario no-root
RUN groupadd --system ocr && useradd --system --gid ocr --home /srv/app ocr \
    && chown -R ocr:ocr /srv/app
USER ocr

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
