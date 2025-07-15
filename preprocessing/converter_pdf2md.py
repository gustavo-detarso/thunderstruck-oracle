import os
from unstructured.partition.pdf import partition_pdf

DATA_DIR = "data"

def salvar_markdown(path_pdf, output_path):
    print(f"Processando: {path_pdf}")
    try:
        # Só languages, sem ocr_languages!
        elements = partition_pdf(filename=path_pdf, languages=["por"])
        print(f"Elementos extraídos: {len(elements)}")
    except Exception as e:
        print(f"Erro ao extrair: {e}")
        with open(output_path + ".err.txt", "w", encoding="utf-8") as f:
            f.write(str(e))
        return

    if not elements or len(elements) == 0:
        with open(output_path + ".empty.txt", "w", encoding="utf-8") as f:
            f.write("NENHUM TEXTO EXTRAÍDO!")
        print(f"Nenhum texto extraído de {path_pdf}.")
        return

    md_lines = []
    for el in elements:
        if el.category == "Title":
            md_lines.append(f"# {el.text.strip()}")
        elif el.category == "NarrativeText":
            md_lines.append(el.text.strip())
        elif el.category == "List":
            for item in el.text.strip().split("\n"):
                md_lines.append(f"- {item.strip()}")
        elif el.category == "Table":
            md_lines.append("\n**Tabela:**\n")
            md_lines.append(el.text.strip())
            md_lines.append("\n")
        else:
            md_lines.append(el.text.strip())
    md_content = "\n\n".join(md_lines)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"✅ Salvo: {output_path}")

def varrer_pdfs(data_dir):
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                abs_path = os.path.join(root, file)
                output_path = abs_path[:-4] + ".md"
                salvar_markdown(abs_path, output_path)

if __name__ == "__main__":
    varrer_pdfs(DATA_DIR)

