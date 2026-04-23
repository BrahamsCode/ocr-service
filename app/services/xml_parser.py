"""
Parser de CPE SUNAT en XML UBL 2.1.

Casos soportados:
  - Factura (Invoice, type 01)
  - Boleta  (Invoice, type 03)
  - Nota de crédito (CreditNote, type 07)
  - Nota de débito (DebitNote, type 08)
  - Guía de remisión (DespatchAdvice, types 09 y 31)

El XML viene del sistema SUNAT/facturador electrónico y **ya está estructurado**,
así que se extraen los campos con 100% de precisión sin pasar por OCR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET

# Namespaces UBL 2.1 usados por SUNAT
NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "DebitNote": "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
    "DespatchAdvice": "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
}

_VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
_MOTOR_RE = re.compile(
    r"(?:motor|motor\s*n[°º]?)\s*[:\-]?\s*([A-Z0-9.\-]{6,25})", re.IGNORECASE
)
_MARCA_RE = re.compile(r"\bmarca\s*[:\-]?\s*([A-ZÑ][A-ZÑ0-9]{1,14})\b", re.IGNORECASE)
_MODELO_RE = re.compile(r"\bmodelo\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{1,14})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:a[ñn]o|year)\s*(?:modelo)?\s*[:\-]?\s*((?:19|20)\d{2})", re.IGNORECASE)
_COLOR_RE = re.compile(r"\bcolor\s*[:\-]?\s*([A-ZÑ]{3,15})", re.IGNORECASE)


class XmlParseError(Exception):
    pass


@dataclass
class UblResult:
    document_type: str  # FACTURA | BOLETA | NOTA_CREDITO | NOTA_DEBITO | GUIA_REMISION
    fields: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────


def parse(xml_bytes: bytes) -> UblResult:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise XmlParseError(f"XML inválido: {e}") from e

    tag = _local_tag(root.tag)

    if tag == "Invoice":
        return _parse_invoice(root)
    if tag == "CreditNote":
        return _parse_credit_note(root)
    if tag == "DebitNote":
        return _parse_debit_note(root)
    if tag == "DespatchAdvice":
        return _parse_despatch_advice(root)

    raise XmlParseError(
        f"Raíz XML no reconocida: {tag}. Esperado: Invoice | CreditNote | DebitNote | DespatchAdvice"
    )


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────


def _text(el: ET.Element | None, xpath: str) -> str | None:
    if el is None:
        return None
    found = el.find(xpath, NS)
    if found is None or found.text is None:
        return None
    txt = found.text.strip()
    return txt or None


def _attr(el: ET.Element | None, xpath: str, attr: str) -> str | None:
    if el is None:
        return None
    found = el.find(xpath, NS)
    if found is None:
        return None
    return found.get(attr)


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _party_info(party: ET.Element | None) -> tuple[str | None, str | None, str | None]:
    """Extrae (ruc, razón social, dirección) de <cac:Party>."""
    if party is None:
        return None, None, None
    ruc = _text(party, ".//cbc:ID[@schemeID='6']") or _text(party, ".//cac:PartyIdentification/cbc:ID")
    razon = (
        _text(party, ".//cac:PartyLegalEntity/cbc:RegistrationName")
        or _text(party, ".//cac:PartyName/cbc:Name")
    )
    direccion = (
        _text(party, ".//cac:PartyLegalEntity/cac:RegistrationAddress/cbc:StreetName")
        or _text(party, ".//cac:RegistrationAddress/cac:AddressLine/cbc:Line")
        or _text(party, ".//cac:Address/cbc:StreetName")
    )
    return ruc, razon, direccion


def _extract_vehicle_from_text(text: str) -> dict[str, Any]:
    """Busca VIN/motor/marca/modelo/año/color en la descripción de productos."""
    out: dict[str, Any] = {}
    if not text:
        return out
    if m := _VIN_RE.search(text.upper()):
        out["vin"] = m.group(0)
    if m := _MOTOR_RE.search(text):
        out["motor"] = m.group(1).upper()
    if m := _MARCA_RE.search(text):
        out["marca"] = m.group(1).strip().upper()
    if m := _MODELO_RE.search(text):
        out["modelo"] = m.group(1).strip().upper()
    if m := _YEAR_RE.search(text):
        out["year_model"] = int(m.group(1))
    if m := _COLOR_RE.search(text):
        out["color"] = m.group(1).strip().upper()
    return out


# ────────────────────────────────────────────────────────────
# Invoice / CreditNote / DebitNote
# ────────────────────────────────────────────────────────────


def _parse_invoice(root: ET.Element) -> UblResult:
    return _parse_billing_doc(root, "FACTURA_O_BOLETA", line_tag="cac:InvoiceLine")


def _parse_credit_note(root: ET.Element) -> UblResult:
    return _parse_billing_doc(root, "NOTA_CREDITO", line_tag="cac:CreditNoteLine")


def _parse_debit_note(root: ET.Element) -> UblResult:
    return _parse_billing_doc(root, "NOTA_DEBITO", line_tag="cac:DebitNoteLine")


def _parse_billing_doc(root: ET.Element, doc_kind: str, *, line_tag: str) -> UblResult:
    warnings: list[str] = []

    # ID del documento, ej "F008-00134314"
    doc_id = _text(root, "cbc:ID")
    serie = number = None
    if doc_id and "-" in doc_id:
        serie, _, number = doc_id.partition("-")
        number = number.zfill(8)

    # Tipo específico (01=Factura, 03=Boleta, 07=Nota Crédito, 08=Nota Débito)
    type_code = _text(root, "cbc:InvoiceTypeCode") or _text(root, "cbc:CreditNoteTypeCode") or _text(
        root, "cbc:DebitNoteTypeCode"
    )
    tipo_name = {
        "01": "FACTURA",
        "03": "BOLETA",
        "07": "NOTA_CREDITO",
        "08": "NOTA_DEBITO",
    }.get(type_code or "", doc_kind)

    issue_date = _text(root, "cbc:IssueDate")
    issue_time = _text(root, "cbc:IssueTime")
    currency = _text(root, "cbc:DocumentCurrencyCode")

    # Partes
    supplier = root.find("cac:AccountingSupplierParty/cac:Party", NS)
    customer = root.find("cac:AccountingCustomerParty/cac:Party", NS)
    ruc_emisor, razon_emisor, direccion_emisor = _party_info(supplier)
    ruc_cliente, razon_cliente, direccion_cliente = _party_info(customer)

    # Totales
    totals = root.find("cac:LegalMonetaryTotal", NS)
    total = _to_float(_text(totals, "cbc:PayableAmount"))
    subtotal = _to_float(_text(totals, "cbc:LineExtensionAmount"))
    descuento = _to_float(_text(totals, "cbc:AllowanceTotalAmount"))

    # IGV, ISC, otros impuestos
    igv = isc = None
    for tax_total in root.findall("cac:TaxTotal", NS):
        tax_amount = _to_float(_text(tax_total, "cbc:TaxAmount"))
        for subtotal_el in tax_total.findall("cac:TaxSubtotal", NS):
            tax_id = _text(subtotal_el, "cac:TaxCategory/cac:TaxScheme/cbc:ID")
            amt = _to_float(_text(subtotal_el, "cbc:TaxAmount"))
            if tax_id == "1000":
                igv = amt
            elif tax_id == "2000":
                isc = amt
        if igv is None and tax_amount is not None:
            igv = tax_amount

    # Líneas de detalle (productos / servicios)
    items: list[dict[str, Any]] = []
    vehicle_fields: dict[str, Any] = {}
    for line in root.findall(line_tag, NS):
        desc = _text(line, "cac:Item/cbc:Description")
        qty = _to_float(_text(line, "cbc:InvoicedQuantity") or _text(line, "cbc:CreditedQuantity") or _text(line, "cbc:DebitedQuantity"))
        unit_price = _to_float(_text(line, "cac:Price/cbc:PriceAmount"))
        line_total = _to_float(_text(line, "cbc:LineExtensionAmount"))
        codigo = _text(line, "cac:Item/cac:SellersItemIdentification/cbc:ID")
        item = {
            "codigo": codigo,
            "descripcion": desc,
            "cantidad": qty,
            "precio_unitario": unit_price,
            "total": line_total,
        }
        items.append(item)
        # Si la descripción contiene VIN / marca / modelo, lo capturamos
        if desc:
            vehicle_fields.update(_extract_vehicle_from_text(desc))

    fields = {
        "document_number": doc_id,
        "serie": serie,
        "number": number,
        "document_type": tipo_name,
        "document_type_code": type_code,
        "issue_date": issue_date,
        "issue_time": issue_time,
        "currency": currency,
        "ruc_emisor": ruc_emisor,
        "razon_social_emisor": razon_emisor,
        "direccion_emisor": direccion_emisor,
        "ruc_cliente": ruc_cliente,
        "razon_social_cliente": razon_cliente,
        "direccion_cliente": direccion_cliente,
        "subtotal": subtotal,
        "igv": igv,
        "isc": isc,
        "descuento_total": descuento,
        "total": total,
        **vehicle_fields,
    }

    return UblResult(document_type=tipo_name, fields=fields, items=items, warnings=warnings)


# ────────────────────────────────────────────────────────────
# DespatchAdvice (guía de remisión)
# ────────────────────────────────────────────────────────────


def _parse_despatch_advice(root: ET.Element) -> UblResult:
    warnings: list[str] = []

    doc_id = _text(root, "cbc:ID")
    serie = number = None
    if doc_id and "-" in doc_id:
        serie, _, number = doc_id.partition("-")
        number = number.zfill(8)

    # Tipo: 09 = guía remitente, 31 = guía transportista
    type_code = _text(root, "cbc:DespatchAdviceTypeCode")
    tipo_guia = {"09": "REMITENTE", "31": "TRANSPORTISTA"}.get(type_code or "")

    issue_date = _text(root, "cbc:IssueDate")
    issue_time = _text(root, "cbc:IssueTime")

    # Partes
    despatch = root.find("cac:DespatchSupplierParty/cac:Party", NS)
    delivery = root.find("cac:DeliveryCustomerParty/cac:Party", NS)
    seller_supplier = root.find("cac:SellerSupplierParty/cac:Party", NS)
    ruc_emisor, razon_emisor, _ = _party_info(despatch)
    ruc_destinatario, razon_destinatario, _ = _party_info(delivery)
    ruc_remitente, razon_remitente, _ = _party_info(seller_supplier)

    # Shipment
    shipment = root.find("cac:Shipment", NS)
    motivo = _text(shipment, "cbc:HandlingCode")  # 01=venta, 02=compra, etc
    motivo_descripcion = _text(shipment, "cbc:Information")
    peso = _to_float(_text(shipment, "cbc:GrossWeightMeasure"))
    peso_unidad = _attr(shipment, "cbc:GrossWeightMeasure", "unitCode")

    transfer_start_date = _text(shipment, ".//cac:ShipmentStage/cbc:TransportModeCode/../../cbc:TransitDirectionCode/..")
    transfer_start_date = _text(shipment, "cac:ShipmentStage/cac:TransitPeriod/cbc:StartDate") or _text(
        shipment, ".//cac:TransitPeriod/cbc:StartDate"
    )

    # Direcciones de partida / llegada
    direccion_partida = _address_text(
        shipment.find("cac:OriginAddress", NS) if shipment is not None else None
    ) or _address_text(shipment.find(".//cac:ShipmentStage/cac:LoadingLocation/cac:Address", NS) if shipment is not None else None)
    direccion_llegada = _address_text(
        shipment.find("cac:Delivery/cac:DeliveryAddress", NS) if shipment is not None else None
    ) or _address_text(shipment.find(".//cac:ShipmentStage/cac:UnloadingLocation/cac:Address", NS) if shipment is not None else None)

    # Transporte (vehículos, conductores)
    placas: list[str] = []
    conductores: list[dict[str, str | None]] = []
    licencias: list[str] = []
    if shipment is not None:
        for stage in shipment.findall("cac:ShipmentStage", NS):
            for vehicle in stage.findall(".//cac:TransportMeans//cac:RoadTransport", NS):
                p = _text(vehicle, "cbc:LicensePlateID")
                if p:
                    placas.append(p.upper())
            for vehicle in stage.findall(".//cac:TransportEquipment", NS):
                p = _text(vehicle, "cbc:ID")
                if p and p.upper() not in placas:
                    placas.append(p.upper())
            for driver in stage.findall("cac:DriverPerson", NS):
                nombre_parts = [
                    _text(driver, "cbc:FirstName"),
                    _text(driver, "cbc:FamilyName"),
                    _text(driver, "cbc:MiddleName"),
                ]
                nombre = " ".join(p for p in nombre_parts if p).strip() or None
                dni = _text(driver, "cbc:ID")
                lic = _text(driver, "cac:IdentityDocumentReference/cbc:ID") or _text(
                    driver, "cbc:JobTitle"
                )
                conductores.append({"nombre": nombre, "dni": dni, "licencia": lic})
                if lic:
                    licencias.append(lic)

    # Líneas (bienes transportados)
    items: list[dict[str, Any]] = []
    vehicle_fields: dict[str, Any] = {}
    for line in root.findall("cac:DespatchLine", NS):
        desc = _text(line, "cac:Item/cbc:Description") or _text(line, "cac:Item/cbc:Name")
        qty = _to_float(_text(line, "cbc:DeliveredQuantity"))
        items.append({"descripcion": desc, "cantidad": qty})
        if desc:
            vehicle_fields.update(_extract_vehicle_from_text(desc))

    # Documento relacionado (guía remitente que origina la del transportista)
    documento_relacionado = None
    for ref in root.findall("cac:AdditionalDocumentReference", NS):
        ref_id = _text(ref, "cbc:ID")
        if ref_id and "-" in ref_id:
            documento_relacionado = ref_id
            break

    fields = {
        "document_number": doc_id,
        "serie": serie,
        "number": number,
        "document_type": "GUIA_REMISION",
        "document_type_code": type_code,
        "tipo_guia": tipo_guia,
        "issue_date": issue_date,
        "issue_time": issue_time,
        "transfer_start_date": transfer_start_date,
        "ruc_emisor": ruc_emisor,
        "razon_social_emisor": razon_emisor,
        "ruc_destinatario": ruc_destinatario,
        "razon_social_destinatario": razon_destinatario,
        "ruc_remitente": ruc_remitente,
        "razon_social_remitente": razon_remitente,
        "direccion_partida": direccion_partida,
        "direccion_llegada": direccion_llegada,
        "peso_bruto": peso,
        "peso_unidad_medida": peso_unidad,
        "motivo_traslado_codigo": motivo,
        "motivo_traslado": motivo_descripcion,
        "placa": placas[0] if placas else None,
        "placa_secundaria": placas[1] if len(placas) > 1 else None,
        "placas": placas,
        "conductores": conductores,
        "licencia_conductor": licencias[0] if licencias else None,
        "nombre_conductor": conductores[0]["nombre"] if conductores else None,
        "dni_conductor": conductores[0]["dni"] if conductores else None,
        "documento_relacionado": documento_relacionado,
        **vehicle_fields,
    }

    return UblResult(document_type="GUIA_REMISION", fields=fields, items=items, warnings=warnings)


def _address_text(addr: ET.Element | None) -> str | None:
    if addr is None:
        return None
    parts: list[str] = []
    for xp in [
        "cbc:StreetName",
        "cbc:AdditionalStreetName",
        "cac:AddressLine/cbc:Line",
        "cbc:CitySubdivisionName",
        "cbc:CityName",
        "cbc:CountrySubentity",
        "cbc:District",
    ]:
        for el in addr.findall(xp, NS):
            if el.text:
                parts.append(el.text.strip())
    return " - ".join(p for p in parts if p) or None
