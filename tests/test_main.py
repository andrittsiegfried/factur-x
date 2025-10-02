from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from facturx import get_facturx_xml_from_pdf, xml_check_xsd

from app.main import app, create_invoice_pdf
from app.models import INVOICE_EXAMPLE, Invoice


def test_openapi_example_matches_invoice_example():
    schema = app.openapi()
    example = schema["components"]["schemas"]["Invoice"]["example"]
    assert example == INVOICE_EXAMPLE


def test_generate_invoice_pdf():
    invoice = Invoice.model_validate(deepcopy(INVOICE_EXAMPLE))

    response = create_invoice_pdf(invoice)

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment; filename=invoice-")

    pdf_bytes = response.body
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")

    attachment_name, xml_bytes = get_facturx_xml_from_pdf(BytesIO(pdf_bytes))
    assert attachment_name == "factur-x.xml"
    assert xml_bytes and len(xml_bytes) > 0

    xml_check_xsd(xml_bytes, flavor="factur-x", level="en16931")
