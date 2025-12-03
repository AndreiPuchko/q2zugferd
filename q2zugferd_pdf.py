import os
import pikepdf
from pikepdf import Dictionary, Name


def q2zugferd_pdf(
    input_pdf: str,
    xml_path: str | bytes,
    output_pdf: str,
    icc_profile_path: str,
    pdfa_level="B",  # "A" or "B"
    xml_mime="application/octet-stream",
):
    """
    Create PDF/A-3 with embedded ZUGFeRD / Factur-X XML.
    """

    # --- Open source PDF ---
    pdf = pikepdf.open(input_pdf)

    # --- 1. Load ICC profile ---
    try:
        with open(icc_profile_path, "rb") as f:
            icc_data = f.read()
    except FileNotFoundError:
        pdf.close()
        raise FileNotFoundError(f"ICC profile not found: {icc_profile_path}")

    # Create ICC stream
    icc_stream = pdf.make_stream(icc_data)
    icc_stream["/N"] = 3  # 3 channels for RGB
    icc_stream["/Alternate"] = "/DeviceRGB"

    # Ensure the ICC profile is RGB (user must provide a valid RGB ICC profile)
    # If you want to enforce, you could check the profile header, but this is usually not necessary.

    # OutputIntent
    pdf.Root["/OutputIntents"] = [
        Dictionary(
            {
                "/Type": "/OutputIntent",
                "/S": "/GTS_PDFA1",
                "/OutputCondition": "Custom",
                "/OutputConditionIdentifier": "Custom",
                "/DestOutputProfile": pdf.make_indirect(icc_stream),
            }
        )
    ]

    # Ensure DefaultRGB for DeviceRGB in document root
    if "/Resources" not in pdf.Root:
        pdf.Root["/Resources"] = Dictionary()
    pdf.Root["/Resources"]["/DefaultRGB"] = pdf.make_indirect(icc_stream)

    # Ensure DefaultRGB for DeviceRGB in every page
    for page in pdf.pages:
        resources = page.get("/Resources", Dictionary())
        page["/Resources"] = resources
        resources["/DefaultRGB"] = pdf.make_indirect(icc_stream)

    # --- 3. Read XML ---
    if isinstance(xml_path, (bytes, bytearray)):
        xml_bytes = xml_path
    elif os.path.isfile(xml_path):
        with open(xml_path, "rb") as f:
            xml_bytes = f.read()
    else:
        xml_bytes = xml_path.encode("utf-8")

    # --- 4. EmbeddedFile stream ---
    ef_stream = pdf.make_stream(xml_bytes)
    ef_stream["/Type"] = "/EmbeddedFile"
    ef_stream["/Subtype"] = "application/xml"  # Valid MIME type for ZUGFeRD XML

    filename = "zugferd-invoice.xml"

    # --- 5. FileSpec with AFRelationship & Subtype ---
    file_spec = Dictionary(
        {
            "/Type": "/Filespec",
            "/F": filename,
            "/UF": filename,
            "/Subtype": "application/xml",  # Valid MIME type for ZUGFeRD XML
            "/AFRelationship": Name("/Data"),
            "/EF": Dictionary({"/F": pdf.make_indirect(ef_stream)}),
            "/Desc": "ZUGFeRD / Factur-X Invoice XML",
        }
    )

    file_spec_ref = pdf.make_indirect(file_spec)

    # --- 6. Names → EmbeddedFiles ---
    names_dict = pdf.Root.get("/Names", Dictionary())
    pdf.Root["/Names"] = names_dict

    embedded_files = names_dict.get("/EmbeddedFiles", Dictionary())
    names_dict["/EmbeddedFiles"] = embedded_files

    names_array = embedded_files.get("/Names")
    if names_array is None:
        embedded_files["/Names"] = [filename, file_spec_ref]
    else:
        names_array.extend([filename, file_spec_ref])

    # --- 7. AF (mandatory for PDF/A-3 attachments) ---
    pdf.Root["/AF"] = [file_spec_ref]

    # --- 8. Minimal XMP Metadata stream (required) ---
    xmp = b"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description rdf:about=""
    xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
   <pdfaid:part>3</pdfaid:part>
   <pdfaid:conformance>B</pdfaid:conformance>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    meta_stream = pdf.make_stream(xmp)
    meta_stream["/Type"] = "/Metadata"
    meta_stream["/Subtype"] = "/XML"
    pdf.Root["/Metadata"] = pdf.make_indirect(meta_stream)

    # --- 9. Save as PDF/A-3B ---
    try:
        from pikepdf import PdfA

        if pdfa_level.upper() == "A":
            pdfa_mode = PdfA.PDFA_3A
        else:
            pdfa_mode = PdfA.PDFA_3B

        pdf.save(
            output_pdf,
            pdfa_mode=pdfa_mode,
            linearize=True,
        )

    except ImportError:
        # Older pikepdf versions
        pdf.save(output_pdf, linearize=True)
