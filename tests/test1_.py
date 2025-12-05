from q2zugferd import q2zugferd_xml, q2zugferd_pdf
from datasets.data1 import zugferd_data
import os


def test_xml_generation():
    xml = q2zugferd_xml(zugferd_data)
    assert isinstance(xml, str)
    assert xml.startswith("<?xml")


def test_pdf_generation(tmp_path):
    xml = q2zugferd_xml(zugferd_data)
    input_pdf = "datasets/invoice1.pdf"
    output_pdf = tmp_path / "zugferd_test.pdf"
    q2zugferd_pdf(input_pdf, xml, str(output_pdf))
    assert os.path.isfile(output_pdf)
    assert os.path.getsize(output_pdf) > 0
