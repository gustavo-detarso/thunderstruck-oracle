import os
import re
import pandas as pd
from pathlib import Path
from pdfminer.high_level import extract_text

def pdf_para_txt(pdf_path, txt_path):
    texto = extract_text(pdf_path)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(texto)
    print(f"PDF convertido: {pdf_path} -> {txt_path}")

def extrair_tabela_robusta(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        linhas = [l.strip() for l in f.readlines()]

    linhas = [re.sub(r'[\r\n]+', '', l) for l in linhas if l.strip()]

    registros = []
    buffer = ""

    for linha in linhas:
        if re.match(r"^[A-Z]{2}\.", linha):
            if buffer:
                registros.append(buffer.strip())
            buffer = linha
        else:
            buffer += " " + linha

    if buffer:
        registros.append(buffer.strip())

    padrao = re.compile(
        r"([A-Z]{2})\.\s*([A-ZÀ-ÿ\s]+?)\.?\s*APS\s+([A-ZÀ-ÿ\s\.]+)",
        re.IGNORECASE
    )

    resultados = []
    for rec in registros:
        match = padrao.search(rec)
        if match:
            uf = match.group(1).strip().upper()
            cidade = match.group(2).replace('.', '').strip()
            unidade = match.group(3).replace('.', '').strip()
            resultados.append({'Estado': uf, 'Cidade': cidade, 'Unidade': unidade})
        else:
            print(f"Registro ignorado (não bateu padrão): {rec[:100]}...")

    df = pd.DataFrame(resultados)
    return df

def posprocessar_txt_para_csv_se_tabela(txt_path):
    if not txt_path.name.endswith('[tabela].txt'):
        return

    csv_path = txt_path.with_suffix('.csv')
    if csv_path.exists():
        print(f"Arquivo CSV já existe, pulando conversão: {csv_path}")
        return

    df = extrair_tabela_robusta(txt_path)
    if not df.empty:
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"Conversão robusta concluída! Arquivo salvo como: {csv_path}")
    else:
        print(f"Nenhum dado válido extraído de: {txt_path}")

def converter_todos_pdfs_para_txt(diretorio='./data/'):
    diretorio = Path(diretorio)
    pdfs = list(diretorio.rglob('*.pdf')) + list(diretorio.rglob('*.PDF'))

    if not pdfs:
        print("Nenhum PDF encontrado no diretório.")
        return

    for pdf_path in pdfs:
        txt_path = pdf_path.with_suffix('.txt')
        pdf_para_txt(str(pdf_path), str(txt_path))

        if pdf_path.name.endswith('[tabela].pdf'):
            posprocessar_txt_para_csv_se_tabela(txt_path)

if __name__ == "__main__":
    converter_todos_pdfs_para_txt('./data/')

