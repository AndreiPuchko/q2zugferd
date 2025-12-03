import os
import pikepdf
from pikepdf import Dictionary

def Name(x):
    return x


def q2zugferd_pdf(
    input_pdf: str,
    xml_path: str | bytes,
    output_pdf: str,
    icc_profile_path: str,
    pdfa_level="B",  # "A" or "B"
    xml_mime="application/xml",
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

    # Создание ICC потока
    icc_stream = pdf.make_stream(icc_data)
    icc_stream["/N"] = 3
    icc_stream["/Alternate"] = "/DeviceRGB"

    # OutputIntent
    pdf.Root.OutputIntents = [
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

    # --- Ensure DefaultRGB for DeviceRGB ---
    if "/Resources" not in pdf.Root:
        pdf.Root["/Resources"] = Dictionary()
    pdf.Root["/Resources"]["/DefaultRGB"] = pdf.make_indirect(icc_stream)

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
    ef_stream.Subtype = xml_mime

    filename = "zugferd-invoice.xml"

    # --- 5. FileSpec with AFRelationship & Subtype ---
    file_spec = Dictionary(
        {
            "/Type": "/Filespec",
            "/F": filename,
            "/UF": filename,
            "/Subtype": xml_mime,  # ✅ required for veraPDF
            "/AFRelationship": "/Data",  # ✅ required for PDF/A-3
            "/EF": Dictionary({"/F": pdf.make_indirect(ef_stream)}),
            "/Desc": "ZUGFeRD / Factur-X Invoice XML",
        }
    )
    file_spec["/AFRelationship"] = "/Data"

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
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    meta_stream = pdf.make_stream(xmp)
    meta_stream["/Type"] = "/Metadata"
    meta_stream["/Subtype"] = "/XML"
    pdf.Root["/Metadata"] = pdf.make_indirect(meta_stream)

    with pdf.open_metadata(set_pikepdf_as_editor=True) as meta:
        meta["pdfaid:part"] = "3"
        meta["pdfaid:conformance"] = pdfa_level  # "B"

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
