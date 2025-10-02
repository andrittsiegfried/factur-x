from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

from lxml import etree

from .models import Invoice, LineItem


NSMAP = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def _qn(prefix: str, name: str) -> etree.QName:
    return etree.QName(NSMAP[prefix], name)


def _format_decimal(value: Decimal, digits: str = "0.01") -> str:
    quant = Decimal(digits)
    return str(value.quantize(quant, rounding=ROUND_HALF_UP))


def _date_element(tag: str, value: date, *, child_tag: str | None = None) -> etree.Element:
    element = etree.Element(_qn("ram", tag))
    container = (
        etree.SubElement(element, _qn("ram", child_tag))
        if child_tag
        else element
    )
    datetime_el = etree.SubElement(container, _qn("udt", "DateTimeString"), attrib={"format": "102"})
    datetime_el.text = value.strftime("%Y%m%d")
    return element


def _create_trade_party(tag: str, party_data) -> etree.Element:
    party_elem = etree.Element(_qn("ram", tag))
    etree.SubElement(party_elem, _qn("ram", "Name")).text = party_data.name
    if party_data.tax_registration_id:
        legal_org = etree.SubElement(party_elem, _qn("ram", "SpecifiedLegalOrganization"))
        etree.SubElement(legal_org, _qn("ram", "ID")).text = party_data.tax_registration_id
    address = etree.SubElement(party_elem, _qn("ram", "PostalTradeAddress"))
    etree.SubElement(address, _qn("ram", "PostcodeCode")).text = party_data.address.postal_code
    etree.SubElement(address, _qn("ram", "LineOne")).text = party_data.address.street
    etree.SubElement(address, _qn("ram", "CityName")).text = party_data.address.city
    etree.SubElement(address, _qn("ram", "CountryID")).text = party_data.address.country_code
    if party_data.email:
        comms = etree.SubElement(party_elem, _qn("ram", "URIUniversalCommunication"))
        etree.SubElement(comms, _qn("ram", "URIID")).text = party_data.email
    if party_data.vat_identifier:
        tax_reg = etree.SubElement(party_elem, _qn("ram", "SpecifiedTaxRegistration"))
        etree.SubElement(tax_reg, _qn("ram", "ID"), attrib={"schemeID": "VAT"}).text = party_data.vat_identifier
    return party_elem


def _line_trade_tax(line: LineItem, currency: str, line_total: Decimal) -> etree.Element:
    tax = etree.Element(_qn("ram", "ApplicableTradeTax"))
    tax_amount = (line_total * line.vat_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    etree.SubElement(tax, _qn("ram", "CalculatedAmount"), attrib={"currencyID": currency}).text = _format_decimal(tax_amount, "0.01")
    etree.SubElement(tax, _qn("ram", "TypeCode")).text = "VAT"
    etree.SubElement(tax, _qn("ram", "BasisAmount"), attrib={"currencyID": currency}).text = _format_decimal(line_total, "0.01")
    etree.SubElement(tax, _qn("ram", "CategoryCode")).text = "S"
    etree.SubElement(tax, _qn("ram", "RateApplicablePercent")).text = _format_decimal(line.vat_rate, "0.01")
    return tax


def build_facturx_xml(invoice: Dict) -> bytes:
    """Build a Factur-X EN16931 compliant XML document."""

    invoice_model = Invoice.model_validate(invoice)
    currency = invoice_model.currency

    root = etree.Element(_qn("rsm", "CrossIndustryInvoice"), nsmap=NSMAP)

    context = etree.SubElement(root, _qn("rsm", "ExchangedDocumentContext"))
    guideline = etree.SubElement(context, _qn("ram", "GuidelineSpecifiedDocumentContextParameter"))
    etree.SubElement(
        guideline,
        _qn("ram", "ID"),
        attrib={"schemeID": "urn:factur-x.eu:1p0:en16931:ver1.0"},
    ).text = "urn:factur-x.eu:1p0:en16931:ver1.0"

    document = etree.SubElement(root, _qn("rsm", "ExchangedDocument"))
    etree.SubElement(document, _qn("ram", "ID")).text = invoice_model.invoice_number
    etree.SubElement(document, _qn("ram", "TypeCode")).text = "380"
    issue_dt = etree.SubElement(document, _qn("ram", "IssueDateTime"))
    etree.SubElement(issue_dt, _qn("udt", "DateTimeString"), attrib={"format": "102"}).text = invoice_model.issue_date.strftime("%Y%m%d")

    transaction = etree.SubElement(root, _qn("rsm", "SupplyChainTradeTransaction"))

    vat_groups: Dict[Decimal, Dict[str, Decimal]] = defaultdict(lambda: {"basis": Decimal("0"), "tax": Decimal("0")})

    for index, line in enumerate(invoice_model.line_items, start=1):
        line_total = (line.unit_price * line.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_amount = (line_total * line.vat_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat_groups[line.vat_rate]["basis"] += line_total
        vat_groups[line.vat_rate]["tax"] += tax_amount

        line_item = etree.SubElement(transaction, _qn("ram", "IncludedSupplyChainTradeLineItem"))
        doc = etree.SubElement(line_item, _qn("ram", "AssociatedDocumentLineDocument"))
        etree.SubElement(doc, _qn("ram", "LineID")).text = str(index)

        product = etree.SubElement(line_item, _qn("ram", "SpecifiedTradeProduct"))
        etree.SubElement(product, _qn("ram", "Name")).text = line.description

        line_agreement = etree.SubElement(line_item, _qn("ram", "SpecifiedLineTradeAgreement"))
        gross = etree.SubElement(line_agreement, _qn("ram", "GrossPriceProductTradePrice"))
        etree.SubElement(gross, _qn("ram", "ChargeAmount"), attrib={"currencyID": currency}).text = _format_decimal(line.unit_price, "0.01")
        net = etree.SubElement(line_agreement, _qn("ram", "NetPriceProductTradePrice"))
        etree.SubElement(net, _qn("ram", "ChargeAmount"), attrib={"currencyID": currency}).text = _format_decimal(line.unit_price, "0.01")

        line_delivery = etree.SubElement(line_item, _qn("ram", "SpecifiedLineTradeDelivery"))
        etree.SubElement(line_delivery, _qn("ram", "BilledQuantity"), attrib={"unitCode": "C62"}).text = _format_decimal(line.quantity, "0.001")

        line_settlement = etree.SubElement(line_item, _qn("ram", "SpecifiedLineTradeSettlement"))
        line_settlement.append(_line_trade_tax(line, currency, line_total))
        line_sum = etree.SubElement(line_settlement, _qn("ram", "SpecifiedTradeSettlementLineMonetarySummation"))
        etree.SubElement(line_sum, _qn("ram", "LineTotalAmount"), attrib={"currencyID": currency}).text = _format_decimal(line_total, "0.01")

    agreement = etree.SubElement(transaction, _qn("ram", "ApplicableHeaderTradeAgreement"))
    agreement.append(_create_trade_party("SellerTradeParty", invoice_model.seller))
    agreement.append(_create_trade_party("BuyerTradeParty", invoice_model.buyer))

    delivery = etree.SubElement(transaction, _qn("ram", "ApplicableHeaderTradeDelivery"))
    delivery.append(
        _date_element(
            "ActualDeliverySupplyChainEvent",
            invoice_model.issue_date,
            child_tag="OccurrenceDateTime",
        )
    )

    settlement = etree.SubElement(transaction, _qn("ram", "ApplicableHeaderTradeSettlement"))
    if invoice_model.payment_reference:
        etree.SubElement(settlement, _qn("ram", "PaymentReference")).text = invoice_model.payment_reference
    etree.SubElement(settlement, _qn("ram", "InvoiceCurrencyCode")).text = currency

    payment_means = etree.SubElement(settlement, _qn("ram", "SpecifiedTradeSettlementPaymentMeans"))
    etree.SubElement(payment_means, _qn("ram", "TypeCode")).text = invoice_model.payment_means_code
    if invoice_model.seller_bank_iban:
        account = etree.SubElement(payment_means, _qn("ram", "PayeePartyCreditorFinancialAccount"))
        etree.SubElement(account, _qn("ram", "IBANID")).text = invoice_model.seller_bank_iban

    for rate, amounts in vat_groups.items():
        tax = etree.SubElement(settlement, _qn("ram", "ApplicableTradeTax"))
        etree.SubElement(tax, _qn("ram", "CalculatedAmount"), attrib={"currencyID": currency}).text = _format_decimal(amounts["tax"], "0.01")
        etree.SubElement(tax, _qn("ram", "TypeCode")).text = "VAT"
        etree.SubElement(tax, _qn("ram", "BasisAmount"), attrib={"currencyID": currency}).text = _format_decimal(amounts["basis"], "0.01")
        etree.SubElement(tax, _qn("ram", "CategoryCode")).text = "S"
        etree.SubElement(tax, _qn("ram", "RateApplicablePercent")).text = _format_decimal(rate, "0.01")

    taxable_total = sum(group["basis"] for group in vat_groups.values())
    tax_total = sum(group["tax"] for group in vat_groups.values())
    grand_total = taxable_total + tax_total

    if invoice_model.due_date:
        payment_terms = etree.SubElement(settlement, _qn("ram", "SpecifiedTradePaymentTerms"))
        due_date = etree.SubElement(payment_terms, _qn("ram", "DueDateDateTime"))
        etree.SubElement(due_date, _qn("udt", "DateTimeString"), attrib={"format": "102"}).text = invoice_model.due_date.strftime("%Y%m%d")

    monetary = etree.SubElement(settlement, _qn("ram", "SpecifiedTradeSettlementHeaderMonetarySummation"))
    etree.SubElement(monetary, _qn("ram", "LineTotalAmount"), attrib={"currencyID": currency}).text = _format_decimal(taxable_total, "0.01")
    etree.SubElement(monetary, _qn("ram", "TaxBasisTotalAmount"), attrib={"currencyID": currency}).text = _format_decimal(taxable_total, "0.01")
    etree.SubElement(monetary, _qn("ram", "TaxTotalAmount"), attrib={"currencyID": currency}).text = _format_decimal(tax_total, "0.01")
    etree.SubElement(monetary, _qn("ram", "GrandTotalAmount"), attrib={"currencyID": currency}).text = _format_decimal(grand_total, "0.01")
    etree.SubElement(monetary, _qn("ram", "DuePayableAmount"), attrib={"currencyID": currency}).text = _format_decimal(grand_total, "0.01")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


__all__ = ["build_facturx_xml"]
