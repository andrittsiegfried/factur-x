from __future__ import annotations

from io import BytesIO

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from facturx import get_facturx_xml_from_pdf, xml_check_xsd
from fastapi.testclient import TestClient

from copy import deepcopy

from app.main import app
from app.models import INVOICE_EXAMPLE


client = TestClient(app)


def test_generate_invoice_pdf():
    payload = deepcopy(INVOICE_EXAMPLE)

    response = client.post("/invoices/pdf", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")

    pdf_bytes = response.content
    attachment_name, xml_bytes = get_facturx_xml_from_pdf(BytesIO(pdf_bytes))
    assert attachment_name == "factur-x.xml"
    assert xml_bytes is not None and len(xml_bytes) > 0

    xml_check_xsd(xml_bytes, flavor="factur-x", level="en16931")
