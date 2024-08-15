#python3 -m pip install python-docx
#python3 -m pip install pypandoc
#python3 -m pip install docx2pdf
 
#python3 -m pip install pdfkit
#sudo apt-get install wkhtmltopdf
#sudo apt-get update
#sudo apt-get install libreoffice



import io
from docx import Document
import pdfkit
from tempfile import NamedTemporaryFile


import io
from docx import Document
import subprocess
from tempfile import NamedTemporaryFile

def replace_text_in_docx_in_memory(template_path, replacements): 
    doc = Document(template_path) 
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value) 
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def convert_docx_to_pdf_with_libreoffice(docx_buffer): 
    with NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
        temp_docx_file.write(docx_buffer.getvalue())
        temp_docx_path = temp_docx_file.name 
    temp_pdf_path = temp_docx_path.replace('.docx', '.pdf') 
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', temp_docx_path, '--outdir', '/tmp'])

    with open(temp_pdf_path, 'rb') as pdf_file:
        pdf_buffer = io.BytesIO(pdf_file.read()) 
    subprocess.run(['rm', temp_docx_path, temp_pdf_path]) 
    return pdf_buffer



# Example usage
template_path = '/var/www/html/skytron_backend/Skytronsystem/skytron_api/static/Cetificate_template.docx'
aa="test"
def geneateCet(savepath,IMEI,Make,Model,Validity,RegNo,FitmentDate,TaggingDate,ActivationDate,Status,Date):
    replacements = {
        '{{IMEI}}':IMEI,
        '{{Make}}':Make ,
        '{{Model}}':Model,
        '{{Validity}}':Validity,
        '{{RegNo}}':RegNo,
        '{{FitmentDate}}':FitmentDate,
        '{{TaggingDate}}':TaggingDate,
        '{{ActivationDate}}':ActivationDate,
        '{{Status}}':Status,
        '{{Date}}':Date     
    }
    docx_buffer = replace_text_in_docx_in_memory(template_path, replacements)
    pdf_buffer = convert_docx_to_pdf_with_libreoffice(docx_buffer)
    with open(savepath+'.pdf', 'wb') as f:
        f.write(pdf_buffer.getvalue())

