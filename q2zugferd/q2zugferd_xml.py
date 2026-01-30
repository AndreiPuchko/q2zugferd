from lxml import etree as ET
from decimal import Decimal
import re

NS_MAP = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

RAM = "{%s}" % NS_MAP["ram"]
RSM = "{%s}" % NS_MAP["rsm"]
UDT = "{%s}" % NS_MAP["udt"]


def q2zugferd_xml(zugferd_data: dict):
    invoice_header = zugferd_data["invoice_header"]
    seller = zugferd_data["seller"]
    buyer = zugferd_data["buyer"]
    currency = zugferd_data["currency"]
    seller_bank_account = zugferd_data["seller_bank_account"]
    invoice_lines = zugferd_data["invoice_lines"]
    vat_breakdown = zugferd_data["vat_breakdown"]

    def _add_text_element(parent, tag_name, text_value):
        if text_value is not None and str(text_value).strip() != "":
            elem = ET.SubElement(parent, tag_name)
            elem.text = str(text_value)
            return elem

    root = ET.Element(RSM + "CrossIndustryInvoice", nsmap=NS_MAP)

    # 1. CONTEXT
    context = ET.SubElement(root, RSM + "ExchangedDocumentContext")
    # bus_proc = ET.SubElement(
    #     context, RAM + "BusinessProcessSpecifiedDocumentContextParameter"
    # )
    # _add_text_element(bus_proc, RAM + "ID", "urn:factur-x.eu:1p0:comfort")
    spec_doc = ET.SubElement(
        context, RAM + "GuidelineSpecifiedDocumentContextParameter"
    )
    _add_text_element(
        spec_doc,
        RAM + "ID",
        "urn:cen.eu:en16931:2017",
    )

    # 2. DOCUMENT HEADER
    doc = ET.SubElement(root, RSM + "ExchangedDocument")
    _add_text_element(doc, RAM + "ID", invoice_header["invoice_number"])
    _add_text_element(doc, RAM + "TypeCode", "380")
    issue_date_time = ET.SubElement(doc, RAM + "IssueDateTime")
    ET.SubElement(
        issue_date_time, UDT + "DateTimeString", format="102"
    ).text = invoice_header["invoice_date"].replace("-", "")

    # for note_key in ["initial_note", "closing_note"]:
    #     if invoice_header.get(note_key):
    #         note = ET.SubElement(doc, RAM + "IncludedNote")
    #         ET.SubElement(note, RAM + "Content").text = invoice_header[note_key]

    # _add_text_element(doc, RAM + "LanguageID", "deu")

    # 3. TRANSACTION (СТРОГИЙ ПОРЯДОК: Lines -> Agreement -> Delivery -> Settlement)
    transaction = ET.SubElement(root, RSM + "SupplyChainTradeTransaction")

    # --- LINE ITEMS ---
    for line in invoice_lines:
        line_item = ET.SubElement(transaction, RAM + "IncludedSupplyChainTradeLineItem")

        doc_line = ET.SubElement(line_item, RAM + "AssociatedDocumentLineDocument")
        _add_text_element(doc_line, RAM + "LineID", line["line_number"])

        product = ET.SubElement(line_item, RAM + "SpecifiedTradeProduct")
        _add_text_element(product, RAM + "Name", line["name"])
        _add_text_element(product, RAM + "Description", line["description"])

        trade_agreement = ET.SubElement(line_item, RAM + "SpecifiedLineTradeAgreement")
        net_price = ET.SubElement(trade_agreement, RAM + "NetPriceProductTradePrice")
        _add_text_element(
            net_price, RAM + "ChargeAmount", "{:.4f}".format(Decimal(line["net_price"]))
        )
        ET.SubElement(
            net_price,
            RAM + "BasisQuantity",
            unitCode=line.get("unit_code", "PCE"),
        ).text = "{:.4f}".format(Decimal(1))

        trade_delivery = ET.SubElement(line_item, RAM + "SpecifiedLineTradeDelivery")
        ET.SubElement(
            trade_delivery,
            RAM + "BilledQuantity",
            unitCode=line.get("unit_code", "PCE"),
        ).text = "{:.4f}".format(Decimal(line["quantity"]))

        trade_settlement = ET.SubElement(
            line_item, RAM + "SpecifiedLineTradeSettlement"
        )
        tax = ET.SubElement(trade_settlement, RAM + "ApplicableTradeTax")
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(tax, RAM + "CategoryCode", "S")
        _add_text_element(
            tax,
            RAM + "RateApplicablePercent",
            "{:.2f}".format(Decimal(line["vat_rate"])),
        )

        monetary_sum = ET.SubElement(
            trade_settlement, RAM + "SpecifiedTradeSettlementLineMonetarySummation"
        )
        _add_text_element(
            monetary_sum,
            RAM + "LineTotalAmount",
            "{:.2f}".format(Decimal(line.get("net_line_total", line["net_total"]))),
        )

    # --- AGREEMENT ---
    agreement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeAgreement")
    _add_text_element(agreement, RAM + "BuyerReference", buyer["part_id"])
    seller_party = ET.SubElement(agreement, RAM + "SellerTradeParty")
    _add_text_element(seller_party, RAM + "Name", seller["name"])

    seller_addr = ET.SubElement(seller_party, RAM + "PostalTradeAddress")
    _add_text_element(seller_addr, RAM + "PostcodeCode", seller["postal_code"])
    _add_text_element(seller_addr, RAM + "LineOne", seller["street"])
    _add_text_element(seller_addr, RAM + "CityName", seller["city"])
    _add_text_element(seller_addr, RAM + "CountryID", seller["country_code"])

    if seller.get("vat_id"):
        tax_reg = ET.SubElement(seller_party, RAM + "SpecifiedTaxRegistration")
        tax_id_elem = ET.SubElement(tax_reg, RAM + "ID", schemeID="VA")
        tax_id_elem.text = seller["vat_id"]

    buyer_party = ET.SubElement(agreement, RAM + "BuyerTradeParty")
    _add_text_element(buyer_party, RAM + "ID", buyer["part_id"])
    _add_text_element(buyer_party, RAM + "Name", buyer["name"])
    buyer_addr = ET.SubElement(buyer_party, RAM + "PostalTradeAddress")
    _add_text_element(buyer_addr, RAM + "PostcodeCode", buyer["postal_code"])
    _add_text_element(buyer_addr, RAM + "LineOne", buyer["street"])
    _add_text_element(buyer_addr, RAM + "CityName", buyer["city"])
    _add_text_element(buyer_addr, RAM + "CountryID", buyer["country_code"])

    # --- DELIVERY ---
    trade_delivery = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeDelivery")
    delivery_event = ET.SubElement(
        trade_delivery, RAM + "ActualDeliverySupplyChainEvent"
    )
    occurrence_date = ET.SubElement(delivery_event, RAM + "OccurrenceDateTime")
    ET.SubElement(
        occurrence_date, UDT + "DateTimeString", format="102"
    ).text = invoice_header["delivery_date"].replace("-", "")

    # --- SETTLEMENT ---
    settlement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeSettlement")
    _add_text_element(
        settlement, RAM + "PaymentReference", invoice_header["invoice_number"]
    )
    _add_text_element(settlement, RAM + "InvoiceCurrencyCode", currency["iso_code"])

    payment_means = ET.SubElement(
        settlement, RAM + "SpecifiedTradeSettlementPaymentMeans"
    )
    _add_text_element(payment_means, RAM + "TypeCode", "42")
    _add_text_element(payment_means, RAM + "Information", "Bank transfer")
    account = ET.SubElement(payment_means, RAM + "PayeePartyCreditorFinancialAccount")
    # Очистка IBAN от пробелов
    clean_iban = re.sub(r"\s+", "", seller_bank_account["iban"])
    _add_text_element(account, RAM + "IBANID", clean_iban)
    # _add_text_element(account, RAM + "AccountName", "Max Mustermann")

    institution = ET.SubElement(
        payment_means, RAM + "PayeeSpecifiedCreditorFinancialInstitution"
    )
    _add_text_element(institution, RAM + "BICID", seller_bank_account["bic_swift"])

    for vat_item in vat_breakdown:
        tax = ET.SubElement(settlement, RAM + "ApplicableTradeTax")
        _add_text_element(
            tax,
            RAM + "CalculatedAmount",
            "{:.2f}".format(Decimal(vat_item["tax_amount"])),
        )
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(
            tax,
            RAM + "BasisAmount",
            "{:.2f}".format(Decimal(vat_item["tax_base_amount"])),
        )
        _add_text_element(tax, RAM + "CategoryCode", "S")
        _add_text_element(
            tax,
            RAM + "RateApplicablePercent",
            "{:.2f}".format(Decimal(vat_item["vat_rate"])),
        )

    terms = ET.SubElement(settlement, RAM + "SpecifiedTradePaymentTerms")
    desc = f"Zahlungsziel: {invoice_header['payment_terms_days']} Tage netto."
    if Decimal(invoice_header.get("skonto_rate", 0)) > 0:
        desc += f" {invoice_header['skonto_rate']}% Skonto bis {invoice_header['skonto_due_date']}."
    _add_text_element(terms, RAM + "Description", desc)

    if invoice_header.get("due_date"):
        due_date = ET.SubElement(terms, RAM + "DueDateDateTime")
        ET.SubElement(
            due_date, UDT + "DateTimeString", format="102"
        ).text = invoice_header["due_date"].replace("-", "")

    monetary_sum = ET.SubElement(
        settlement, RAM + "SpecifiedTradeSettlementHeaderMonetarySummation"
    )
    net = Decimal(invoice_header["net_amount"])
    # Расчет налога на основе breakdown для точности
    tax_total = sum(Decimal(v["tax_amount"]) for v in vat_breakdown)

    _add_text_element(monetary_sum, RAM + "LineTotalAmount", "{:.2f}".format(net))
    _add_text_element(monetary_sum, RAM + "ChargeTotalAmount", "0.00")
    _add_text_element(monetary_sum, RAM + "AllowanceTotalAmount", "0.00")
    _add_text_element(monetary_sum, RAM + "TaxBasisTotalAmount", "{:.2f}".format(net))
    el = _add_text_element(
        monetary_sum, RAM + "TaxTotalAmount", "{:.2f}".format(tax_total)
    )
    if el is not None:
        el.set("currencyID", currency["iso_code"])
    _add_text_element(
        monetary_sum, RAM + "GrandTotalAmount", "{:.2f}".format(net + tax_total)
    )
    _add_text_element(
        monetary_sum, RAM + "TotalPrepaidAmount", "{:.2f}".format(Decimal(0))
    )
    _add_text_element(
        monetary_sum, RAM + "DuePayableAmount", "{:.2f}".format(net + tax_total)
    )

    return ET.tostring(
        root, pretty_print=True, encoding="UTF-8", xml_declaration=True
    ).decode("utf-8")
