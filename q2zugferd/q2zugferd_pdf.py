import os
import pikepdf
from pikepdf import Dictionary, Name, Array, Stream
from importlib.resources import files


def replace_device_rgb_recursive(pdf, resources, icc_ref):
    """Рекурсивно заменяет DeviceRGB на ICCBased во всех ресурсах и объектах."""
    if not isinstance(resources, Dictionary):
        return

    # Установка DefaultRGB для текущего контекста ресурсов
    resources["/DefaultRGB"] = icc_ref

    # 1. Обработка словаря ColorSpace
    color_spaces = resources.get("/ColorSpace")
    if isinstance(color_spaces, Dictionary):
        for cs_name, cs_ref in list(color_spaces.items()):
            try:
                # Если прямая ссылка на Name("/DeviceRGB")
                if cs_ref == "/DeviceRGB" or cs_ref == Name("/DeviceRGB"):
                    color_spaces[cs_name] = Array([Name("/ICCBased"), icc_ref])
                else:
                    cs_obj = cs_ref.resolve()
                    if isinstance(cs_obj, (Dictionary, Array)) and "/DeviceRGB" in str(
                        cs_obj
                    ):
                        color_spaces[cs_name] = Array([Name("/ICCBased"), icc_ref])
            except Exception:
                pass

    # 2. Обработка XObjects (Images и Forms)
    xobjects = resources.get("/XObject")
    if isinstance(xobjects, Dictionary):
        for xobj_name, xobj_ref in xobjects.items():
            try:
                xobj = xobj_ref.resolve()
                if not isinstance(xobj, Dictionary):
                    continue

                # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ ДЛЯ ИЗОБРАЖЕНИЙ ---
                # Если само изображение использует /DeviceRGB
                if xobj.get("/Subtype") == "/Image":
                    cs = xobj.get("/ColorSpace")
                    if cs == "/DeviceRGB" or cs == Name("/DeviceRGB"):
                        # Заменяем прямо в объекте изображения
                        xobj["/ColorSpace"] = Array([Name("/ICCBased"), icc_ref])

                # Рекурсия для вложенных форм
                if xobj.get("/Subtype") == "/Form":
                    xobj_resources = xobj.get("/Resources", Dictionary())
                    replace_device_rgb_recursive(pdf, xobj_resources, icc_ref)
                    xobj["/Resources"] = xobj_resources

                # Исправление цветовой группы прозрачности
                group = xobj.get("/Group")
                if isinstance(group, Dictionary) and group.get("/CS") == "/DeviceRGB":
                    group["/CS"] = icc_ref
            except Exception:
                pass

    # 3. Исправление в паттернах (Patterns)
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
                        if (
                            isinstance(group, Dictionary)
                            and group.get("/S") == "/Transparency"
                        ):
                            if group.get("/CS") == "/DeviceRGB":
                                print(
                                    f"DeviceRGB found at {path}/XObject/{xobj_name}/Group/CS"
                                )
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


def q2zugferd_pdf(input_pdf, xml_path, output_pdf, pdfa_level="U"):
    (
        """_summary_

    Args:
        input_pdf (_type_): _description_
        xml_path (_type_): _description_
        output_pdf (_type_): _description_
        pdfa_level (str, optional): _description_. Defaults to "B".
    """
        """Main function with automatic DeviceRGB check"""
    )
    # --- Open PDF ---
    pdf = pikepdf.open(input_pdf)
    info = pdf.docinfo
    info["/Creator"] = "q2zugferd"

    # --- Load ICC profile ---
    icc_profile_path = files("q2zugferd").joinpath("icc/sRGB2014.icc")
    with open(icc_profile_path, "rb") as f:
        icc_data = f.read()
    icc_stream = pdf.make_stream(icc_data)
    icc_stream["/N"] = 3
    icc_ref = pdf.make_indirect(icc_stream)

    # --- OutputIntent ---
    oid = Dictionary(
        Type=Name.OutputIntent,
        S=Name("/GTS_PDFA1"),
        OutputCondition="sRGB",
        OutputConditionIdentifier="sRGB IEC61966-2.1",
        RegistryName="http://www.color.org",
        DestOutputProfile=icc_ref,
        Info="sRGB2014 ICC profile",
    )

    output_intent_ref = pdf.make_indirect(oid)
    output_intent = Array([output_intent_ref])

    pdf.Root["/OutputIntents"] = output_intent

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
    xml_filename = "factur-x.xml"
    xml_mime = Name("/text/xml")
    ef_stream = pdf.make_stream(xml_bytes)
    
    ef_stream["/Type"] = Name.EmbeddedFile
    ef_stream["/Subtype"] = xml_mime
    ef_stream["/Params"] = Dictionary()
    ef_stream["/Params"]["/CreationDate"] = info["/CreationDate"]
    ef_stream["/Params"]["/Size"] = ef_stream["/Length"]

    ef_stream_ref = pdf.make_indirect(ef_stream)

    files_dict = Dictionary()
    files_dict["/F"] = ef_stream_ref
    files_dict["/UF"] = ef_stream_ref
    files_dict_ref = pdf.make_indirect(files_dict)

    filespec = Dictionary(
        Type=Name.Filespec,
        F=xml_filename,
        UF=xml_filename,
    )
    filespec["/AFRelationship"] = Name("/Alternative")
    filespec["/Desc"] = "Invoice metadata: ZUGFeRD standard"
    filespec["/EF"] = files_dict_ref

    filespec_ref = pdf.make_indirect(filespec)

    ef_tree_dict = Dictionary()
    ef_tree_dict.Names = Array([xml_filename, filespec_ref])
    ef_tree_ref = pdf.make_indirect(ef_tree_dict)

    # Names dictionary
    if "/Names" not in pdf.Root:
        pdf.Root["/Names"] = Dictionary()

    if "/Names" not in pdf.Root:
        pdf.Root.Names = Dictionary()

    # Теперь pdf.Root.Names.EmbeddedFiles будет указывать на 16 0 R
    pdf.Root.Names.EmbeddedFiles = ef_tree_ref

    pdf.Root.Lang = "de-DE"
    if "/AF" not in pdf.Root:
        pdf.Root.AF = Array()
    pdf.Root.AF.append(filespec_ref)

    # Minimal XMP metadata with compliant extension schema
    profile_name = "EN 16931"
    xmp = f"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
 <rdf:RDF>
  <rdf:Description rdf:about="" xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
   <pdfaid:part>3</pdfaid:part>
   <pdfaid:conformance>{pdfa_level.upper()}</pdfaid:conformance>
  </rdf:Description>
  <rdf:Description rdf:about=""
    xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/"
    xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#"
    xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">
   <pdfaExtension:schemas>
    <rdf:Bag>
     <rdf:li rdf:parseType="Resource">
      <pdfaSchema:schema>Factur-X</pdfaSchema:schema>
      <pdfaSchema:namespaceURI>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI>
      <pdfaSchema:prefix>fx</pdfaSchema:prefix>
      <pdfaSchema:property>
       <rdf:Seq>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>Filename of embedded XML</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>DocumentType</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>Document type (INVOICE)</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>Version</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>ZUGFeRD version</pdfaProperty:description>
        </rdf:li>
        <rdf:li rdf:parseType="Resource">
         <pdfaProperty:name>Profile</pdfaProperty:name>
         <pdfaProperty:valueType>Text</pdfaProperty:valueType>
         <pdfaProperty:category>external</pdfaProperty:category>
         <pdfaProperty:description>ZUGFeRD profile</pdfaProperty:description>
        </rdf:li>
       </rdf:Seq>
      </pdfaSchema:property>
     </rdf:li>
    </rdf:Bag>
   </pdfaExtension:schemas>
  </rdf:Description>
  <rdf:Description rdf:about="" xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#">
   <fx:DocumentFileName>
    <rdf:Description>
     <rdf:value>factur-x.xml</rdf:value>
    </rdf:Description>
   </fx:DocumentFileName>
   <fx:DocumentType>
    <rdf:Description>
     <rdf:value>INVOICE</rdf:value>
    </rdf:Description>
   </fx:DocumentType>
   <fx:Version>
    <rdf:Description>
     <rdf:value>2.3.3</rdf:value>
    </rdf:Description>
   </fx:Version>
   <fx:Profile>
    <rdf:Description>
     <rdf:value>{profile_name}</rdf:value>
    </rdf:Description>
   </fx:Profile>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""

    meta_stream = pdf.make_stream(xmp.encode("utf-8"))
    meta_stream["/Type"] = "/Metadata"
    meta_stream["/Subtype"] = "/XML"
    pdf.Root["/Metadata"] = pdf.make_indirect(meta_stream)

    # --- Save ---
    pdf.save(output_pdf, linearize=False, compress_streams=False)
    pdf.close()

    # --- Automatic check after saving ---
    pdf_check = pikepdf.open(output_pdf)
    scan_for_device_rgb(pdf_check)
    pdf_check.close()
