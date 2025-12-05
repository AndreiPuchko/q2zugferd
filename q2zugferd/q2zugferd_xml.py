from lxml import etree as ET
from decimal import Decimal

# --- NAMESPACE CONSTANTS (REQUIRED FOR ZUGFeRD) ---
# We use URI for element creation (key feature of lxml),
# and NS_MAP for correct prefix mapping in the final XML.

NS_MAP = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

# Convenient "wrappers" for URI
RAM = "{%s}" % NS_MAP["ram"]
RSM = "{%s}" % NS_MAP["rsm"]
UDT = "{%s}" % NS_MAP["udt"]
QDT = "{%s}" % NS_MAP["qdt"]


# --- MAIN XML GENERATOR ---
def q2zugferd_xml(zugferd_data: dict):
    """_summary_

    Args:
        zugferd_data (dict): _description_

    Returns:
        _type_: _description_
    """    """
    Generates ZUGFeRD 2.1 XML (Basic Profile) from prepared data.

    :param zugferd_data: Dictionary with invoice data (structure as in zugferd_data).
    :return: String with formatted XML.
    """

    invoice_header = zugferd_data["invoice_header"]
    seller = zugferd_data["seller"]
    buyer = zugferd_data["buyer"]
    currency = zugferd_data["currency"]
    seller_bank_account = zugferd_data["seller_bank_account"]
    invoice_lines = zugferd_data["invoice_lines"]
    vat_breakdown = zugferd_data["vat_breakdown"]

    # --- HELPER FUNCTION FOR TEXT FIELDS ---
    def _add_text_element(parent, tag_name, text_value):
        """Creates a child element and assigns text to it."""
        if text_value is not None:
            elem = ET.SubElement(parent, tag_name)
            elem.text = str(text_value)
            return elem

    # 1. Root element CrossIndustryInvoice
    root = ET.Element(RSM + "CrossIndustryInvoice", nsmap=NS_MAP)

    # ----------------------------------------------------------------------
    # 1. ExchangedDocumentContext (Document context)
    # ----------------------------------------------------------------------
    context = ET.SubElement(root, RSM + "ExchangedDocumentContext")

    # 1.1. BusinessProcessSpecifiedDocumentContextParameter (Process ID - optional)
    # In ZUGFeRD/XRechnung often used to specify the format (Profile)
    bus_proc = ET.SubElement(context, RAM + "BusinessProcessSpecifiedDocumentContextParameter")
    # Use recommended ID for BASIC profile
    _add_text_element(bus_proc, RAM + "ID", "urn:factur-x.eu:1p0:basic")

    # 1.2. GuidelineSpecifiedDocumentContextParameter (Rule/standard ID)
    # This is a required element to indicate compliance with EN16931
    spec_doc = ET.SubElement(context, RAM + "GuidelineSpecifiedDocumentContextParameter")
    # ID indicates compliance with EN16931 and BASIC profile
    _add_text_element(spec_doc, RAM + "ID", "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic")

    # ----------------------------------------------------------------------
    # 2. ExchangedDocument (General data)
    # ----------------------------------------------------------------------
    doc = ET.SubElement(root, RSM + "ExchangedDocument")
    _add_text_element(doc, RAM + "ID", invoice_header["invoice_number"])

    # 1. TypeCode (must be second)
    _add_text_element(doc, RAM + "TypeCode", "380")

    # 2. IssueDateTime (must be third)
    issue_date_time = ET.SubElement(doc, RAM + "IssueDateTime")
    date_str = invoice_header["invoice_date"].replace("-", "")
    date_string = ET.SubElement(issue_date_time, UDT + "DateTimeString", format="102")
    date_string.text = date_str

    if invoice_header.get("initial_note"):
        note1 = ET.SubElement(doc, RAM + "IncludedNote")
        ET.SubElement(note1, RAM + "Content").text = invoice_header["initial_note"]

    if invoice_header.get("closing_note"):
        note2 = ET.SubElement(doc, RAM + "IncludedNote")
        ET.SubElement(note2, RAM + "Content").text = invoice_header["closing_note"]

    # 3. LanguageID
    _add_text_element(doc, RAM + "LanguageID", "deu")

    # ----------------------------------------------------------------------
    # B. SupplyChainTradeTransaction
    # ----------------------------------------------------------------------
    transaction = ET.SubElement(root, RSM + "SupplyChainTradeTransaction")

    # B.1. Line Items (Invoice positions)
    for line in invoice_lines:
        line_item = ET.SubElement(transaction, RAM + "IncludedSupplyChainTradeLineItem")

        # Line Document (Line number)
        doc_line = ET.SubElement(line_item, RAM + "AssociatedDocumentLineDocument")
        _add_text_element(doc_line, RAM + "LineID", line["line_number"])

        # Product (Product/Service)
        product = ET.SubElement(line_item, RAM + "SpecifiedTradeProduct")
        _add_text_element(product, RAM + "Name", line["name"])
        _add_text_element(product, RAM + "Description", line["description"])
        # SKU
        # product_id = self.db_data.get_record("products", f"pid={line['product_id']}") # If you need to get SKU
        # _add_text_element(product, RAM + "SellerAssignedID", product_id['sku'])

        # Trade Delivery (Quantity)
        trade_delivery = ET.SubElement(line_item, RAM + "SpecifiedLineTradeDelivery")

        # Billed Quantity (Quantity and Unit of Measure)
        unit_code = line.get("unit_code", "PCE")
        billed_qty = ET.SubElement(trade_delivery, RAM + "BilledQuantity", unitCode=unit_code)
        # Round quantity to 4 decimal places
        billed_qty.text = "{:.4f}".format(Decimal(line["quantity"]))

        # Trade Settlement (Line settlement)
        trade_settlement = ET.SubElement(line_item, RAM + "SpecifiedLineTradeSettlement")

        # 1. Tax (VAT per line) - USE ApplicableTradeTax
        tax = ET.SubElement(trade_settlement, RAM + "ApplicableTradeTax")
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(tax, RAM + "CategoryCode", "S")  # Standard
        _add_text_element(tax, RAM + "RateApplicablePercent", "{:.2f}".format(Decimal(line["vat_rate"])))

        # 2. Monetary Summation (Line amount) - USE SpecifiedTradeSettlementLineMonetarySummation
        monetary_sum = ET.SubElement(trade_settlement, RAM + "SpecifiedTradeSettlementLineMonetarySummation")
        # Round to 2 decimal places
        _add_text_element(
            monetary_sum, RAM + "LineTotalAmount", "{:.2f}".format(Decimal(line["net_line_total"]))
        )

    # ----------------------------------------------------------------------
    # C. ApplicableHeaderTradeAgreement (Agreement)
    # ----------------------------------------------------------------------
    agreement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeAgreement")

    # Seller
    seller_party = ET.SubElement(agreement, RAM + "SellerTradeParty")
    _add_text_element(seller_party, RAM + "Name", seller["name"])

    seller_addr = ET.SubElement(seller_party, RAM + "PostalTradeAddress")
    _add_text_element(seller_addr, RAM + "PostcodeCode", seller["postal_code"])
    _add_text_element(seller_addr, RAM + "LineOne", seller["street"])
    _add_text_element(seller_addr, RAM + "CityName", seller["city"])
    _add_text_element(seller_addr, RAM + "CountryID", seller["country_code"])

    # Buyer
    buyer_party = ET.SubElement(agreement, RAM + "BuyerTradeParty")
    _add_text_element(buyer_party, RAM + "Name", buyer["name"])

    # ----------------------------------------------------------------------
    # D. ApplicableHeaderTradeDelivery (Delivery date)
    # ----------------------------------------------------------------------
    trade_delivery = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeDelivery")
    delivery_event = ET.SubElement(trade_delivery, RAM + "ActualDeliverySupplyChainEvent")

    occurrence_date = ET.SubElement(delivery_event, RAM + "OccurrenceDateTime")
    delivery_date_str = invoice_header["delivery_date"].replace("-", "")
    date_string = ET.SubElement(occurrence_date, UDT + "DateTimeString", format="102")
    date_string.text = delivery_date_str

    # ----------------------------------------------------------------------
    # E. ApplicableHeaderTradeSettlement (Settlement)
    # ----------------------------------------------------------------------
    settlement = ET.SubElement(transaction, RAM + "ApplicableHeaderTradeSettlement")
    _add_text_element(settlement, RAM + "InvoiceCurrencyCode", currency["iso_code"])

    # E.2. Payment Means (Seller's bank details)
    payment_means = ET.SubElement(settlement, RAM + "SpecifiedTradeSettlementPaymentMeans")
    _add_text_element(payment_means, RAM + "TypeCode", "30")  # 30 = Credit Transfer

    # E.1. VAT Breakdown
    for vat_item in vat_breakdown:
        tax = ET.SubElement(settlement, RAM + "ApplicableTradeTax")
        _add_text_element(tax, RAM + "CalculatedAmount", "{:.2f}".format(Decimal(vat_item["tax_amount"])))
        _add_text_element(tax, RAM + "TypeCode", "VAT")
        _add_text_element(tax, RAM + "BasisAmount", "{:.2f}".format(Decimal(vat_item["tax_base_amount"])))
        _add_text_element(tax, RAM + "CategoryCode", "S")  # Standard
        _add_text_element(tax, RAM + "RateApplicablePercent", "{:.2f}".format(Decimal(vat_item["vat_rate"])))

    # IBAN
    account = ET.SubElement(payment_means, RAM + "PayeePartyCreditorFinancialAccount")
    _add_text_element(account, RAM + "IBANID", seller_bank_account["iban"])

    # BIC
    institution = ET.SubElement(payment_means, RAM + "PayeeSpecifiedCreditorFinancialInstitution")
    _add_text_element(institution, RAM + "BICID", seller_bank_account["bic_swift"])

    # E.4. Payment Terms
    terms = ET.SubElement(settlement, RAM + "SpecifiedTradePaymentTerms")

    # E.3. Monetary Summation (Totals)
    monetary_sum = ET.SubElement(settlement, RAM + "SpecifiedTradeSettlementHeaderMonetarySummation")

    # Round to 2 decimal places
    net_amount = Decimal(invoice_header["net_amount"])
    tax_total = Decimal(invoice_header["gross_amount"]) - net_amount
    gross_amount = Decimal(invoice_header["gross_amount"])

    _add_text_element(monetary_sum, RAM + "LineTotalAmount", "{:.2f}".format(net_amount))
    _add_text_element(monetary_sum, RAM + "TaxBasisTotalAmount", "{:.2f}".format(net_amount))
    _add_text_element(monetary_sum, RAM + "TaxTotalAmount", "{:.2f}".format(tax_total))
    _add_text_element(monetary_sum, RAM + "GrandTotalAmount", "{:.2f}".format(gross_amount))

    # Net payment (payment term)
    payment_base_text = f'Zahlungsziel: {invoice_header["payment_terms_days"]} Tage netto.'

    # Skonto terms (if applicable)
    if Decimal(invoice_header.get("skonto_rate", 0)) > 0:
        skonto_text = f' 3% Skonto bei Zahlung bis zum {invoice_header["skonto_due_date"]}.'
        payment_base_text += skonto_text

    _add_text_element(terms, RAM + "Description", payment_base_text)

    # ----------------------------------------------------------------------
    # 3. Finalization and output
    # ----------------------------------------------------------------------

    # Convert tree to string with pretty formatting
    zu = ET.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True).decode("utf-8")
    return zu
