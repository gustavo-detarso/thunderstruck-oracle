import os
import json

DATA_DIR = "./data"
TAGS_JSON = "tags.json"

def get_tags_and_files(data_dir):
    entries = []
    for root, _, files in os.walk(data_dir):
        rel_path = os.path.relpath(root, data_dir)
        if rel_path == ".":
            continue  # ignora raiz
        tag = rel_path.replace("\\", "/")  # Para Windows/Linux
        for file in files:
            if file.startswith("."):
                continue
            # Adiciona registro do arquivo
            entries.append({
                "file": f"{tag}/{file}",
                "tags": [tag]
            })
    return entries

def main():
    entries = get_tags_and_files(DATA_DIR)
    with open(TAGS_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"✅ Gerado {TAGS_JSON} com {len(entries)} arquivos/tags.")

if __name__ == "__main__":
    main()
