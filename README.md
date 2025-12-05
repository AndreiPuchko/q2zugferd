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
