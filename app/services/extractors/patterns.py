"""
Patrones regex compartidos entre extractores.

Todos los patrones están diseñados para texto OCR ruidoso:
  - Toleran espacios extra, saltos de línea, y caracteres confundidos (O/0, I/1)
  - Case-insensitive donde aplica
"""

import re

# Comprobantes electrónicos SUNAT: F001-00000123, B001-12345, FF01-00001234
DOC_NUMBER = re.compile(
    r"\b([A-Z]{1,4}\d{1,3})\s*[-–]\s*(\d{1,8})\b",
    re.IGNORECASE,
)

# RUC: 11 dígitos, empieza con 10, 15, 17, 20
RUC = re.compile(r"\b(1[05-7]|20)\d{9}\b")

# VIN: 17 caracteres alfanuméricos sin I/O/Q
VIN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")

# Placas peruanas: ABC-123 | A1A-123 | AB1-234
PLACA = re.compile(r"\b[A-Z]{1,3}[- ]?\d{3,4}[A-Z]?\b")

# Motor: alfanumérico 8-20 chars después de "Motor:" o "Motor N°"
MOTOR = re.compile(
    r"(?:motor|motor\s*n[°º]?|motor\s*nro\.?)\s*[:\-]?\s*([A-Z0-9.\-]{6,25})",
    re.IGNORECASE,
)

# Fecha (múltiples formatos): 15/04/2026, 2026-04-15, 15-04-2026, 15 Abr 2026
DATE_SLASH  = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
DATE_DASH   = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_SPANISH = re.compile(
    r"\b(\d{1,2})\s+(?:de\s+)?(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)[a-zA-Z]*\s+(?:de\s+)?(\d{4})\b",
    re.IGNORECASE,
)

SPANISH_MONTHS = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}

# Monto: S/ 15,000.00 | USD 15000.00 | 15.000,00
AMOUNT = re.compile(
    r"(?:S/\.?|PEN|USD|\$|US\$)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
    re.IGNORECASE,
)

CURRENCY_HINTS = {
    "PEN": re.compile(r"\bPEN\b|\bS/\.?", re.IGNORECASE),
    "USD": re.compile(r"\bUSD\b|\bUS\$|\bDOLAR", re.IGNORECASE),
}

# Año modelo (debe ser razonable: 1990-2099)
YEAR_MODEL = re.compile(
    r"(?:a[ñn]o|year|modelo)\s*[:\-]?\s*((?:19|20)\d{2})",
    re.IGNORECASE,
)


def normalize_amount(raw: str) -> float | None:
    """Convierte '15,000.00' o '15.000,00' → 15000.00"""
    if not raw:
        return None
    s = raw.strip()

    # Formato con coma decimal: 15.000,00
    if re.search(r",\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None


def normalize_date(match_groups: tuple, fmt: str) -> str | None:
    """Convierte capturas de fecha a YYYY-MM-DD."""
    try:
        if fmt == "slash":
            dd, mm, yyyy = match_groups
            return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        if fmt == "dash":
            yyyy, mm, dd = match_groups
            return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        if fmt == "spanish":
            dd, month_abbr, yyyy = match_groups
            month = SPANISH_MONTHS.get(month_abbr[:3].lower())
            if not month:
                return None
            return f"{yyyy}-{month}-{dd.zfill(2)}"
    except (ValueError, IndexError):
        return None
    return None


def find_first_date(text: str) -> str | None:
    """Encuentra la primera fecha plausible en cualquier formato."""
    if m := DATE_DASH.search(text):
        return normalize_date(m.groups(), "dash")
    if m := DATE_SLASH.search(text):
        return normalize_date(m.groups(), "slash")
    if m := DATE_SPANISH.search(text):
        return normalize_date(m.groups(), "spanish")
    return None
