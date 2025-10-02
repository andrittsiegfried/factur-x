from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Address(BaseModel):
    street: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    country_code: str = Field(..., min_length=2, max_length=2)


class Party(BaseModel):
    name: str = Field(..., min_length=1)
    address: Address
    vat_identifier: Optional[str] = None
    tax_registration_id: Optional[str] = None
    email: Optional[str] = None


class LineItem(BaseModel):
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    vat_rate: Decimal = Field(..., ge=Decimal("0"))

    @field_validator("quantity", "unit_price", "vat_rate", mode="before")
    @classmethod
    def _convert_decimal(cls, value):
        if isinstance(value, (float, int)):
            return Decimal(str(value))
        return value


INVOICE_EXAMPLE: Dict[str, Any] = {
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


class Invoice(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": INVOICE_EXAMPLE})

    invoice_number: str = Field(..., min_length=1)
    issue_date: date
    due_date: Optional[date] = None
    seller: Party
    buyer: Party
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    line_items: List[LineItem] = Field(..., min_length=1)
    payment_reference: Optional[str] = None
    payment_means_code: str = Field(default="30")
    seller_bank_iban: Optional[str] = None

    @field_validator("seller_bank_iban")
    @classmethod
    def _strip_iban(cls, value):
        if value:
            return value.replace(" ", "")
        return value

__all__ = [
    "Address",
    "Party",
    "LineItem",
    "Invoice",
    "INVOICE_EXAMPLE",
]
