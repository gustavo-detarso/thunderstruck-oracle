import re
import os
import json
import faiss
import pickle
import numpy as np
import hashlib
from datetime import datetime
from llama_cpp import Llama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredODTLoader,
    CSVLoader,
    UnstructuredExcelLoader
)
from langchain_core.documents import Document
from chat.chat_manager import load_model_path

INDEXER_VERSION = "1.9"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

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

def split_text_fixed(text, chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", " "]
    )
    return splitter.split_text(text)

def extrair_tabelas_generico(texto, max_colunas=10, min_colunas=2):
    linhas = texto.split('\n')
    tabelas = []
    bloco = []
    padrao_linha_tabela = re.compile(r"^\s*(\d+\.|\.\s*|\|\s*|[A-Z]{2}\s*\.)")
    for linha in linhas:
        if padrao_linha_tabela.match(linha) and len(linha.split()) >= min_colunas:
            bloco.append(linha)
        else:
            if len(bloco) >= 2:
                tabelas.append(list(bloco))
            bloco = []
    if len(bloco) >= 2:
        tabelas.append(list(bloco))

    tabelas_estruturadas = []
    for tab in tabelas:
        delimitadores = [r'\s{2,}', r'\t', r'\|', r'\.']
        melhor_delim = None
        max_cols = 0
        for delim in delimitadores:
            cols = [re.split(delim, l.strip()) for l in tab]
            num_cols = max(len(c) for c in cols)
            if num_cols > max_cols:
                melhor_delim = delim
                max_cols = num_cols
        if melhor_delim:
            rows = [list(map(str.strip, re.split(melhor_delim, l.strip()))) for l in tab]
            header = None
            if any(re.search('[A-Za-z]', cel) for cel in rows[0]):
                header = rows[0]
                rows = rows[1:]
            else:
                header = [f"Coluna_{i+1}" for i in range(len(rows[0]))]
            if len(header) <= max_colunas:
                tabelas_estruturadas.append({'header': header, 'rows': rows})
    return tabelas_estruturadas

def tabela_to_chunks(tab, rel_path):
    header = tab['header']
    linhas = []
    linhas.append(" | ".join(header))
    for row in tab['rows']:
        linha_formatada = " | ".join(str(cell).strip() for cell in row)
        linhas.append(linha_formatada)
    tabela_md = "\n".join(linhas)
    chunk = f"Tabela extraída ({rel_path}):\n{tabela_md}"
    return [chunk]

class IndexManager:
    def __init__(self):
        self.model = Llama(model_path=load_model_path(), embedding=True)
        self.data_dir = "./data/"
        self.tags_file = "./db/tags.json"
        self.db_dir = "./db/"
        self.chunks = []
        self.chunk_meta = []
        self.embeddings = []
        self.tag_map = self._load_tag_map()
        self.tabelas_extraidas = []

    def _load_tag_map(self):
        with open(self.tags_file) as f:
            tag_data = json.load(f)
        return {entry["file"]: entry["tags"] for entry in tag_data}

    def _arquivo_tem_chunk_existente(self, caminho_absoluto):
        rel_path = os.path.relpath(caminho_absoluto, self.data_dir).replace("\\", "/")
        return any(meta["file"] == rel_path for meta in self.chunk_meta)

    def indexar_arquivos(self, arquivos):
        sobrescrever = False
        if any(self._arquivo_tem_chunk_existente(a) for a in arquivos):
            resposta = input("⚠️ Arquivos já foram indexados. Deseja sobrescrever os chunks existentes? (s/n): ").strip().lower()
            sobrescrever = resposta.startswith("s")

        arquivos_relativos = [
            os.path.relpath(a, self.data_dir).replace("\\", "/")
            for a in arquivos
        ]
        arquivos_com_tags = set(self.tag_map.keys())
        processados = 0
        self.tabelas_extraidas = []

        for path, rel_path in zip(arquivos, arquivos_relativos):
            if rel_path not in arquivos_com_tags:
                print(f"⚠️ Ignorado (sem tags no tags.json): {rel_path}")
                continue

            loader = self.get_loader(path)
            if not loader:
                continue

            file_docs = loader() if callable(loader) else loader.load()
            tags = self.tag_map.get(rel_path, [])

            # CSV = único chunk
            if path.endswith('.csv'):
                doc = file_docs[0]
                lines = doc.page_content.strip().splitlines()
                tabela_md = "\n".join(lines)
                chunk_text = f"Tabela extraída ({rel_path}):\n{tabela_md}"
                chunk_hash = text_hash(chunk_text)
                if not sobrescrever and any(m["chunk_hash"] == chunk_hash for m in self.chunk_meta):
                    continue
                self.chunks.append(chunk_text)
                self.chunk_meta.append({
                    "file": rel_path,
                    "fonte": rel_path,
                    "tags": tags + ["tabela_extraida"],
                    "content_start": chunk_text[:200],
                    "chunk_hash": chunk_hash,
                    "created_at": datetime.now().isoformat(),
                    "source_path": path,
                    "indexer_version": INDEXER_VERSION
                })
                processados += 1
                continue

            # Outros formatos: padrão
            for d in file_docs:
                raw_text = d.page_content

                # Tabelas genéricas
                tabelas_doc = extrair_tabelas_generico(raw_text)
                if tabelas_doc:
                    for tab in tabelas_doc:
                        tab['file'] = rel_path
                    self.tabelas_extraidas.extend(tabelas_doc)
                    for tab in tabelas_doc:
                        descritores = tabela_to_chunks(tab, rel_path)
                        for chunk_text in descritores:
                            chunk_hash = text_hash(chunk_text)
                            if not sobrescrever and any(m["chunk_hash"] == chunk_hash for m in self.chunk_meta):
                                continue
                            self.chunks.append(chunk_text)
                            self.chunk_meta.append({
                                "file": rel_path,
                                "fonte": rel_path,
                                "tags": tags + ["tabela_extraida"],
                                "content_start": chunk_text[:200],
                                "chunk_hash": chunk_hash,
                                "created_at": datetime.now().isoformat(),
                                "source_path": path,
                                "indexer_version": INDEXER_VERSION
                            })

                # Chunking padrão (texto puro)
                clean_text = clean_faq(raw_text)
                for chunk_text in split_text_fixed(clean_text):
                    chunk_hash = text_hash(chunk_text)
                    if not sobrescrever and any(m["chunk_hash"] == chunk_hash for m in self.chunk_meta):
                        continue
                    self.chunks.append(chunk_text)
                    self.chunk_meta.append({
                        "file": rel_path,
                        "fonte": rel_path,
                        "tags": tags,
                        "content_start": chunk_text[:200],
                        "chunk_hash": chunk_hash,
                        "created_at": datetime.now().isoformat(),
                        "source_path": path,
                        "indexer_version": INDEXER_VERSION
                    })
            processados += 1

        print(f"🧩 {len(self.chunks)} chunks extraídos de {processados} arquivos.")

        # Salva tabelas extraídas em json (opcional)
        if self.tabelas_extraidas:
            os.makedirs(self.db_dir, exist_ok=True)
            tabela_json_path = os.path.join(self.db_dir, "tabelas_extraidas.json")
            with open(tabela_json_path, "w", encoding="utf-8") as f:
                json.dump(self.tabelas_extraidas, f, ensure_ascii=False, indent=2)
            print(f"💾 Tabelas extraídas salvas em: {tabela_json_path}")

        self.create_embeddings()
        self.save_index()

    def get_loader(self, path):
        if path.endswith(".pdf"):
            return PyPDFLoader(path)
        elif path.endswith(".docx"):
            return UnstructuredWordDocumentLoader(path)
        elif path.endswith(".odt"):
            return UnstructuredODTLoader(path)
        elif path.endswith(".csv"):
            return CSVLoader(path)
        elif path.endswith(".xlsx") or path.endswith(".xls"):
            return UnstructuredExcelLoader(path)
        else:
            print(f"Formato não suportado: {path}")
            return None

    def create_embeddings(self):
        self.embeddings = []
        for i, chunk in enumerate(self.chunks):
            try:
                resp = self.model.embed(chunk)
                emb = None
                if isinstance(resp, dict) and "data" in resp and isinstance(resp["data"], list):
                    emb = resp["data"][0].get("embedding") or resp["data"][0].get("data")
                elif isinstance(resp, dict) and "embedding" in resp:
                    emb = resp["embedding"]
                elif isinstance(resp, list):
                    emb = resp
                if emb is None:
                    raise RuntimeError("Embedding inválido")
                arr = np.array(emb, dtype=np.float32)
                self.embeddings.append(arr)
                print(f"🔹 Chunk {i}: shape {arr.shape}, arquivo: {self.chunk_meta[i]['file']}")
            except Exception as e:
                print(f"❌ Erro ao gerar embedding do chunk {i}: {e}")
        print(f"✅ {len(self.embeddings)} embeddings gerados.")

    def save_index(self):
        if not self.embeddings:
            print("❌ Nenhum embedding para salvar.")
            return
        os.makedirs(self.db_dir, exist_ok=True)
        embeddings_np = np.vstack(self.embeddings).astype("float32")
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings_np)
        meta_info = {
            "created_at": datetime.now().isoformat(),
            "indexer_version": INDEXER_VERSION,
            "embedding_dim": dim,
            "n_chunks": len(self.chunks),
            "n_files": len(set(m["file"] for m in self.chunk_meta)),
            "files_indexed": list(set(m["file"] for m in self.chunk_meta))
        }
        with open(os.path.join(self.db_dir, "faiss.index"), "wb") as f:
            pickle.dump(index, f)
        with open(os.path.join(self.db_dir, "documents.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)
        with open(os.path.join(self.db_dir, "meta.pkl"), "wb") as f:
            pickle.dump(self.chunk_meta, f)
        with open(os.path.join(self.db_dir, "index_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_info, f, indent=2, ensure_ascii=False)
        print("💾 Índice salvo com sucesso.")

def carregar_index():
    index_path = os.path.join("./db", "faiss.index")
    documents_path = os.path.join("./db", "documents.pkl")
    meta_path = os.path.join("./db", "meta.pkl")
    index_meta_path = os.path.join("./db", "index_meta.json")

    if not all(os.path.exists(p) for p in [index_path, documents_path, meta_path, index_meta_path]):
        raise FileNotFoundError("Algum dos arquivos do índice está ausente. Execute o indexador primeiro.")

    with open(index_path, "rb") as f:
        index = pickle.load(f)
    with open(documents_path, "rb") as f:
        documents = pickle.load(f)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    with open(index_meta_path, "r", encoding="utf-8") as f:
        meta_info = json.load(f)
    emb_dim = meta_info.get("embedding_dim", 4096)

    return index, documents, meta, emb_dim

