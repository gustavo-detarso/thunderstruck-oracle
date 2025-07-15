import pdfplumber

def pdf_para_texto(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() or ""
            texto += "\n"
    return texto

