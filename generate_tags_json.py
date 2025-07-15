import os
import json

DATA_DIR = "./data"
DB_DIR = "./db"
TAGS_JSON = os.path.join(DB_DIR, "tags.json")

def get_tags_and_files(data_dir):
    entries = []
    for root, _, files in os.walk(data_dir):
        rel_path = os.path.relpath(root, data_dir)
        tag = rel_path.replace("\\", "/") if rel_path != "." else ""
        for file in files:
            if file.startswith("."):
                continue
            # Filtra somente arquivos pdf, txt, csv (case insensitive)
            if not file.lower().endswith((".pdf", ".txt", ".csv")):
                continue
            file_rel_path = f"{tag}/{file}" if tag else file
            file_rel_path = file_rel_path.replace("//", "/")
            entries.append({
                "file": file_rel_path,
                "tags": [tag] if tag else []
            })
    return entries

def selecionar_arquivos(entries):
    print("\nArquivos encontrados:")
    for idx, entry in enumerate(entries):
        print(f"[{idx}] {entry['file']} (tags: {', '.join(entry['tags']) if entry['tags'] else '-'})")
    selecionados = input(
        "\nDigite os números dos arquivos a serem incluídos, separados por vírgula (ex: 0,2,5):\n> "
    )
    try:
        indices = [int(x.strip()) for x in selecionados.split(",") if x.strip().isdigit()]
    except Exception:
        print("❌ Entrada inválida!")
        return []
    entries_escolhidos = [entries[i] for i in indices if 0 <= i < len(entries)]
    return entries_escolhidos

def main():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    entries = get_tags_and_files(DATA_DIR)
    if not entries:
        print("Nenhum arquivo elegível encontrado!")
        return
    escolhidos = selecionar_arquivos(entries)
    if not escolhidos:
        print("Nenhum arquivo selecionado.")
        return
    with open(TAGS_JSON, "w", encoding="utf-8") as f:
        json.dump(escolhidos, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Gerado {TAGS_JSON} com {len(escolhidos)} arquivos/tags.")

if __name__ == "__main__":
    main()

