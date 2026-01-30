from q2zugferd import q2zugferd_pdf, q2zugferd_xml
from datasets.data1 import zugferd_data as zugferd_data

xml = q2zugferd_xml(zugferd_data)
open("temp/factur.xml", "w").write(xml)
q2zugferd_pdf("datasets/invoice0.pdf", xml, "temp/zugferd1.pdf")
