"""Extractor de campos para facturas peruanas (SUNAT)."""

from __future__ import annotations

import re

from app.schemas.invoice import InvoiceFields
from app.services.extractors import patterns as P


def extract(text: str) -> tuple[InvoiceFields, list[str]]:
    """
    Devuelve (campos_extraídos, warnings).
    Warnings son advertencias no bloqueantes (ej: múltiples VINs encontrados).
    """
    warnings: list[str] = []
    upper = text.upper()

    fields = InvoiceFields(
        document_number=_extract_document_number(upper),
        document_type=_extract_document_type(upper),
        issue_date=P.find_first_date(text),
        ruc_emisor=_extract_ruc_emisor(upper),
        razon_social_emisor=_extract_razon_social(upper, role="emisor"),
        ruc_cliente=_extract_ruc_cliente(upper),
        razon_social_cliente=_extract_razon_social(upper, role="cliente"),
        total=_extract_total(text),
        currency=_extract_currency(text),
        vin=_extract_vin(upper, warnings),
        motor=_extract_motor(text),
        marca=_extract_after_label(upper, r"MARCA"),
        modelo=_extract_after_label(upper, r"MODELO"),
        year_model=_extract_year_model(text),
        color=_extract_after_label(upper, r"COLOR"),
        placa=_extract_placa(upper),
    )

    return fields, warnings


def _extract_document_number(upper: str) -> str | None:
    m = P.DOC_NUMBER.search(upper)
    if not m:
        return None
    serie, num = m.group(1), m.group(2)
    return f"{serie.upper()}-{num.zfill(8)}"


def _extract_document_type(upper: str) -> str | None:
    if "FACTURA ELECTR" in upper or re.search(r"\bF\d{2,3}\b", upper):
        return "FACTURA"
    if "BOLETA" in upper:
        return "BOLETA"
    if "NOTA DE CR" in upper or "NOTA CR" in upper:
        return "NC"
    if "GUIA DE REMISI" in upper or "GUÍA DE REMISI" in upper:
        return "GUIA"
    return None


def _extract_ruc_emisor(upper: str) -> str | None:
    """El RUC del emisor suele aparecer arriba, antes que el del cliente."""
    rucs = P.RUC.findall(upper)
    all_rucs = [m.group(0) for m in P.RUC.finditer(upper)]
    return all_rucs[0] if all_rucs else None


def _extract_ruc_cliente(upper: str) -> str | None:
    all_rucs = [m.group(0) for m in P.RUC.finditer(upper)]
    return all_rucs[1] if len(all_rucs) >= 2 else None


def _extract_razon_social(upper: str, role: str) -> str | None:
    """
    Busca líneas cercanas a los keywords 'SEÑOR(ES)' o después del RUC.
    No es perfecto — el OCR fragmenta las razones sociales — pero aproxima.
    """
    if role == "cliente":
        # Patrón: SEÑORES: XXX | ADQUIRIENTE: XXX | CLIENTE: XXX
        m = re.search(
            r"(?:SE[ÑN]OR(?:ES)?|ADQUIRIENTE|CLIENTE|CLIENT)\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{4,80})",
            upper,
        )
        if m:
            return _clean_razon(m.group(1))
    if role == "emisor":
        m = re.search(
            r"(?:RAZ[ÓO]N\s*SOCIAL|EMISOR|PROVEEDOR)\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{4,80})",
            upper,
        )
        if m:
            return _clean_razon(m.group(1))
    return None


def _clean_razon(raw: str) -> str:
    # Cortar al primer salto de línea o punto doble
    cleaned = re.split(r"\n|\s{3,}", raw.strip())[0]
    return cleaned.strip(" .,-")


def _extract_total(text: str) -> float | None:
    """Busca el mayor monto mencionado con símbolo de moneda → asume que es el total."""
    matches = [P.normalize_amount(m.group(1)) for m in P.AMOUNT.finditer(text)]
    valid = [a for a in matches if a is not None and a > 0]
    return max(valid) if valid else None


def _extract_currency(text: str) -> str | None:
    for code, pattern in P.CURRENCY_HINTS.items():
        if pattern.search(text):
            return code
    return None


def _extract_vin(upper: str, warnings: list[str]) -> str | None:
    vins = list({m.group(0) for m in P.VIN.finditer(upper)})
    if not vins:
        return None
    if len(vins) > 1:
        warnings.append(f"Se encontraron {len(vins)} VINs posibles: {vins}. Se usó el primero.")
    return vins[0]


def _extract_motor(text: str) -> str | None:
    m = P.MOTOR.search(text)
    return m.group(1).upper() if m else None


def _extract_year_model(text: str) -> int | None:
    m = P.YEAR_MODEL.search(text)
    if not m:
        return None
    try:
        y = int(m.group(1))
        if 1990 <= y <= 2099:
            return y
    except ValueError:
        pass
    return None


def _extract_after_label(upper: str, label_pattern: str) -> str | None:
    """Extrae el texto que sigue a una etiqueta (ej: MARCA: TOYOTA)."""
    m = re.search(
        rf"{label_pattern}\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .\-]{{2,30}})",
        upper,
    )
    if not m:
        return None
    value = re.split(r"\n|\s{3,}", m.group(1).strip())[0]
    return value.strip(" .,-") or None


def _extract_placa(upper: str) -> str | None:
    # Buscar cerca de "PLACA" para evitar falsos positivos
    m = re.search(r"PLACA\s*[:\-]?\s*([A-Z]{1,3}[- ]?\d{3,4}[A-Z]?)", upper)
    if m:
        return m.group(1).replace(" ", "-").upper()
    return None
