import os
import json
import faiss
import pickle
import numpy as np
from llama_cpp import Llama
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredODTLoader,
    CSVLoader,
    UnstructuredExcelLoader
)
import hashlib
from datetime import datetime
from chat_manager import load_model_path

INDEXER_VERSION = "1.4"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100

def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def clean_faq(text):
    lines = []
    for line in text.split('\n'):
        l = line.strip()
        if l.lower().startswith(('pergunta:', 'resposta:', 'q:', 'a:', 'p:', 'r:')):
            continue
        if not l and lines and not lines[-1]:
            continue
        lines.append(l)
    return ' '.join([line for line in lines if line])

def split_by_paragraph(text, min_len=200):
    # Divide em blocos de parágrafo, une parágrafos curtos para formar chunks razoáveis
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ""
    for para in paras:
        if len(current) + len(para) < min_len:
            current = (current + " " + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks

class IndexManager:
    def __init__(self):
        self.model = Llama(model_path=load_model_path(), embedding=True)
        self.data_dir = "./data/"
        self.tags_file = "./tags.json"
        self.db_dir = "./db/"
        self.chunks = []
        self.chunk_meta = []
        self.embeddings = []

    def run_indexer(self):
        self.load_tags()
        self.load_documents_and_chunks()
        self.create_embeddings()
        self.save_index()

    def load_tags(self):
        with open(self.tags_file) as f:
            self.tag_data = json.load(f)
        self.tag_map = {entry["file"]: entry["tags"] for entry in self.tag_data}

    def load_documents_and_chunks(self):
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                path = os.path.join(root, file)
                loader = self.get_loader(file, path)
                if loader:
                    file_docs = loader.load()
                    rel_path = os.path.relpath(path, self.data_dir).replace("\\", "/")
                    file_tags = self.tag_map.get(rel_path, [])
                    tags = file_tags.copy()
                    for d in file_docs:
                        clean_text = clean_faq(d.page_content)
                        # --- split by paragraph:
                        for chunk_text in split_by_paragraph(clean_text, min_len=300):
                            chunk_hash = text_hash(chunk_text)
                            self.chunks.append(chunk_text)
                            self.chunk_meta.append({
                                "file": rel_path,
                                "tags": tags,
                                "content_start": chunk_text[:200],
                                "chunk_hash": chunk_hash,
                                "created_at": datetime.now().isoformat(),
                                "source_path": path,
                                "indexer_version": INDEXER_VERSION
                            })

    def get_loader(self, file, path):
        if file.endswith(".pdf"):
            return PyPDFLoader(path)
        elif file.endswith(".docx"):
            return UnstructuredWordDocumentLoader(path)
        elif file.endswith(".odt"):
            return UnstructuredODTLoader(path)
        elif file.endswith(".csv"):
            return CSVLoader(path)
        elif file.endswith(".xlsx"):
            return UnstructuredExcelLoader(path)
        else:
            print(f"Formato não suportado: {file}")
            return None

    def create_embeddings(self):
        self.embeddings = []
        for i, chunk in enumerate(self.chunks):
            resp = self.model.embed(chunk)
            if isinstance(resp, dict) and "data" in resp and isinstance(resp["data"], list):
                emb = resp["data"][0].get("embedding") or resp["data"][0].get("data")
            elif isinstance(resp, dict) and "embedding" in resp:
                emb = resp["embedding"]
            elif isinstance(resp, list):
                if isinstance(resp[0], float):
                    emb = resp
                elif isinstance(resp[0], list):
                    emb = resp[0]
            else:
                raise RuntimeError(f"Formato inesperado de embed(): {type(resp)}")
            arr = np.array(emb, dtype=np.float32)
            self.embeddings.append(arr)
            print(f"Chunk {i}: embedding shape {arr.shape}, arquivo: {self.chunk_meta[i]['file']}")
        print(f"👉 Criados {len(self.embeddings)} embeddings para {len(self.chunks)} chunks.")

    def save_index(self):
        if not self.embeddings:
            print("❌ Nenhum embedding criado. Verifique seus arquivos em ./data e o tags.json.")
            return
        os.makedirs(self.db_dir, exist_ok=True)
        embeddings_np = np.vstack(self.embeddings).astype('float32')
        assert embeddings_np.shape[0] == len(self.chunks), \
            f"embeddings count ({embeddings_np.shape[0]}) != chunks ({len(self.chunks)})"
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings_np)
        meta_info = {
            "created_at": datetime.now().isoformat(),
            "indexer_version": INDEXER_VERSION,
            "embedding_dim": dim,
            "n_chunks": len(self.chunks),
            "n_files": len(set([m["file"] for m in self.chunk_meta])),
            "files_indexed": list(set([m["file"] for m in self.chunk_meta]))
        }
        with open(os.path.join(self.db_dir, "faiss.index"), "wb") as f:
            pickle.dump(index, f)
        with open(os.path.join(self.db_dir, "documents.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)
        with open(os.path.join(self.db_dir, "meta.pkl"), "wb") as f:
            pickle.dump(self.chunk_meta, f)
        with open(os.path.join(self.db_dir, "index_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_info, f, indent=2, ensure_ascii=False)
        print(f"✅ Indexação concluída: {len(self.chunks)} chunks processados em {meta_info['n_files']} arquivos.")
        print(f"📄 index_meta.json gerado para auditoria e rastreio.")
