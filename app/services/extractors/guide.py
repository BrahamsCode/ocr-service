"""Extractor para guías de remisión (SUNAT) y fotos de guías."""

from __future__ import annotations

import re

from app.schemas.guide import GuideFields
from app.services.extractors import patterns as P


def extract(text: str) -> tuple[GuideFields, list[str]]:
    warnings: list[str] = []
    upper = text.upper()

    serie, number = _extract_serie_number(upper)

    fields = GuideFields(
        guide_series=serie,
        guide_number=number,
        issue_date=P.find_first_date(text),
        transfer_start_date=_extract_transfer_date(text),
        ruc_emisor=_extract_nth_ruc(upper, 0),
        ruc_destinatario=_extract_nth_ruc(upper, 1),
        razon_social_emisor=_extract_razon_social(upper, role="emisor"),
        razon_social_destinatario=_extract_razon_social(upper, role="destinatario"),
        placa=_extract_placa(upper),
        licencia_conductor=_extract_licencia(upper),
        direccion_partida=_extract_direccion(upper, "PARTIDA"),
        direccion_llegada=_extract_direccion(upper, "LLEGADA"),
        peso_bruto_kg=_extract_peso(text),
        motivo_traslado=_extract_motivo(upper),
        vin=_extract_vin(upper, warnings),
        motor=_extract_motor(text),
    )

    return fields, warnings


def _extract_serie_number(upper: str) -> tuple[str | None, str | None]:
    # Guías suelen ser T001-..., EG01-..., V001-...
    m = P.DOC_NUMBER.search(upper)
    if not m:
        return None, None
    serie, num = m.group(1).upper(), m.group(2).zfill(8)
    return serie, num


def _extract_transfer_date(text: str) -> str | None:
    # Fecha de inicio de traslado suele aparecer con esa etiqueta
    m = re.search(
        r"(?:fecha\s*(?:de\s*)?(?:inicio\s*(?:de\s*)?)?traslado)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    raw = m.group(1)
    if "/" in raw:
        dd, mm, yyyy = raw.split("/")
        return f"{yyyy}-{mm}-{dd}"
    return raw


def _extract_nth_ruc(upper: str, idx: int) -> str | None:
    rucs = [m.group(0) for m in P.RUC.finditer(upper)]
    return rucs[idx] if idx < len(rucs) else None


def _extract_razon_social(upper: str, role: str) -> str | None:
    if role == "emisor":
        m = re.search(
            r"(?:RAZ[ÓO]N\s*SOCIAL|REMITENTE|EMISOR)\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{4,80})",
            upper,
        )
    else:
        m = re.search(
            r"(?:DESTINATARIO|CONSIGNATARIO|ADQUIRIENTE)\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{4,80})",
            upper,
        )
    if not m:
        return None
    return re.split(r"\n|\s{3,}", m.group(1).strip())[0].strip(" .,-") or None


def _extract_placa(upper: str) -> str | None:
    m = re.search(r"PLACA\s*[:\-]?\s*([A-Z]{1,3}[- ]?\d{3,4}[A-Z]?)", upper)
    if m:
        return m.group(1).replace(" ", "-").upper()
    # Fallback: buscar patrón de placa en cualquier lado
    m = P.PLACA.search(upper)
    return m.group(0).replace(" ", "-").upper() if m else None


def _extract_licencia(upper: str) -> str | None:
    m = re.search(
        r"(?:LICENCIA|BREVETE)\s*(?:DE\s*CONDUCIR)?\s*[:\-]?\s*([A-Z0-9\-]{6,12})",
        upper,
    )
    return m.group(1) if m else None


def _extract_direccion(upper: str, tipo: str) -> str | None:
    m = re.search(
        rf"(?:DIRECCI[ÓO]N\s*DE\s*)?{tipo}\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,#°\-]{{6,120}})",
        upper,
    )
    if not m:
        return None
    return re.split(r"\n|\s{3,}", m.group(1).strip())[0].strip(" .,-") or None


def _extract_peso(text: str) -> float | None:
    m = re.search(
        r"(?:peso\s*bruto|peso\s*total)\s*(?:\(?kg\)?)?\s*[:\-]?\s*(\d{1,3}(?:[.,]\d{1,3})?)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return P.normalize_amount(m.group(1))


def _extract_motivo(upper: str) -> str | None:
    m = re.search(
        r"MOTIVO\s*(?:DE)?\s*TRASLADO\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{4,80})",
        upper,
    )
    if not m:
        return None
    return re.split(r"\n|\s{3,}", m.group(1).strip())[0].strip(" .,-") or None


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
