from __future__ import annotations

from io import BytesIO

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from facturx import get_facturx_xml_from_pdf, xml_check_xsd
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_invoice_pdf():
    payload = {
        "invoice_number": "INV-2024-0001",
        "issue_date": "2024-01-15",
        "due_date": "2024-01-30",
        "currency": "EUR",
        "payment_reference": "INV-2024-0001",
        "payment_means_code": "30",
        "seller_bank_iban": "FR7630004000031234567890143",
        "seller": {
            "name": "ACME Corp",
            "address": {
                "street": "1 Infinite Loop",
                "postal_code": "75001",
                "city": "Paris",
                "country_code": "FR",
            },
            "vat_identifier": "FR12345678901",
            "tax_registration_id": "123456789",
            "email": "billing@acme.example",
        },
        "buyer": {
            "name": "Client SAS",
            "address": {
                "street": "10 Rue de la Paix",
                "postal_code": "75002",
                "city": "Paris",
                "country_code": "FR",
            },
            "vat_identifier": "FR98765432109",
            "email": "contact@client.example",
        },
        "line_items": [
            {
                "description": "Consulting services",
                "quantity": "2",
                "unit_price": "150",
                "vat_rate": "20",
            },
            {
                "description": "Software license",
                "quantity": "1",
                "unit_price": "300",
                "vat_rate": "20",
            },
        ],
    }

    response = client.post("/invoices/pdf", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")

    pdf_bytes = response.content
    attachment_name, xml_bytes = get_facturx_xml_from_pdf(BytesIO(pdf_bytes))
    assert attachment_name == "factur-x.xml"
    assert xml_bytes is not None and len(xml_bytes) > 0

    xml_check_xsd(xml_bytes, flavor="factur-x", level="en16931")
