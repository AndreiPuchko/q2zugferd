from q2zugferd_xml import q2zugferd_xml
from q2zugferd_pdf import q2zugferd_pdf
from datasets.data1 import zugferd_data as zugferd_data

xml = q2zugferd_xml(zugferd_data)

q2zugferd_pdf("datasets/invoice1.pdf", xml, "temp/zugferd1.pdf", "icc/sRGB2014.icc")
