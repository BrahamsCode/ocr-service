"""
Extractor para guías de remisión SUNAT (remitente y transportista) y fotos de guías.

Estrategia: parseo por líneas. PyMuPDF extrae el texto del PDF en orden de
objetos, no visual, así que muchos labels aparecen separados de sus valores.
Armamos un índice de líneas y buscamos el valor en líneas adyacentes cuando
el label no viene acompañado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.guide import GuideFields
from app.services.extractors import patterns as P

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

_RE_RUC_TAIL = re.compile(r"\s*-\s*REGISTRO\s+[ÚU]NICO\s+DE\s+CONTRIBUYENTES.*$", re.IGNORECASE)
_RE_WHITESPACE = re.compile(r"\s+")
_RE_PESO_NUM = re.compile(r"^\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s*$")
_RE_DNI = re.compile(r"\bDOCUMENTO\s+NACIONAL\s+DE\s+IDENTIDAD\s*N[°º]?\s*(\d{8})", re.IGNORECASE)
_RE_LICENCIA = re.compile(
    r"(?:licencia|lincencia|brevete)\s*(?:de\s*conducir)?\s*[:\-]?\s*([A-Z0-9\-]{6,12})",
    re.IGNORECASE,
)
_RE_MTC = re.compile(r"\bMTC\b\s*[-:]?\s*(\d{6,10})", re.IGNORECASE)
_RE_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)?\b", re.IGNORECASE)
_RE_PLACA = re.compile(r"\b[A-Z]{1,3}[- ]?\d{3,4}[A-Z]?\b")
_RE_DOC_REF = re.compile(r"\b([A-Z]{1,4}\d{1,3})\s*[-–]\s*(\d{1,8})\b")
_RE_INDICATOR = re.compile(r"^(SI|NO)\s*$", re.IGNORECASE)
_RE_TIPO_REMITENTE = re.compile(r"GU[ÍI]A\s+DE\s+REMISI[ÓO]N\s+(ELECTR[ÓO]NICA\s+)?REMITENTE", re.IGNORECASE)
_RE_TIPO_TRANSPORTISTA = re.compile(
    r"GU[ÍI]A\s+DE\s+REMISI[ÓO]N\s+(ELECTR[ÓO]NICA\s+)?TRANSPORTISTA", re.IGNORECASE
)


@dataclass
class _Doc:
    """Estructura auxiliar con el texto parseado para lookups rápidos."""

    raw: str
    lines: list[str]
    upper_lines: list[str]

    @classmethod
    def from_text(cls, text: str) -> _Doc:
        lines = [ln.strip() for ln in text.splitlines()]
        return cls(raw=text, lines=lines, upper_lines=[ln.upper() for ln in lines])

    def find_line_containing(self, needle: str, start: int = 0) -> int:
        needle_up = needle.upper()
        for i in range(start, len(self.upper_lines)):
            if needle_up in self.upper_lines[i]:
                return i
        return -1

    def find_line_matching(self, regex: re.Pattern[str], start: int = 0) -> int:
        for i in range(start, len(self.lines)):
            if regex.search(self.lines[i]):
                return i
        return -1


def _clean_razon_social(s: str) -> str | None:
    if not s:
        return None
    s = _RE_RUC_TAIL.sub("", s)
    s = s.strip(" ,:-")  # NO strippar "." al final (puede ser S.A.C., S.A., etc)
    s = _RE_WHITESPACE.sub(" ", s)
    # Si solo quedaron dígitos → probablemente el RUC, no la razón social
    if s.isdigit() or len(s) < 3:
        return None
    return s or None


def _prev_non_empty(doc: _Doc, idx: int, max_back: int = 4) -> list[str]:
    """Devuelve hasta max_back líneas no vacías *previas* a idx (en orden visual)."""
    out: list[str] = []
    i = idx - 1
    while i >= 0 and len(out) < max_back:
        if doc.lines[i]:
            out.append(doc.lines[i])
        i -= 1
    return list(reversed(out))


def _next_non_empty(doc: _Doc, idx: int, max_fwd: int = 6) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    i = idx + 1
    while i < len(doc.lines) and len(out) < max_fwd:
        if doc.lines[i]:
            out.append((i, doc.lines[i]))
        i += 1
    return out


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────


def extract(text: str) -> tuple[GuideFields, list[str]]:
    warnings: list[str] = []
    doc = _Doc.from_text(text)

    tipo = _extract_tipo_guia(doc)
    serie, number = _extract_serie_number(doc)
    issue_date, issue_time = _extract_issue_datetime(doc)

    ruc_emisor = _extract_ruc_emisor(doc)
    razon_emisor = _extract_razon_emisor(doc, tipo, serie, number)

    ruc_destinatario, razon_destinatario = _extract_party(doc, "DESTINATARIO")
    ruc_remitente, razon_remitente = _extract_party(doc, "REMITENTE")

    fields = GuideFields(
        tipo_guia=tipo,
        guide_series=serie,
        guide_number=number,
        issue_date=issue_date,
        issue_time=issue_time,
        transfer_start_date=_extract_transfer_date(text),
        ruc_emisor=ruc_emisor,
        razon_social_emisor=razon_emisor,
        ruc_destinatario=ruc_destinatario,
        razon_social_destinatario=razon_destinatario,
        ruc_remitente=ruc_remitente,
        razon_social_remitente=razon_remitente,
        mtc=_extract_mtc(doc),
        placa=_extract_placa(doc, which="Principal"),
        placa_secundaria=_extract_placa(doc, which="Secundario"),
        licencia_conductor=_extract_licencia(doc),
        dni_conductor=_extract_dni_conductor(doc),
        nombre_conductor=_extract_nombre_conductor(doc),
        direccion_partida=None,  # se asigna abajo en bloque
        direccion_llegada=None,
        peso_bruto_kg=_extract_peso(doc),
        peso_unidad_medida=_extract_peso_unidad(doc),
        motivo_traslado=_extract_motivo(doc),
        documento_relacionado=_extract_documento_relacionado(doc),
        vin=_extract_vin(doc, warnings),
        motor=_extract_motor(text),
    )

    # Direcciones: resolver en bloque (los 2 labels pueden venir juntos tras los valores)
    fields.direccion_partida, fields.direccion_llegada = _extract_direcciones(doc)

    return fields, warnings


# ──────────────────────────────────────────────────────────────
# Specific extractors
# ──────────────────────────────────────────────────────────────


def _extract_tipo_guia(doc: _Doc) -> str | None:
    if _RE_TIPO_TRANSPORTISTA.search(doc.raw):
        return "TRANSPORTISTA"
    if _RE_TIPO_REMITENTE.search(doc.raw):
        return "REMITENTE"
    return None


def _extract_serie_number(doc: _Doc) -> tuple[str | None, str | None]:
    # Buscar patrón N° EG03 - 00000263 o T001-00001234
    for line in doc.lines:
        if not line:
            continue
        up = line.upper()
        # Descartar líneas que sean "documentos relacionados"
        if "DOCUMENTOS RELACIONADOS" in up:
            continue
        m = _RE_DOC_REF.search(line)
        if m and re.search(r"\bN[°º]\s*" + re.escape(m.group(0)), line, re.IGNORECASE):
            return m.group(1).upper(), m.group(2).zfill(8)
    # Fallback: primer match del patrón global
    m = P.DOC_NUMBER.search(doc.raw)
    if m:
        return m.group(1).upper(), m.group(2).zfill(8)
    return None, None


def _extract_issue_datetime(doc: _Doc) -> tuple[str | None, str | None]:
    # "Fecha y hora de emisión: 23/02/2026 05:25 PM" o en líneas separadas
    date = None
    time = None
    # Buscar línea con fecha+hora
    for line in doc.lines:
        m_date = P.DATE_SLASH.search(line) or P.DATE_DASH.search(line)
        if not m_date:
            continue
        # Si el label es de inicio de traslado, saltar — eso va en otro campo
        if re.search(r"inicio\s*(de\s*)?traslado", line, re.IGNORECASE):
            continue
        # Tiene formato slash o dash?
        if "/" in m_date.group(0):
            date = P.normalize_date(m_date.groups(), "slash")
        else:
            date = P.normalize_date(m_date.groups(), "dash")
        # Buscar hora en la misma línea
        m_t = _RE_TIME.search(line)
        if m_t:
            hh, mm, ampm = m_t.group(1), m_t.group(2), (m_t.group(3) or "").upper()
            h = int(hh)
            if ampm == "PM" and h < 12:
                h += 12
            if ampm == "AM" and h == 12:
                h = 0
            time = f"{h:02d}:{mm}"
        break
    # Si no hay fecha, usar find_first_date
    if not date:
        date = P.find_first_date(doc.raw)
    return date, time


def _extract_transfer_date(text: str) -> str | None:
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


def _extract_ruc_emisor(doc: _Doc) -> str | None:
    # El RUC del emisor suele aparecer junto a "RUC N°" en el header
    for line in doc.lines[:10]:
        m = re.search(r"RUC\s*N[°º]?\s*(\d{11})", line, re.IGNORECASE)
        if m:
            return m.group(1)
    # Fallback: primer RUC del documento
    m = P.RUC.search(doc.raw)
    return m.group(0) if m else None


def _extract_razon_emisor(
    doc: _Doc,
    tipo: str | None,
    serie: str | None,
    number: str | None,
) -> str | None:
    """
    En guía electrónica SUNAT, la razón social del emisor (transportista o remitente
    principal) suele venir como línea aislada justo después del bloque del número
    de documento (línea que matchea 'N° EG03 - 00000263').
    """
    if serie and number:
        # Localizar la línea del número de doc
        needle_re = re.compile(
            rf"\bN[°º]\s*{re.escape(serie)}\s*-\s*0*{int(number)}\b", re.IGNORECASE
        )
        idx = doc.find_line_matching(needle_re)
        if idx >= 0:
            for _, next_line in _next_non_empty(doc, idx, max_fwd=4):
                up = next_line.upper()
                # Saltar líneas que son claramente labels/meta
                if any(s in up for s in ("FECHA", "R.U.C", "RUC ", "GU[IÍ]A", "EMISI")):
                    continue
                cleaned = _clean_razon_social(next_line)
                if cleaned:
                    return cleaned
    return None


def _extract_party(doc: _Doc, role: str) -> tuple[str | None, str | None]:
    """
    role ∈ {"DESTINATARIO", "REMITENTE"}. Busca 'Datos del <role>:' y extrae
    RUC + razón social, ya sea en la misma línea o en la siguiente no vacía.
    """
    label_re = re.compile(rf"DATOS\s+DEL\s+{role}\s*[:\-]?\s*(.*)$", re.IGNORECASE)
    for i, line in enumerate(doc.lines):
        m = label_re.search(line)
        if not m:
            continue
        inline = m.group(1).strip()
        chunk = inline
        if not chunk:
            # Buscar en las próximas líneas no vacías
            for _, nxt in _next_non_empty(doc, i, max_fwd=6):
                # Saltar si es label de otra sección
                if re.match(r"^(DATOS\s+DEL|FECHA|MTC|GU[IÍ]A|BIENES|N[UÚ]MERO)", nxt.upper()):
                    continue
                chunk = nxt
                break
        if not chunk:
            continue
        m_ruc = P.RUC.search(chunk)
        ruc = m_ruc.group(0) if m_ruc else None
        # Razón social: el texto antes del RUC, o si no hay, todo el chunk
        raw_rs = chunk
        if m_ruc:
            raw_rs = chunk[: m_ruc.start()].rstrip(" -")
        return ruc, _clean_razon_social(raw_rs)
    return None, None


def _extract_mtc(doc: _Doc) -> str | None:
    for line in doc.lines:
        m = _RE_MTC.search(line)
        if m:
            return m.group(1)
    return None


def _extract_placa(doc: _Doc, which: str) -> str | None:
    """
    Busca línea con 'Principal:' o 'Secundario 1:' y toma la primera placa
    que aparezca después.
    """
    label_re = re.compile(rf"^\s*{which}\s*(?:\d+)?\s*:", re.IGNORECASE)
    for i, line in enumerate(doc.lines):
        if not label_re.search(line):
            continue
        inline = line.split(":", 1)[1].strip() if ":" in line else ""
        m = _RE_PLACA.search(inline)
        if m:
            return m.group(0).replace(" ", "-").upper()
        # Buscar en las siguientes líneas
        for _, nxt in _next_non_empty(doc, i, max_fwd=5):
            if re.match(r"^(SECUNDARIO|PRINCIPAL|N[UÚ]MERO|ENTIDAD|DATOS)", nxt.upper()):
                break
            m = _RE_PLACA.search(nxt)
            if m and not nxt.strip().isdigit():
                return m.group(0).replace(" ", "-").upper()
    # Fallback solo para Principal
    if which.upper() == "PRINCIPAL":
        idx = doc.find_line_containing("Placa")
        if idx >= 0:
            for _, nxt in _next_non_empty(doc, idx, max_fwd=4):
                m = _RE_PLACA.search(nxt)
                if m:
                    return m.group(0).replace(" ", "-").upper()
    return None


def _extract_licencia(doc: _Doc) -> str | None:
    for line in doc.lines:
        m = _RE_LICENCIA.search(line)
        if m:
            return m.group(1).upper()
    return None


def _extract_dni_conductor(doc: _Doc) -> str | None:
    m = _RE_DNI.search(doc.raw)
    return m.group(1) if m else None


def _extract_nombre_conductor(doc: _Doc) -> str | None:
    # Línea típica: "APAZA CALLA CAIN OLVER - DOCUMENTO NACIONAL DE IDENTIDAD N° 42776117"
    for line in doc.lines:
        m = re.search(
            r"^([A-ZÑÁÉÍÓÚ' .]{6,80})\s*-\s*DOCUMENTO\s+NACIONAL\s+DE\s+IDENTIDAD",
            line,
            re.IGNORECASE,
        )
        if m:
            name = re.sub(r"\s+", " ", m.group(1).strip(" .,:-"))
            return name.upper() if name else None
    # Fallback: línea después de "Datos de los conductores:"
    idx = doc.find_line_containing("Datos de los conductores")
    if idx >= 0:
        for _, nxt in _next_non_empty(doc, idx, max_fwd=4):
            up = nxt.upper()
            if up.startswith("PRINCIPAL:"):
                inline = nxt.split(":", 1)[1].strip()
                m = re.search(r"^([A-ZÑÁÉÍÓÚ' .]+)", inline)
                if m and len(m.group(1).strip()) >= 6:
                    return re.sub(r"\s+", " ", m.group(1).strip(" .,:-")).upper()
    return None


def _extract_direcciones(doc: _Doc) -> tuple[str | None, str | None]:
    """
    Devuelve (partida, llegada).

    En SUNAT text-layer los 2 labels 'Punto de llegada:' / 'Punto de Partida:'
    vienen uno tras otro al final del bloque, y las direcciones vienen ANTES
    en el mismo orden. Estrategia:
      1) Si ambos labels aparecen inline con valor → usar eso.
      2) Si vienen labels-sólo consecutivos: juntar todos los bloques de
         dirección previos (contiguos entre labels anteriores y los nuestros)
         y asociarlos por orden: bloque[0]=llegada, bloque[1]=partida.
      3) Fallback a formato 'Dirección de <tipo>:' inline.
    """
    partida = llegada = None

    # 1) Inline directo
    inline_partida = _find_inline_direccion(doc, "partida")
    inline_llegada = _find_inline_direccion(doc, "llegada")
    if inline_partida:
        partida = inline_partida
    if inline_llegada:
        llegada = inline_llegada
    if partida and llegada:
        return partida, llegada

    # 2) Labels-sólo consecutivos (caso SUNAT)
    idx_llegada = _find_label_only(doc, "llegada")
    idx_partida = _find_label_only(doc, "partida")

    if idx_llegada >= 0 or idx_partida >= 0:
        first_idx = min(i for i in (idx_llegada, idx_partida) if i >= 0)
        # Juntar líneas desde arriba del primer label que sean direcciones
        blocks = _address_blocks_before(doc, first_idx)
        # Orden en raw coincide con orden de labels.
        # Si el primer label encontrado es llegada → blocks[0]=llegada, blocks[1]=partida.
        # Si primer label es partida → blocks[0]=partida, blocks[1]=llegada.
        if idx_llegada >= 0 and idx_partida >= 0:
            if idx_llegada < idx_partida:
                llegada = llegada or (blocks[0] if len(blocks) >= 1 else None)
                partida = partida or (blocks[1] if len(blocks) >= 2 else None)
            else:
                partida = partida or (blocks[0] if len(blocks) >= 1 else None)
                llegada = llegada or (blocks[1] if len(blocks) >= 2 else None)
        elif idx_llegada >= 0:
            llegada = llegada or (blocks[0] if blocks else None)
        elif idx_partida >= 0:
            partida = partida or (blocks[0] if blocks else None)

    # 3) Legacy "Dirección de partida/llegada: ..."
    if not partida:
        m = re.search(
            r"direcci[óo]n\s+de\s+partida\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,#°\-/]{6,200})",
            doc.raw, re.IGNORECASE,
        )
        if m:
            partida = _clean_address(m.group(1))
    if not llegada:
        m = re.search(
            r"direcci[óo]n\s+de\s+llegada\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,#°\-/]{6,200})",
            doc.raw, re.IGNORECASE,
        )
        if m:
            llegada = _clean_address(m.group(1))

    return partida, llegada


def _find_inline_direccion(doc: _Doc, tipo: str) -> str | None:
    label_re = re.compile(rf"^\s*punto\s+de\s+{tipo}\s*[:\-]\s*(.+)$", re.IGNORECASE)
    for line in doc.lines:
        m = label_re.search(line)
        if m:
            val = m.group(1).strip()
            if val and _looks_like_address(val):
                return _clean_address(val)
    return None


def _find_label_only(doc: _Doc, tipo: str) -> int:
    """Retorna el índice de la línea que contiene solo el label 'Punto de <tipo>:'."""
    label_re = re.compile(rf"^\s*punto\s+de\s+{tipo}\s*[:\-]?\s*$", re.IGNORECASE)
    for i, line in enumerate(doc.lines):
        if label_re.search(line):
            return i
    return -1


def _address_blocks_before(doc: _Doc, idx: int) -> list[str]:
    """
    Agrupa líneas contiguas 'address-like' que aparecen antes de idx.
    Un bloque termina cuando se encuentra una línea vacía o una línea-label.
    """
    # Retroceder recolectando líneas no vacías hasta encontrar un label/separador
    collected: list[str] = []
    i = idx - 1
    while i >= 0:
        line = doc.lines[i]
        if not line:
            i -= 1
            continue
        up = line.upper()
        # Detener en labels conocidos / cabezales
        if re.match(
            r"^(FECHA|DATOS|BIENES|PUNTO|N[UÚ]MERO|MTC|INDICADOR|RUC|GU[IÍ]A|R\.U\.C|DOCUMENTOS)",
            up,
        ):
            break
        if _RE_INDICATOR.match(line):
            break
        collected.append(line)
        i -= 1
    collected.reverse()  # orden visual

    # Agrupar en bloques: una línea que empieza con AV./JR./CALLE/CAR./OTR. inicia bloque
    blocks: list[list[str]] = []
    for ln in collected:
        up = ln.upper().strip()
        starts_address = bool(
            re.match(r"^(AV\.|AVENIDA|JR\.|JIRON|CALLE|CAR\.|CARRETERA|OTR\.|NRO|PSJE|PROLONG|PROL\.|MZ\.)", up)
        )
        if starts_address or not blocks:
            blocks.append([ln])
        else:
            blocks[-1].append(ln)

    return [_clean_address(" ".join(b)) for b in blocks if b]


def _looks_like_address(s: str) -> bool:
    up = s.upper()
    if len(s) < 10:
        return False
    keywords = ("AV.", "AVENIDA", "JR.", "CALLE", "CAR.", "CARRETERA", "OTR.", "NRO", "KM.")
    return any(k in up for k in keywords) or re.search(r"\d", s) is not None


def _collect_address_from_lines(lines: list[str]) -> str | None:
    candidates: list[str] = []
    for ln in lines:
        up = ln.upper()
        # Descartar labels / cosas que no son direcciones
        if re.match(r"^(FECHA|DATOS|BIENES|PUNTO|N[UÚ]MERO|MTC|INDICADOR|RUC|GU[IÍ]A)", up):
            continue
        if _RE_INDICATOR.match(ln):
            continue
        if _looks_like_address(ln) or (candidates and len(ln) <= 40):
            candidates.append(ln)
    if not candidates:
        return None
    joined = " ".join(candidates)
    return _clean_address(joined)


def _clean_address(s: str) -> str:
    s = _RE_WHITESPACE.sub(" ", s).strip(" .,:-")
    return s


def _extract_peso(doc: _Doc) -> float | None:
    """
    Casos:
      "Peso Bruto total de la carga: 3,750"
      "Peso Bruto total de la carga:"
      (otras líneas)
      "KGM"
      "3,750"
    """
    idx = doc.find_line_containing("Peso Bruto")
    if idx < 0:
        idx = doc.find_line_containing("Peso total")
    if idx < 0:
        return None
    line = doc.lines[idx]
    # Primero probar inline
    m = re.search(r"[:\-]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)", line)
    if m:
        return _peso_to_kg(m.group(1))
    # Buscar en las próximas líneas el primer número razonable
    for _, nxt in _next_non_empty(doc, idx, max_fwd=6):
        m2 = _RE_PESO_NUM.match(nxt)
        if m2:
            return _peso_to_kg(m2.group(1))
    return None


def _peso_to_kg(raw: str) -> float | None:
    """
    '3,750' en Perú suele ser 3750 (separador de miles, no decimal).
    Pero si es '3,75' o '3.75' puede ser decimal — distinguir por cantidad de dígitos.
    """
    s = raw.strip()
    # Si tiene coma y exactamente 3 dígitos decimales → separador de miles
    m_thousands = re.fullmatch(r"(\d{1,3})[.,](\d{3})", s)
    if m_thousands:
        return float(m_thousands.group(1) + m_thousands.group(2))
    # Si tiene coma o punto con 1-2 decimales → decimal real
    return P.normalize_amount(s)


def _extract_peso_unidad(doc: _Doc) -> str | None:
    idx = doc.find_line_containing("Unidad de Medida del Peso")
    if idx >= 0:
        for _, nxt in _next_non_empty(doc, idx, max_fwd=4):
            up = nxt.upper().strip()
            if up in {"KGM", "KG", "TNE", "LBR", "GRM"}:
                return up
    # Búsqueda libre
    m = re.search(r"\b(KGM|TNE|KG|LBR)\b", doc.raw, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _extract_motivo(doc: _Doc) -> str | None:
    m = re.search(
        r"MOTIVO\s*(?:DE)?\s*TRASLADO\s*[:\-]?\s*([A-ZÑÁÉÍÓÚ0-9 .,&\-]{3,80})",
        doc.raw,
        re.IGNORECASE,
    )
    if not m:
        return None
    val = re.split(r"\n|\s{3,}", m.group(1).strip())[0].strip(" .,-")
    return val.upper() or None


def _extract_documento_relacionado(doc: _Doc) -> str | None:
    idx = doc.find_line_containing("Documentos Relacionados")
    if idx < 0:
        idx = doc.find_line_containing("Guía de Remisión Remitente")
    if idx < 0:
        return None
    # Buscar patrón serie-número en las próximas líneas
    for j in range(idx, min(idx + 4, len(doc.lines))):
        m = _RE_DOC_REF.search(doc.lines[j])
        if m:
            return f"{m.group(1).upper()}-{m.group(2).zfill(8)}"
    return None


def _extract_vin(doc: _Doc, warnings: list[str]) -> str | None:
    vins = list({m.group(0) for m in P.VIN.finditer(doc.raw.upper())})
    if not vins:
        return None
    if len(vins) > 1:
        warnings.append(f"Se encontraron {len(vins)} VINs posibles: {vins}. Se usó el primero.")
    return vins[0]


def _extract_motor(text: str) -> str | None:
    m = P.MOTOR.search(text)
    return m.group(1).upper() if m else None
