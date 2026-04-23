# OCR Service

Microservicio OCR para facturas, guías de remisión y fotos de VIN. Pensado para
consumirse desde el sistema Laravel de `proyectoautos` via HTTP.

**Stack**: FastAPI + Tesseract + OpenCV + PyMuPDF · Python 3.12

## Arranque rápido

### Con Docker (recomendado)

```bash
cp .env.example .env
# edita API_KEY con un valor seguro
docker compose up --build -d
```

El servicio queda expuesto en `http://localhost:8000`. Docs interactivas en
`http://localhost:8000/docs`.

### Sin Docker (desarrollo local)

Requiere tener **Tesseract** instalado en el sistema con idioma español:

```bash
# Debian / Ubuntu
sudo apt install -y tesseract-ocr tesseract-ocr-spa poppler-utils

# macOS
brew install tesseract tesseract-lang

# Windows
#   Descargar de https://github.com/UB-Mannheim/tesseract/wiki
#   Añadir C:\Program Files\Tesseract-OCR al PATH
```

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Endpoints

Todos los `/ocr/*` requieren el header `X-API-Key` con el valor configurado en `.env`.

| Método | Ruta | Descripción |
|---|---|---|
| GET  | `/health` | Estado del servicio + versión de Tesseract + idiomas cargados |
| POST | `/ocr/invoice` | OCR + extracción de facturas peruanas (SUNAT) |
| POST | `/ocr/guide` | OCR + extracción de guías de remisión |
| POST | `/ocr/text` | OCR genérico — devuelve texto crudo por página |

### Ejemplo: extraer factura

```bash
curl -X POST http://localhost:8000/ocr/invoice \
  -H "X-API-Key: tu-api-key" \
  -F "file=@factura.pdf"
```

Respuesta:
```json
{
  "fields": {
    "document_number": "F008-00134314",
    "document_type": "FACTURA",
    "issue_date": "2026-04-15",
    "ruc_emisor": "20344877158",
    "razon_social_emisor": "DERCO PERU S.A.",
    "total": 11497.39,
    "currency": "PEN",
    "vin": "LGWEFGA54SA932190",
    "motor": "HFC4GB2.3DS3361747",
    "marca": "JAC",
    "modelo": "JS2"
  },
  "raw_text": "...",
  "meta": {
    "engine": "pdf-text-layer",
    "confidence": 99.0,
    "page_count": 1,
    "processing_ms": 120,
    "raw_text_length": 1850,
    "preprocessed": false
  },
  "warnings": []
}
```

## Arquitectura

```
app/
├── main.py                 # FastAPI + CORS + rate limit
├── config.py               # Settings vía pydantic-settings
├── deps.py                 # Auth por API key
├── routers/                # Endpoints HTTP (uno por tipo de doc)
├── services/
│   ├── ocr_engine.py       # Tesseract wrapper (dataclass OcrResult)
│   ├── pdf_processor.py    # PyMuPDF: text-layer + render pages
│   ├── image_preprocessor.py  # OpenCV: deskew + denoise + threshold
│   └── extractors/         # Regex por tipo de documento
│       ├── patterns.py     # Patrones compartidos (RUC, VIN, fechas)
│       ├── invoice.py
│       └── guide.py
├── schemas/                # Pydantic request/response
└── utils/
    └── file_validator.py   # Tipo MIME + tamaño
```

**Por qué esta separación**: los routers son delgados, los extractores son
independientes del motor OCR. Para agregar Google Vision / AWS Textract más
adelante, solo se añade otra estrategia en `ocr_engine.py` sin tocar nada más.

## PDF con capa de texto vs. escaneo

`pdf_processor.pdf_has_text_layer()` detecta si el PDF ya trae texto extraíble
(los generados por SUNAT/facturadores electrónicos lo traen). En ese caso se
devuelve directamente esa capa — 10-100× más rápido que OCR y **precisión
perfecta**.

Solo cuando el PDF es un escaneo (sin capa de texto) o se sube una imagen, se
corre Tesseract con preprocesado OpenCV.

## Preprocesado OpenCV

Especialmente útil para fotos de celular a guías:

1. **Grayscale** → reduce complejidad
2. **Deskew** (`cv2.minAreaRect`) → corrige inclinación
3. **Denoise** (`cv2.fastNlMeansDenoising`) → limpia ruido conservando bordes
4. **Adaptive threshold gaussiano** → binariza con iluminación desigual

Toggle en `.env` con `PREPROCESS_ENABLED=false` para comparar.

## Seguridad

- **API key obligatoria** en todos los endpoints `/ocr/*` (header `X-API-Key`)
- **Rate limiting** por IP (configurable, default 30/min) — requiere `slowapi`
- **CORS** restringido a orígenes en `ALLOWED_ORIGINS`
- Contenedor corre como **usuario no-root**
- **Validación estricta** de tipo MIME y tamaño antes de procesar

## Integración con Laravel

El cliente Laravel lo encuentras en el proyecto `proyectoautos` en
`app/Services/OcrClient.php`. Recibe un `UploadedFile` y devuelve los campos
extraídos listos para auto-rellenar el form.

## Tests

```bash
pip install pytest
pytest
```

Los tests de extractores no requieren Tesseract instalado — usan texto fijo.

## Deploy en VPS

1. `git clone` + `cp .env.example .env` + configurar API key segura
2. `docker compose up -d --build`
3. Apuntar reverse proxy (Nginx/Caddy) a `http://localhost:8000`
4. HTTPS obligatorio si se llama desde el Laravel en producción

Recomendación: dedicar al menos **1 vCPU + 2 GB RAM** para Tesseract.
