from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Iterable

from facturx import generate_from_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Invoice
from .xml_builder import build_facturx_xml


def _format_amount(value: Decimal) -> str:
    return f"{value:.2f}"


def _draw_multiline(c: canvas.Canvas, lines: Iterable[str], start_y: float, line_height: float = 18) -> float:
    y = start_y
    for line in lines:
        c.drawString(40, y, line)
        y -= line_height
    return y


def _render_invoice_pdf(invoice: Invoice) -> bytes:
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4

    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(40, height - 60, f"Invoice {invoice.invoice_number}")

    pdf_canvas.setFont("Helvetica", 11)
    y_position = height - 100
    y_position = _draw_multiline(
        pdf_canvas,
        [
            "Seller:",
            invoice.seller.name,
            invoice.seller.address.street,
            f"{invoice.seller.address.postal_code} {invoice.seller.address.city}",
            invoice.seller.address.country_code,
        ],
        y_position,
    )

    y_position = _draw_multiline(
        pdf_canvas,
        [
            "Buyer:",
            invoice.buyer.name,
            invoice.buyer.address.street,
            f"{invoice.buyer.address.postal_code} {invoice.buyer.address.city}",
            invoice.buyer.address.country_code,
        ],
        y_position - 20,
    )

    y_position -= 20
    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawString(40, y_position, "Lines")
    y_position -= 20
    pdf_canvas.setFont("Helvetica", 11)

    total_excl_tax = Decimal("0")
    for index, line in enumerate(invoice.line_items, start=1):
        line_total = line.unit_price * line.quantity
        total_excl_tax += line_total
        pdf_canvas.drawString(
            40,
            y_position,
            f"{index}. {line.description} — Qty: {line.quantity} × {line.unit_price} = {_format_amount(line_total)} {invoice.currency}",
        )
        y_position -= 16

    tax_total = sum(
        (line.unit_price * line.quantity * line.vat_rate / Decimal("100"))
        for line in invoice.line_items
    )
    grand_total = total_excl_tax + tax_total

    y_position -= 10
    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawString(40, y_position, f"Subtotal: {_format_amount(total_excl_tax)} {invoice.currency}")
    y_position -= 16
    pdf_canvas.drawString(40, y_position, f"VAT: {_format_amount(tax_total)} {invoice.currency}")
    y_position -= 16
    pdf_canvas.drawString(40, y_position, f"Total due: {_format_amount(grand_total)} {invoice.currency}")

    pdf_canvas.showPage()
    pdf_canvas.save()
    buffer.seek(0)
    return buffer.read()


def generate_facturx_pdf(invoice: Invoice) -> bytes:
    pdf_bytes = _render_invoice_pdf(invoice)
    xml_bytes = build_facturx_xml(invoice.model_dump(mode="python"))

    pdf_buffer = BytesIO(pdf_bytes)
    pdf_buffer.seek(0)
    generate_from_file(
        pdf_buffer,
        xml_bytes,
        flavor="factur-x",
        level="en16931",
        check_xsd=True,
    )
    pdf_buffer.seek(0)
    return pdf_buffer.read()


__all__ = ["generate_facturx_pdf"]
