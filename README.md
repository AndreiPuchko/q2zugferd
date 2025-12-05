# q2zugferd

ZUGFeRD / Factur-X PDF and XML generator for Python.

## Features

- Generate ZUGFeRD 2.1 (Factur-X) compliant XML invoices.
- Embed XML invoices into PDF/A-3 files for electronic invoicing.
- Supports sRGB ICC profiles for PDF/A compliance.

## Installation

```bash
pip install q2zugferd
```

## Data Structure: `zugferd_data`

The `zugferd_data` dictionary contains all invoice information required to generate a ZUGFeRD XML. Its structure typically includes:

- `invoice_header`: Invoice metadata (invoice_number, invoice_date, delivery_date, net/gross amounts, payment terms, skonto, notes, etc.)
- `seller`: Seller's company information (name, vat_id, address, legal_id, tax_number, etc.)
- `buyer`: Buyer's company information (name, vat_id, address, etc.)
- `currency`: Currency details (iso_code, name, etc.)
- `seller_bank_account`: Seller's bank account info (iban, bic_swift, etc.)
- `invoice_lines`: List of invoice line items, each with product, quantity, price, VAT, etc.
- `vat_breakdown`: List of VAT breakdowns (rate, base amount, tax amount, etc.)

**Example:**

```python
zugferd_data = {
    "invoice_header": {
        "invoice_number": "INV-2025-11-102",
        "invoice_date": "2025-11-27",
        "currency_id": "978",
        "payment_terms_days": "14",
        "due_date": "2025-12-10",
        "net_amount": "36630.00",
        "gross_amount": "41391.90",
        "delivery_date": "2025-12-01",
        "skonto_rate": "3.00",
        "skonto_due_date": "2025-12-03",
        "initial_note": "Einleitu\n\n\nngstext * 1",
        "closing_note": "Schlusstext * 2 line2rth ;erl jh o; ;ke\n;hioej r;hioje;itrohj ;wioj ht;iodjfhgil'dgdgfh dfh gdfh",
    },
    "seller": {
        "vat_id": "DE279247134",
        "name": "Webware Internet Solutions GmbH",
        "postal_code": "12345",
        "city": "Hremen",
        "country_code": "",
        "iban": "",
        "bic": "",
        "street": "Einbahn Straße 19",
        "country_id": "",
        "contact_name": "",
        "default_bank_id": "0",
        "default_payment_bank_id": "0",
    },
    "buyer": {
        "pid": "2",
        "vat_id": "",
        "name": "Agoratech",
        "legal_name": "",
        "street_name": "",
        "building_number": "",
        "postal_code": "34130",
        "city": "Kassel",
        "country_code": "",
        "email": "",
        "phone": "",
        "iban": "",
        "bic": "",
        "legal_id": "",
        "tax_number": "",
        "uri_id": "",
        "street": "Teichstr. 14-16",
        "country_id": "",
        "contact_name": "",
    },
    "currency": {
        "cid": "978",
        "iso_code": "EUR",
        "name": "Euro",
    },
    "seller_bank_account": {
        "baid": "5",
        "party_id": "1",
        "account_name": "2",
        "iban": "2iban",
        "bic_swift": "2bic",
        "currency_id": "756",
        "default_account": "*",
        "default_payment_account": "",
    },
    "invoice_lines": [
        {
            "lid": "1",
            "invoice_id": "1",
            "product_id": "28",
            "line_number": "1",
            "quantity": "333.0000",
            "unit_code": "MTR",
            "net_price": "55.0000",
            "vat_rate": "19.00",
            "net_line_total": "0.00",
            "delivery_date": "2025-11-12",
            "description": "Rolle Netzwerkkabel, 100 Meter.",
            "rid": "0",
            "unit_id": "4",
            "net_line_total__": "47730.00",
            "net_total": "18315.00",
            "vat_total": "3479.85",
            "gross_total": "21794.85",
            "name": "Netzwerkkabel Cat 6 (100m)",
        },
        {
            "lid": "4",
            "invoice_id": "1",
            "product_id": "28",
            "line_number": "2",
            "quantity": "333.0000",
            "unit_code": "MTR",
            "net_price": "55.0000",
            "vat_rate": "7.00",
            "net_line_total": "0.00",
            "delivery_date": "2025-11-12",
            "description": "Rolle Netzwerkkabel, 100 Meter.",
            "rid": "0",
            "unit_id": "4",
            "net_line_total__": "47730.00",
            "net_total": "18315.00",
            "vat_total": "1282.05",
            "gross_total": "19597.05",
            "name": "Netzwerkkabel Cat 6 (100m)",
        },
    ],
    "vat_breakdown": [
        {
            "vid": "44",
            "rid": "0",
            "vat_rate": "7.00",
            "tax_base_amount": "18315.00",
            "tax_amount": "1282.05",
            "invoice_id": "1",
        },
        {
            "vid": "43",
            "rid": "0",
            "vat_rate": "19.00",
            "tax_base_amount": "18315.00",
            "tax_amount": "3479.85",
            "invoice_id": "1",
        },
    ],
}
```

## Usage Example: Generate ZUGFeRD XML

The `q2zugferd_xml` function takes a `zugferd_data` dictionary (see structure above) and returns a ZUGFeRD-compliant XML string.

```python
from q2zugferd import q2zugferd_xml
from datasets.data1 import zugferd_data

# Generate ZUGFeRD XML string
xml_string = q2zugferd_xml(zugferd_data)

print(xml_string)  # Outputs the XML invoice as a string
```

- **Input:** `zugferd_data` (dict) – invoice data as described above.
- **Output:** XML string (str) – ready for embedding in PDF/A-3 or electronic transmission.

## Usage

```python
from q2zugferd import q2zugferd_xml, q2zugferd_pdf
from datasets.data1 import zugferd_data

# Generate ZUGFeRD XML
xml = q2zugferd_xml(zugferd_data)

# Embed XML into PDF/A-3
q2zugferd_pdf(
    "datasets/invoice1.pdf",      # Input PDF
    xml,                          # XML data (string)
    "temp/zugferd1.pdf",          # Output PDF/A-3 file
)
```

## Requirements

- Python 3.8+
- lxml
- pikepdf

## License

MIT

## References

- [ZUGFeRD Specification](https://www.ferd-net.de/)
- [Factur-X Standard](https://www.factur-x.org/)
