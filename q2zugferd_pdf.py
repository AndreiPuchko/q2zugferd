import os
import datetime
import hashlib
import pikepdf
from pikepdf import Dictionary, Name, Array


def replace_device_rgb_recursive(pdf, resources, icc_ref):
    """Recursively replace all DeviceRGB ColorSpaces in resources with ICCBased"""
    if not isinstance(resources, Dictionary):
        return

    resources["/DefaultRGB"] = icc_ref

    # Replace /ColorSpace entries
    color_spaces = resources.get("/ColorSpace")
    if isinstance(color_spaces, Dictionary):
        for cs_name, cs_ref in list(color_spaces.items()):
            try:
                # If cs_ref is a direct Name("/DeviceRGB")
                if cs_ref == Name("/DeviceRGB") or cs_ref == "/DeviceRGB":
                    icc_array = Array([Name("/ICCBased"), icc_ref, 3])
                    color_spaces[cs_name] = pdf.make_indirect(icc_array)
                else:
                    cs = cs_ref.resolve()
                    if isinstance(cs, Dictionary) and cs.get("/CS") == "/DeviceRGB":
                        icc_array = Array([Name("/ICCBased"), icc_ref, 3])
                        color_spaces[cs_name] = pdf.make_indirect(icc_array)
            except Exception:
                pass

    # XObjects
    xobjects = resources.get("/XObject")
    if isinstance(xobjects, Dictionary):
        for xobj_name, xobj_ref in xobjects.items():
            try:
                xobj = xobj_ref.resolve()
                if isinstance(xobj, Dictionary):
                    if xobj.get("/Subtype") == "/Form":
                        xobj_resources = xobj.get("/Resources", Dictionary())
                        replace_device_rgb_recursive(pdf, xobj_resources, icc_ref)
                        xobj["/Resources"] = xobj_resources
                    group = xobj.get("/Group")
                    if isinstance(group, Dictionary) and group.get("/S") == "/Transparency":
                        if group.get("/CS") == "/DeviceRGB":
                            group["/CS"] = icc_ref
            except Exception:
                pass

    # Patterns
    patterns = resources.get("/Pattern")
    if isinstance(patterns, Dictionary):
        for pat_name, pat_ref in patterns.items():
            try:
                pat = pat_ref.resolve()
                if isinstance(pat, Dictionary):
                    pat_res = pat.get("/Resources", Dictionary())
                    replace_device_rgb_recursive(pdf, pat_res, icc_ref)
                    pat["/Resources"] = pat_res
            except Exception:
                pass

    # ExtGState
    extgstate = resources.get("/ExtGState")
    if isinstance(extgstate, Dictionary):
        for gs_name, gs_ref in extgstate.items():
            try:
                gs = gs_ref.resolve()
                if isinstance(gs, Dictionary):
                    if "/BG" in gs and gs["/BG"] == "/DeviceRGB":
                        gs["/BG"] = icc_ref
                    if "/BG2" in gs and gs["/BG2"] == "/DeviceRGB":
                        gs["/BG2"] = icc_ref
            except Exception:
                pass


def scan_for_device_rgb(pdf):
    """Scan entire PDF for any remaining DeviceRGB references"""
    issues_found = 0

    def check_resources(resources, path="Root"):
        nonlocal issues_found
        if not isinstance(resources, Dictionary):
            return

        # ColorSpaces
        color_spaces = resources.get("/ColorSpace")
        if isinstance(color_spaces, Dictionary):
            for cs_name, cs_ref in color_spaces.items():
                if cs_ref == "/DeviceRGB":
                    print(f"DeviceRGB found at {path}/ColorSpace/{cs_name}")
                    issues_found += 1

        # XObjects
        xobjects = resources.get("/XObject")
        if isinstance(xobjects, Dictionary):
            for xobj_name, xobj_ref in xobjects.items():
                try:
                    xobj = xobj_ref.resolve()
                    if isinstance(xobj, Dictionary):
                        xobj_resources = xobj.get("/Resources", Dictionary())
                        check_resources(xobj_resources, path + f"/XObject/{xobj_name}")
                        group = xobj.get("/Group")
                        if isinstance(group, Dictionary) and group.get("/S") == "/Transparency":
                            if group.get("/CS") == "/DeviceRGB":
                                print(f"DeviceRGB found at {path}/XObject/{xobj_name}/Group/CS")
                                issues_found += 1
                except Exception:
                    pass

        # Patterns
        patterns = resources.get("/Pattern")
        if isinstance(patterns, Dictionary):
            for pat_name, pat_ref in patterns.items():
                try:
                    pat = pat_ref.resolve()
                    if isinstance(pat, Dictionary):
                        pat_res = pat.get("/Resources", Dictionary())
                        check_resources(pat_res, path + f"/Pattern/{pat_name}")
                except Exception:
                    pass

        # ExtGState
        extgstate = resources.get("/ExtGState")
        if isinstance(extgstate, Dictionary):
            for gs_name, gs_ref in extgstate.items():
                try:
                    gs = gs_ref.resolve()
                    if isinstance(gs, Dictionary):
                        if "/BG" in gs and gs["/BG"] == "/DeviceRGB":
                            print(f"DeviceRGB found at {path}/ExtGState/{gs_name}/BG")
                            issues_found += 1
                        if "/BG2" in gs and gs["/BG2"] == "/DeviceRGB":
                            print(f"DeviceRGB found at {path}/ExtGState/{gs_name}/BG2")
                            issues_found += 1
                except Exception:
                    pass

    # Check pages
    for i, page in enumerate(pdf.pages):
        resources = page.get("/Resources", Dictionary())
        check_resources(resources, f"Page[{i}]")
        group = page.get("/Group")
        if isinstance(group, Dictionary) and group.get("/S") == "/Transparency":
            if group.get("/CS") == "/DeviceRGB":
                print(f"DeviceRGB found at Page[{i}]/Group/CS")
                issues_found += 1

    if issues_found == 0:
        print("✅ No DeviceRGB references found. PDF is ready for PDF/A-3B validation.")
    else:
        print(f"⚠️ Total DeviceRGB references remaining: {issues_found}")


def q2zugferd_pdf(input_pdf, xml_path, output_pdf, icc_profile_path, pdfa_level="B"):
    """Main function with automatic DeviceRGB check"""
    # --- Open PDF ---
    pdf = pikepdf.open(input_pdf)

    # --- Load ICC profile ---
    with open(icc_profile_path, "rb") as f:
        icc_data = f.read()
    icc_stream = pdf.make_stream(icc_data)
    icc_stream["/N"] = 3
    icc_ref = pdf.make_indirect(icc_stream)

    # --- OutputIntent ---
    output_intent = Dictionary(
        {
            "/Type": "/OutputIntent",
            "/S": "/GTS_PDFA1",
            "/OutputConditionIdentifier": "sRGB IEC61966-2.1",
            "/RegistryName": "http://www.color.org",
            "/DestOutputProfile": icc_ref,
            "/Info": "sRGB2014 ICC profile",
        }
    )
    pdf.Root["/OutputIntents"] = [output_intent]

    # --- Fix DeviceRGB ---
    if "/Resources" not in pdf.Root:
        pdf.Root["/Resources"] = Dictionary()
    replace_device_rgb_recursive(pdf, pdf.Root["/Resources"], icc_ref)
    for page in pdf.pages:
        resources = page.get("/Resources", Dictionary())
        replace_device_rgb_recursive(pdf, resources, icc_ref)
        page["/Resources"] = resources
        group = page.get("/Group")
        if isinstance(group, Dictionary) and group.get("/S") == "/Transparency":
            if group.get("/CS") == "/DeviceRGB":
                group["/CS"] = icc_ref

    # --- Embed XML (ZUGFeRD) ---
    if isinstance(xml_path, (bytes, bytearray)):
        xml_bytes = xml_path
    elif os.path.isfile(xml_path):
        with open(xml_path, "rb") as f:
            xml_bytes = f.read()
    else:
        xml_bytes = xml_path.encode("utf-8")
    xml_filename = "zugferd-invoice.xml"
    xml_mime = Name("/application/xml")
    ef_stream = pdf.make_stream(xml_bytes)
    ef_stream["/Type"] = "/EmbeddedFile"
    ef_stream["/Subtype"] = xml_mime
    file_spec = Dictionary(
        {
            "/Type": "/Filespec",
            "/F": xml_filename,
            "/UF": xml_filename,
            "/AFRelationship": Name("/Data"),
            "/Subtype": xml_mime,
            "/EF": Dictionary({"/F": pdf.make_indirect(ef_stream)}),
            "/Desc": "ZUGFeRD Invoice",
        }
    )
    file_spec_ref = pdf.make_indirect(file_spec)

    # Names dictionary
    if "/Names" not in pdf.Root:
        pdf.Root["/Names"] = Dictionary()
    names = pdf.Root["/Names"]
    if "/EmbeddedFiles" not in names:
        names["/EmbeddedFiles"] = Dictionary()
    embedded_files = names["/EmbeddedFiles"]
    if "/Names" not in embedded_files:
        embedded_files["/Names"] = []
    embedded_files["/Names"].extend([xml_filename, file_spec_ref])
    if "/AF" not in pdf.Root:
        pdf.Root["/AF"] = []
    pdf.Root["/AF"].append(file_spec_ref)

    # Minimal XMP metadata
    xmp = f"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
   <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
     <pdfaid:part>3</pdfaid:part>
     <pdfaid:conformance>{pdfa_level.upper()}</pdfaid:conformance>
   </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    meta_stream = pdf.make_stream(xmp.encode("utf-8"))
    meta_stream["/Type"] = "/Metadata"
    meta_stream["/Subtype"] = "/XML"
    pdf.Root["/Metadata"] = pdf.make_indirect(meta_stream)

    # --- Save ---
    pdf.save(output_pdf, linearize=True)
    pdf.close()

    # --- Automatic check after saving ---
    pdf_check = pikepdf.open(output_pdf)
    scan_for_device_rgb(pdf_check)
    pdf_check.close()
