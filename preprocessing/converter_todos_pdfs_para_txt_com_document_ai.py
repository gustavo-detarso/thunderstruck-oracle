from pathlib import Path
from document_ai_utils import processar_pdf_com_document_ai

def converter_todos_pdfs_para_txt_com_document_ai(
    data_dir='./data/',
    json_key_path='/home/gustavodetarso/Documentos/thunderstruck-oracle/config/extrator-de-pdf-466005-274c224a0b2c.json',
    project_id='extrator-de-pdf-466005',
    location='us',
    processor_id='37610ad7919cad3a'
):
    diretorio = Path(data_dir)
    pdfs = list(diretorio.rglob('*.pdf')) + list(diretorio.rglob('*.PDF'))

    if not pdfs:
        print("Nenhum PDF encontrado no diretório.")
        return

    for pdf_path in pdfs:
        print(f"Processando com Document AI: {pdf_path}")
        txt_path, csv_paths = processar_pdf_com_document_ai(
            pdf_path=str(pdf_path),
            json_key_path=json_key_path,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            output_dir=str(diretorio)
        )
        print(f"Arquivo TXT gerado: {txt_path}")
        for csv in csv_paths:
            print(f"Arquivo CSV gerado: {csv}")

if __name__ == "__main__":
    converter_todos_pdfs_para_txt_com_document_ai()

