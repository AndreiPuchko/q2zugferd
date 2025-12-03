import os
import datetime
import hashlib
import pikepdf
from pikepdf import Dictionary, Name


def q2zugferd_pdf(
    input_pdf: str,
    xml_path: str | bytes,
    output_pdf: str,
    icc_profile_path: str,
    pdfa_level="B",
):
    """
    Create PDF/A-3 with embedded ZUGFeRD / Factur-X XML.
    """

    # --- 1. Load Data ---
    if isinstance(xml_path, (bytes, bytearray)):
        xml_bytes = xml_path
        xml_size = len(xml_bytes)
        mod_date = datetime.datetime.now()
    elif os.path.isfile(xml_path):
        with open(xml_path, "rb") as f:
            xml_bytes = f.read()
        xml_size = os.path.getsize(xml_path)
        mod_date = datetime.datetime.fromtimestamp(os.path.getmtime(xml_path))
    else:
        xml_bytes = xml_path.encode("utf-8")
        xml_size = len(xml_bytes)
        mod_date = datetime.datetime.now()

    if not os.path.exists(icc_profile_path):
        raise FileNotFoundError(f"ICC profile not found: {icc_profile_path}")

    with open(icc_profile_path, "rb") as f:
        icc_data = f.read()

    # --- 2. Open PDF and Setup OutputIntent & DefaultRGB ---
    pdf = pikepdf.open(input_pdf)

    # ICC Stream Setup
    icc_stream = pdf.make_stream(icc_data)
    icc_stream["/N"] = 3
    icc_ref = pdf.make_indirect(icc_stream)  # Store the reference once

    # OutputIntent Setup
    output_intent = Dictionary(
        {
            "/Type": "/OutputIntent",
            "/S": "/GTS_PDFA1",
            "/OutputConditionIdentifier": "sRGB IEC61966-2.1",
            "/RegistryName": "http://www.color.org",
            "/DestOutputProfile": icc_ref,
            "/Info": "sRGB IEC61966-2.1",
        }
    )
    pdf.Root["/OutputIntents"] = [output_intent]

    # CRITICAL FIX: Set DefaultRGB for the document and all pages
    if "/Resources" not in pdf.Root:
        pdf.Root["/Resources"] = Dictionary()
    pdf.Root["/Resources"]["/DefaultRGB"] = icc_ref

    for page in pdf.pages:
        # Create or retrieve the resources dictionary
        resources = page.get("/Resources", Dictionary())
        page["/Resources"] = resources

        # Ensure DefaultRGB is set at the page level for DeviceRGB usage
        resources["/DefaultRGB"] = icc_ref

    # --- 3. Embed XML File ---

    pdf_date_str = mod_date.strftime("D:%Y%m%d%H%M%S+00'00'")
    md5_checksum = hashlib.md5(xml_bytes).digest()

    xml_mime_name = Name(r"/application/xml")

    # EmbeddedFile Stream Dictionary
    ef_stream = pdf.make_stream(xml_bytes)
    ef_stream["/Type"] = "/EmbeddedFile"
    ef_stream["/Subtype"] = xml_mime_name  # FIX: Setting Subtype here is correct

    ef_stream["/Params"] = Dictionary(
        {
            "/Size": xml_size,
            "/ModDate": pdf_date_str,
            "/CreationDate": pdf_date_str,
            "/CheckSum": md5_checksum,
        }
    )

    filename = "zugferd-invoice.xml"

    # File Specification Dictionary (CRITICAL FIXES HERE)
    file_spec = Dictionary(
        {
            "/Type": "/Filespec",
            "/F": filename,
            "/UF": filename,
            # FIX (Test 3): Ensure AFRelationship is present
            "/AFRelationship": Name("/Data"),
            "/Desc": "ZUGFeRD Invoice",
            # FIX (Test 1): Ensure Subtype is also present in the FileSpec dictionary
            "/Subtype": xml_mime_name,
            "/EF": Dictionary({"/F": pdf.make_indirect(ef_stream)}),
        }
    )

    file_spec_ref = pdf.make_indirect(file_spec)

    # --- 4. Register Attachment in PDF Structure ---

    if "/Names" not in pdf.Root:
        pdf.Root["/Names"] = Dictionary()

    names = pdf.Root["/Names"]
    if "/EmbeddedFiles" not in names:
        names["/EmbeddedFiles"] = Dictionary()

    embedded_files = names["/EmbeddedFiles"]
    if "/Names" not in embedded_files:
        embedded_files["/Names"] = []

    embedded_files["/Names"].extend([filename, file_spec_ref])

    if "/AF" not in pdf.Root:
        pdf.Root["/AF"] = []
    pdf.Root["/AF"].append(file_spec_ref)

    # --- 5. XMP Metadata (ZUGFeRD Schema) ---
    rdf_zugferd = """
    <rdf:Description rdf:about="" xmlns:zf="urn:ferd:pdfa:CrossIndustryDocument:invoice:1p0#">
      <zf:DocumentType>INVOICE</zf:DocumentType>
      <zf:DocumentFileName>zugferd-invoice.xml</zf:DocumentFileName>
      <zf:Version>1.0</zf:Version>
      <zf:ConformanceLevel>BASIC</zf:ConformanceLevel>
    </rdf:Description>
    
    <rdf:Description rdf:about="" xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/"
                     xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#"
                     xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">
      <pdfaExtension:schemas>
        <rdf:Bag>
          <rdf:li rdf:parseType="Resource">
            <pdfaSchema:schema>ZUGFeRD PDFA Extension Schema</pdfaSchema:schema>
            <pdfaSchema:namespaceURI>urn:ferd:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI>
            <pdfaSchema:prefix>zf</pdfaSchema:prefix>
            <pdfaSchema:property>
              <rdf:Seq>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>name of the embedded XML invoice file</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentType</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>INVOICE</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>Version</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The actual version of the ZUGFeRD XML schema</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The conformance level of the embedded ZUGFeRD data</pdfaProperty:description>
                </rdf:li>
              </rdf:Seq>
            </pdfaSchema:property>
          </rdf:li>
        </rdf:Bag>
      </pdfaExtension:schemas>
    </rdf:Description>
    """

    xmp_template = f"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
    <x:xmpmeta xmlns:x='adobe:ns:meta/'>
      <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
        <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
          <pdfaid:part>3</pdfaid:part>
          <pdfaid:conformance>{pdfa_level.upper()}</pdfaid:conformance>
        </rdf:Description>
        {rdf_zugferd}
      </rdf:RDF>
    </x:xmpmeta>
    <?xpacket end='w'?>"""

    meta_stream = pdf.make_stream(xmp_template.encode("utf-8"))
    meta_stream["/Type"] = "/Metadata"
    meta_stream["/Subtype"] = "/XML"
    pdf.Root["/Metadata"] = pdf.make_indirect(meta_stream)

    # --- 6. Save ---
    # The pdfa_mode argument is not used; compliance is achieved by setting the correct structure.
    pdf.save(output_pdf, linearize=True)
    pdf.close()
