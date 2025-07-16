import difflib
import pandas as pd
import os
import re

def buscar_csv_em_subpastas(nome_csv_parcial, raiz="data"):
    for root, dirs, files in os.walk(raiz):
        for file in files:
            if file.endswith(".csv") and nome_csv_parcial in file:
                caminho_encontrado = os.path.join(root, file)
                print(f"[DEBUG] CSV encontrado: {caminho_encontrado}")
                return caminho_encontrado
    for root, dirs, files in os.walk("/mnt/data"):
        for file in files:
            if file.endswith(".csv") and nome_csv_parcial in file:
                caminho_encontrado = os.path.join(root, file)
                print(f"[DEBUG] CSV encontrado (mnt/data): {caminho_encontrado}")
                return caminho_encontrado
    print("[DEBUG] Nenhum CSV encontrado!")
    return None

def contem_palavra_semelhante(texto, palavras, cutoff=0.7):
    return any(
        difflib.get_close_matches(p, [texto], n=1, cutoff=cutoff)
        for p in palavras
    )

def busca_tabela_estruturada(pergunta, nome_csv_parcial="portaria_dpmf-srgps-mps_1424_2025"):
    csv_path = buscar_csv_em_subpastas(nome_csv_parcial)
    if not csv_path or not os.path.exists(csv_path):
        # fallback para ambiente local:
        csv_path = "/mnt/data/portaria_dpmf-srgps-mps_1424_2025[tabela].csv"
        if not os.path.exists(csv_path):
            print("[DEBUG] CSV realmente não encontrado em nenhum lugar.")
            return None, None
        else:
            print(f"[DEBUG] Usando CSV local: {csv_path}")

    uf = None
    uf_nome = None
    uf_match = re.search(r"\b(?:no|na|em|do|da|de|para)\s+([A-Z]{2})\b", pergunta.upper())
    from preprocessing.ufs import NOME_PARA_UF
    if uf_match:
        uf = uf_match.group(1).strip().upper()
        uf_nome = next((k for k, v in NOME_PARA_UF.items() if v == uf), uf)
    else:
        for nome_estado in NOME_PARA_UF:
            padrao = r"\b(?:no|na|em|do|da|de|para)\s+" + re.escape(nome_estado) + r"\b"
            if re.search(padrao, pergunta.lower()):
                uf = NOME_PARA_UF[nome_estado]
                uf_nome = nome_estado
                break

    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception:
        try:
            df = pd.read_csv(csv_path, encoding="latin1")
        except Exception:
            print("[DEBUG] Falha ao ler CSV.")
            return None, uf_nome

    df.columns = [c.strip().lower() for c in df.columns]
    col_uf = "estado"
    col_cidade = "municipio"
    col_unidade = "unidade"

    if uf and col_uf in df.columns:
        df[col_uf] = df[col_uf].astype(str).str.strip().str.upper()
        print(f"[DEBUG] Valores únicos em estado após limpeza: {df[col_uf].unique()}")
        df = df[df[col_uf] == uf]
        print(f"[DEBUG] Linhas para {uf}: {len(df)}")
    else:
        print("[DEBUG] UF não reconhecida ou coluna 'estado' ausente.")
        return None, uf_nome

    lista_cidades = []
    lista_unidades = []

    # Fuzzy matching para palavras-chave na pergunta
    palavras_esperadas = [
        "quais", "liste", "listar", "cidade", "cidades", "unidades", "unidade",
        "municipios", "municípios", "tabela", "aps", "teleatendimento"
    ]
    if not contem_palavra_semelhante(pergunta.lower(), palavras_esperadas, cutoff=0.7):
        print("[DEBUG] Nenhuma palavra-chave encontrada na pergunta.")
        return None, uf_nome

    for _, row in df.iterrows():
        cidade = row[col_cidade] if pd.notnull(row[col_cidade]) else ""
        unidade = row[col_unidade] if pd.notnull(row[col_unidade]) else ""
        if any(t in pergunta.lower() for t in ["cidade", "cidades", "município", "municipio"]):
            if cidade:
                lista_cidades.append(str(cidade).strip())
        elif any(t in pergunta.lower() for t in ["unidade", "aps", "teleatendimento"]):
            if unidade and cidade:
                lista_unidades.append(f"{cidade.strip()}: {unidade.strip()}")
            elif unidade:
                lista_unidades.append(unidade.strip())
            elif cidade:
                lista_unidades.append(cidade.strip())

    if lista_cidades:
        print(f"[DEBUG] {len(lista_cidades)} cidades encontradas.")
        return sorted(set(lista_cidades)), uf_nome
    if lista_unidades:
        print(f"[DEBUG] {len(lista_unidades)} unidades encontradas.")
        return sorted(set(lista_unidades)), uf_nome
    print("[DEBUG] Nenhuma cidade ou unidade encontrada após filtro.")
    return None, uf_nome
