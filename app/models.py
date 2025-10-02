from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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


class Invoice(BaseModel):
    invoice_number: str = Field(..., min_length=1)
    issue_date: date
    due_date: Optional[date] = None
    seller: Party
    buyer: Party
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    line_items: List[LineItem] = Field(default_factory=list)
    payment_reference: Optional[str] = None
    payment_means_code: str = Field(default="30")
    seller_bank_iban: Optional[str] = None

    @field_validator("seller_bank_iban")
    @classmethod
    def _strip_iban(cls, value):
        if value:
            return value.replace(" ", "")
        return value

    @field_validator("line_items")
    @classmethod
    def _ensure_lines(cls, value):
        if not value:
            raise ValueError("Invoice must contain at least one line item")
        return value


__all__ = [
    "Address",
    "Party",
    "LineItem",
    "Invoice",
]
