from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response

from .models import Invoice
from .utils import generate_facturx_pdf

app = FastAPI(
    title="API Factur-X",
    description="Génération de PDF et XML conformes EN16931",
    version="1.0.0",
)


@app.get("/")
def ping() -> dict[str, str]:
    """Simple health endpoint to ensure the API is reachable."""
    return {"message": "API opérationnelle"}


@app.post("/invoices/pdf", response_class=Response)
def create_invoice_pdf(invoice: Invoice) -> Response:
    try:
        pdf_bytes = generate_facturx_pdf(invoice)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = {
        "Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_number}.pdf",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
