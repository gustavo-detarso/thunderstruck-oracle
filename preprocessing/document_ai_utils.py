from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from pathlib import Path
import csv

def processar_pdf_com_document_ai(
    pdf_path: str,
    json_key_path: str,
    project_id: str,
    location: str,
    processor_id: str,
    output_dir: str = "./data"
):
    """
    Processa o PDF usando Google Document AI, extrai texto e tabelas,
    salva TXT e CSVs no diretório especificado.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        json_key_path: Caminho para o JSON da conta de serviço.
        project_id: ID do projeto Google Cloud.
        location: Região do processador (ex: "us" ou "us-central1").
        processor_id: ID do processador do Document AI.
        output_dir: Diretório onde salvar os arquivos gerados.
    """
    credentials = service_account.Credentials.from_service_account_file(json_key_path)
    client = documentai.DocumentProcessorServiceClient(credentials=credentials)

    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    with open(pdf_path, "rb") as f:
        pdf_content = f.read()

    raw_document = documentai.RawDocument(content=pdf_content, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    document = result.document

    # Cria pasta de saída se não existir
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Salva texto completo em TXT
    txt_path = output_path / (Path(pdf_path).stem + ".txt")
    with open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(document.text)
    print(f"Texto salvo em: {txt_path}")

    # Extrai tabelas e salva CSV(s)
    csv_paths = []
    for i, page in enumerate(document.pages):
        for j, table in enumerate(page.tables):
            csv_path = output_path / f"{Path(pdf_path).stem}_page{i+1}_table{j+1}.csv"
            with open(csv_path, "w", newline='', encoding="utf-8") as f_csv:
                writer = csv.writer(f_csv)
                # Cabeçalho e linhas do corpo da tabela
                for row in table.header_rows + table.body_rows:
                    cells = [cell.layout.text_anchor.content.strip() for cell in row.cells]
                    writer.writerow(cells)
            csv_paths.append(csv_path)
            print(f"Tabela salva em: {csv_path}")

    return txt_path, csv_paths

