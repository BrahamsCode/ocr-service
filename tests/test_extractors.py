"""Tests unitarios de los extractores — no requieren Tesseract instalado."""

from app.services.extractors import invoice, guide, patterns


class TestPatterns:
    def test_doc_number_formats(self):
        assert patterns.DOC_NUMBER.search("F001-123").group(1) == "F001"
        assert patterns.DOC_NUMBER.search("F001-123").group(2) == "123"
        assert patterns.DOC_NUMBER.search("FF01-00001234") is not None

    def test_ruc_valid(self):
        assert patterns.RUC.search("20344877158") is not None
        assert patterns.RUC.search("10123456789") is not None
        assert patterns.RUC.search("99999999999") is None  # no empieza con 10/15-17/20

    def test_vin(self):
        assert patterns.VIN.search("LGWEFGA54SA932190") is not None
        assert patterns.VIN.search("INVALID") is None
        # No I/O/Q permitidos en posición
        assert patterns.VIN.search("IOQ12345678901234") is None

    def test_normalize_amount(self):
        assert patterns.normalize_amount("15,000.00") == 15000.00
        assert patterns.normalize_amount("15.000,00") == 15000.00
        assert patterns.normalize_amount("15000") == 15000.0
        assert patterns.normalize_amount("abc") is None


class TestInvoiceExtractor:
    def test_basic_invoice(self):
        text = """
        FACTURA ELECTRONICA
        F008-00134314
        Emisor: DERCO PERU S.A.
        RUC: 20344877158
        Cliente: PACIFICO MOTORS S.A.C.
        RUC: 20555555555
        Fecha de emisión: 15/04/2026
        VIN: LGWEFGA54SA932190
        Motor: HFC4GB2.3DS3361747
        MARCA: JAC
        MODELO: JS2
        Total S/ 11,497.39
        """
        fields, warnings = invoice.extract(text)

        assert fields.document_number == "F008-00134314"
        assert fields.document_type == "FACTURA"
        assert fields.ruc_emisor == "20344877158"
        assert fields.ruc_cliente == "20555555555"
        assert fields.issue_date == "2026-04-15"
        assert fields.vin == "LGWEFGA54SA932190"
        assert fields.motor == "HFC4GB2.3DS3361747"
        assert fields.total == 11497.39
        assert fields.currency == "PEN"
        assert warnings == []

    def test_multiple_vins_warning(self):
        text = "VIN: LGWEFGA54SA932190 y también VIN LGWEFGA54SA932191"
        fields, warnings = invoice.extract(text)
        assert fields.vin is not None
        assert len(warnings) == 1
        assert "2 VINs" in warnings[0]


class TestGuideExtractor:
    def test_basic_guide(self):
        text = """
        GUIA DE REMISION ELECTRONICA
        T001-00001234
        REMITENTE: DERCO PERU S.A.
        RUC: 20344877158
        DESTINATARIO: PACIFICO MOTORS
        RUC: 20555555555
        Fecha de inicio de traslado: 15/04/2026
        PLACA: ABC-123
        Motivo de traslado: VENTA
        Peso bruto: 1500 kg
        """
        fields, warnings = guide.extract(text)

        assert fields.guide_series == "T001"
        assert fields.guide_number == "00001234"
        assert fields.ruc_emisor == "20344877158"
        assert fields.ruc_destinatario == "20555555555"
        assert fields.placa == "ABC-123"
        assert fields.peso_bruto_kg == 1500.0
