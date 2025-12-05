from lxml import etree as ET
from decimal import Decimal

NS_MAP = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

RAM = "{%s}" % NS_MAP["ram"]
RSM = "{%s}" % NS_MAP["rsm"]
UDT = "{%s}" % NS_MAP["udt"]
QDT = "{%s}" % NS_MAP["qdt"]


def q2zugferd_xml(zugferd_data: dict):

    invoice_header = zugferd_data["invoice_header"]
    seller = zugferd_data["seller"]
    buyer = zugferd_data["buyer"]
    currency = zugferd_data["currency"]
    seller_bank_account = zugferd_data["seller_bank_account"]
    invoice_lines = zugferd_data["invoice_lines"]
    vat_breakdown = zugferd_data["vat_breakdown"]

    def _add_text_element(parent, tag_name, text_value):
        if text_value is not None and text_value != "":
            elem = ET.SubElement(parent, tag_name)
            elem.text = str(text_value)
            return elem

    root = ET.Element(RSM + "CrossIndustryInvoice", nsmap=NS_MAP)

    # ------------------------------------------------------------------
    # 1. CONTEXT (EN 16931 COMFORT)
    # ------------------------------------------------------------------
    context = ET.SubElement(root, RSM + "ExchangedDocumentContext")

    bus_proc = ET.SubElement(context, RAM + "BusinessProcessSpecifiedDocumentContextParameter")
    _add_text_element(bus_proc, RAM + "ID", "urn:factur-x.eu:1p0:comfort")

    spec_doc = ET.SubElement(context, RAM + "GuidelineSpecifiedDocumentContextParameter")
    _add_text_element(
        spec_doc,
        RAM + "ID",
        "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:comfort",
    )

    # ------------------------------------------------------------------
    # 2. DOCUMENT HEADER
    # ------------------------------------------------------------------
    doc = ET.SubElement(root, RSM + "ExchangedDocument")
    _add_text_element(doc, RAM + "ID", invoice_header["invoice_number"])
    _add_text_element(doc, RAM + "TypeCode", "380")

    issue_date_time = ET.SubElement(doc, RAM + "IssueDateTime")
    date_str = invoice_header["invoice_date"].replace("-", "")
    ET.SubElement(issue_date_time, UDT + "DateTimeString", format="102").text = date_str

    if invoice_header.get("initial_note"):
        note1 = ET.SubElement(doc, RAM + "IncludedNote")
        ET.SubElement(note1, RAM + "Content").text = invoice_header["initial_note"]

    if invoice_header.get("closing_note"):
        note2 = ET.SubElement(doc, RAM + "IncludedNote")
        ET.SubElement(note2, RAM + "Content").text = invoice_header["closing_note"]

    _add_text_element(doc, RAM + "LanguageID", "deu")

    # ------------------------------------------------------------------
    # B. TRANSACTION
    # ------------------------------------------------------------------
    transaction = ET.SubElement(root, RSM + "SupplyChainTradeTransaction")

    # -----------------------------
    # LINE ITEMS
    # -----------------------------
    for line in invoice_lines:
        line_item = ET.SubElement(transaction, RAM + "IncludedSupplyChainTradeLineItem")

        doc_line = ET.SubElement(line_item, RAM + "AssociatedDocumentLineDocument")
        _add_text_element(doc_line, RAM + "LineID", line["line_number"])

        product = ET.SubElement(line_item, RAM + "SpecifiedTradeProduct")
        _add_text_element(product, RAM + "Name", line["name"])
        _add_text_element(product, RAM + "Description", line["description"])

        trade_delivery = ET.SubElement(line_item, RAM + "SpecifiedLineTradeDelivery")
        unit_code = line.get("unit_code", "PCE")
        billed_qty = ET.SubElement(trade_delivery, RAM + "BilledQuantity", unitCode=unit_code)
        billed_qty.text = "{:.4f}".format(Decimal(line["quantity"]))

        # ✅ EN 16931: UNIT PRICE (MANDATORY)
        trade_agreement = ET.SubElement(line_item, RAM + "SpecifiedLineTradeAgreement")
        net_price = ET.SubElement(trade_agreement, RAM + "NetPriceProductTradePrice")
        _add_text_element(net_price, RAM + "ChargeAmount", "{:.2f}".format(Decimal(line["net_price"])))

        trade_settlement = ET.SubElement(line_item, RAM + "SpecifiedLineTradeSettlement")

        tax = ET.SubElement(trade_settlement, RAM + "ApplicableTradeTax")
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(tax, RAM + "CategoryCode", "S")
        _add_text_element(tax, RAM + "RateApplicablePercent", "{:.2f}".format(Decimal(line["vat_rate"])))

        monetary_sum = ET.SubElement(trade_settlement, RAM + "SpecifiedTradeSettlementLineMonetarySummation")
        _add_text_element(
            monetary_sum,
            RAM + "LineTotalAmount",
            "{:.2f}".format(Decimal(line["net_line_total"] or line["net_total"])),
        )

    # ------------------------------------------------------------------
    # C. AGREEMENT
    # ------------------------------------------------------------------
    agreement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeAgreement")

    seller_party = ET.SubElement(agreement, RAM + "SellerTradeParty")
    _add_text_element(seller_party, RAM + "Name", seller["name"])

    if seller.get("vat_id"):
        tax_reg = ET.SubElement(seller_party, RAM + "SpecifiedTaxRegistration")
        _add_text_element(tax_reg, RAM + "ID", seller["vat_id"])

    seller_addr = ET.SubElement(seller_party, RAM + "PostalTradeAddress")
    _add_text_element(seller_addr, RAM + "PostcodeCode", seller["postal_code"])
    _add_text_element(seller_addr, RAM + "LineOne", seller["street"])
    _add_text_element(seller_addr, RAM + "CityName", seller["city"])
    _add_text_element(seller_addr, RAM + "CountryID", seller["country_code"])

    buyer_party = ET.SubElement(agreement, RAM + "BuyerTradeParty")
    _add_text_element(buyer_party, RAM + "Name", buyer["name"])

    # ✅ EN 16931: BUYER ADDRESS IS MANDATORY
    buyer_addr = ET.SubElement(buyer_party, RAM + "PostalTradeAddress")
    _add_text_element(buyer_addr, RAM + "PostcodeCode", buyer["postal_code"])
    _add_text_element(buyer_addr, RAM + "LineOne", buyer["street"])
    _add_text_element(buyer_addr, RAM + "CityName", buyer["city"])
    _add_text_element(buyer_addr, RAM + "CountryID", buyer["country_code"])

    if buyer.get("vat_id"):
        tax_reg = ET.SubElement(buyer_party, RAM + "SpecifiedTaxRegistration")
        _add_text_element(tax_reg, RAM + "ID", buyer["vat_id"])

    # ------------------------------------------------------------------
    # D. DELIVERY
    # ------------------------------------------------------------------
    trade_delivery = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeDelivery")
    delivery_event = ET.SubElement(trade_delivery, RAM + "ActualDeliverySupplyChainEvent")

    occurrence_date = ET.SubElement(delivery_event, RAM + "OccurrenceDateTime")
    delivery_date_str = invoice_header["delivery_date"].replace("-", "")
    ET.SubElement(occurrence_date, UDT + "DateTimeString", format="102").text = delivery_date_str

    # ------------------------------------------------------------------
    # E. SETTLEMENT
    # ------------------------------------------------------------------
    settlement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeSettlement")
    _add_text_element(settlement, RAM + "InvoiceCurrencyCode", currency["iso_code"])
    _add_text_element(settlement, RAM + "TaxCurrencyCode", currency["iso_code"])

    payment_means = ET.SubElement(settlement, RAM + "SpecifiedTradeSettlementPaymentMeans")
    _add_text_element(payment_means, RAM + "TypeCode", "30")

    for vat_item in vat_breakdown:
        tax = ET.SubElement(settlement, RAM + "ApplicableTradeTax")
        _add_text_element(tax, RAM + "CalculatedAmount", "{:.2f}".format(Decimal(vat_item["tax_amount"])))
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(tax, RAM + "BasisAmount", "{:.2f}".format(Decimal(vat_item["tax_base_amount"])))
        _add_text_element(tax, RAM + "CategoryCode", "S")
        _add_text_element(tax, RAM + "RateApplicablePercent", "{:.2f}".format(Decimal(vat_item["vat_rate"])))

    account = ET.SubElement(payment_means, RAM + "PayeePartyCreditorFinancialAccount")
    _add_text_element(account, RAM + "IBANID", seller_bank_account["iban"])

    institution = ET.SubElement(payment_means, RAM + "PayeeSpecifiedCreditorFinancialInstitution")
    _add_text_element(institution, RAM + "BICID", seller_bank_account["bic_swift"])

    terms = ET.SubElement(settlement, RAM + "SpecifiedTradePaymentTerms")

    # ✅ EN 16931: DUE DATE AS STRUCTURED DATE
    if invoice_header.get("due_date"):
        due_date = ET.SubElement(settlement, RAM + "DueDateDateTime")
        ET.SubElement(due_date, UDT + "DateTimeString", format="102").text = invoice_header[
            "due_date"
        ].replace("-", "")

    monetary_sum = ET.SubElement(settlement, RAM + "SpecifiedTradeSettlementHeaderMonetarySummation")

    net_amount = Decimal(invoice_header["net_amount"])
    tax_total = Decimal(invoice_header["gross_amount"]) - net_amount
    gross_amount = Decimal(invoice_header["gross_amount"])

    _add_text_element(monetary_sum, RAM + "LineTotalAmount", f"{net_amount:.2f}")
    _add_text_element(monetary_sum, RAM + "TaxBasisTotalAmount", f"{net_amount:.2f}")
    _add_text_element(monetary_sum, RAM + "TaxTotalAmount", f"{tax_total:.2f}")
    _add_text_element(monetary_sum, RAM + "GrandTotalAmount", f"{gross_amount:.2f}")

    # ✅ Mandatory even if zero:
    _add_text_element(monetary_sum, RAM + "ChargeTotalAmount", "0.00")
    _add_text_element(monetary_sum, RAM + "AllowanceTotalAmount", "0.00")

    payment_base_text = f'Zahlungsziel: {invoice_header["payment_terms_days"]} Tage netto.'

    if Decimal(invoice_header.get("skonto_rate", 0)) > 0:
        payment_base_text += f' {invoice_header["skonto_rate"]}% Skonto bei Zahlung bis zum {invoice_header["skonto_due_date"]}.'

    _add_text_element(terms, RAM + "Description", payment_base_text)

    zu = ET.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True).decode("utf-8")
    return zu
