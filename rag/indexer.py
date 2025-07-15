import os
import json
from rag.index_manager import IndexManager

if __name__ == "__main__":
    TAGS_FILE = "./db/tags.json"
    DATA_DIR = "./data/"

    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        tags = json.load(f)

    arquivos = [
        os.path.join(DATA_DIR, entry["file"])
        for entry in tags
        if os.path.exists(os.path.join(DATA_DIR, entry["file"]))
    ]

    indexer = IndexManager()
    indexer.tags_file = TAGS_FILE
    indexer.indexar_arquivos(arquivos)

