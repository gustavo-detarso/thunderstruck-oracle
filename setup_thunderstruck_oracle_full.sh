#!/bin/bash

set -e

ROOT="thunderstruck-oracle"
mkdir -p "$ROOT"/{config,db,data,logs,models}

# --- app.py ---
cat > "$ROOT/app.py" << 'EOF'
import streamlit as st
from auth_manager import AuthManager
from chat_manager import ChatManager

auth = AuthManager()
chat = ChatManager()

# Controle de login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    if auth.handle_login():
        st.session_state["logged_in"] = True
        st.rerun()  # Atualiza para esconder a tela de login
else:
    st.title("⚡ Thunderstruck Oracle")
    st.caption("Desenvolvido por Gustavo de Tarso")

    if auth.is_admin():
        with st.sidebar:
            st.header("Administração")
            auth.approve_users()
            auth.export_users()
            auth.delete_users()

    chat.run_chat_interface()
EOF

# --- auth_manager.py ---
cat > "$ROOT/auth_manager.py" << 'EOF'
import streamlit as st
import bcrypt
import sqlite3
import logging
import json

DB_FILE = "config/auth.db"

class AuthManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_db()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler("logs/app.log"),
                logging.StreamHandler()
            ]
        )

    def setup_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            approved INTEGER NOT NULL,
            role TEXT NOT NULL
        )
        """)
        self.conn.commit()

    def save_user(self, username, password_hash, approved, role):
        self.cursor.execute("""
        INSERT OR REPLACE INTO users (username, password_hash, approved, role)
        VALUES (?, ?, ?, ?)
        """, (username, password_hash, approved, role))
        self.conn.commit()

    def get_user(self, username):
        self.cursor.execute("SELECT username, password_hash, approved, role FROM users WHERE username=?", (username,))
        return self.cursor.fetchone()

    def get_pending_users(self):
        self.cursor.execute("SELECT username FROM users WHERE approved=0")
        return [row[0] for row in self.cursor.fetchall()]

    def get_all_users(self):
        self.cursor.execute("SELECT username, approved, role FROM users")
        return self.cursor.fetchall()

    def delete_user(self, username):
        self.cursor.execute("DELETE FROM users WHERE username=?", (username,))
        self.conn.commit()

    def handle_login(self):
        st.title("⚡ Thunderstruck Oracle")

        option = st.radio("Ação", ["Login", "Registrar", "Redefinir senha"])
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password") if option != "Redefinir senha" else None

        if option == "Login":
            if st.button("Entrar"):
                return self.login(username, password)
        elif option == "Registrar":
            if st.button("Registrar"):
                self.register(username, password)
        elif option == "Redefinir senha":
            self.reset_password(username)

        st.markdown(
            "<div style='text-align:center; margin-top: 2em; color: #888;'>"
            "Desenvolvido por <b>Gustavo de Tarso</b>"
            "</div>",
            unsafe_allow_html=True
        )

        return st.session_state.get("logged_in", False)

    def login(self, username, password):
        user = self.get_user(username)
        if not user:
            st.error("Usuário inválido")
            logging.warning(f"TENTATIVA LOGIN FALHOU | {username}")
        elif not bcrypt.checkpw(password.encode(), user[1].encode()):
            st.error("Senha incorreta")
            logging.warning(f"TENTATIVA LOGIN FALHOU | {username}")
        elif not user[2]:
            st.warning("Usuário pendente de aprovação.")
            logging.info(f"TENTATIVA LOGIN PENDENTE | {username}")
        else:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username
            st.session_state["role"] = user[3]
            logging.info(f"LOGIN OK | {username}")
            return True
        return False

    def register(self, username, password):
        if self.get_user(username):
            st.warning("Usuário já existe!")
            return
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.save_user(username, pw_hash, 0, "user")
        st.success("Cadastro realizado! Aguarde aprovação do administrador.")
        logging.info(f"NOVO CADASTRO | {username}")

    def reset_password(self, username):
        new_pw = st.text_input("Nova senha", type="password")
        confirm_pw = st.text_input("Confirme a nova senha", type="password")
        if st.button("Alterar senha"):
            if new_pw != confirm_pw:
                st.error("Senhas não coincidem.")
            else:
                user = self.get_user(username)
                if user:
                    pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                    self.save_user(username, pw_hash, user[2], user[3])
                    st.success("Senha alterada com sucesso!")
                    logging.info(f"RESET SENHA | {username}")
                else:
                    st.error("Usuário não encontrado.")

    def approve_users(self):
        st.subheader("Aprovar usuários pendentes")
        pending = self.get_pending_users()
        for u in pending:
            if st.button(f"Aprovar {u}"):
                user = self.get_user(u)
                self.save_user(user[0], user[1], 1, user[3])
                st.success(f"{u} aprovado!")
                logging.info(f"APROVADO | {u}")

    def export_users(self):
        st.subheader("Exportar usuários")
        users = self.get_all_users()
        export_data = [{"username": u[0], "approved": bool(u[1]), "role": u[2]} for u in users]
        st.download_button(
            "Baixar JSON",
            data=json.dumps(export_data, indent=2),
            file_name="usuarios_exportados.json",
            mime="application/json"
        )

    def delete_users(self):
        st.subheader("Excluir usuários")
        admin_user = st.session_state["current_user"]
        users = self.get_all_users()
        for u in users:
            if u[0] != admin_user:
                if st.button(f"Excluir {u[0]}"):
                    self.delete_user(u[0])
                    st.success(f"{u[0]} excluído")
                    logging.info(f"EXCLUSÃO | {u[0]}")

    def is_admin(self):
        return st.session_state.get("role") == "admin"
EOF

# --- cache_manager.py ---
cat > "$ROOT/cache_manager.py" << 'EOF'
import time
import hashlib

class CacheManager:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.cache = {}

    def _generate_key(self, query, tags):
        key_string = f"{query.lower().strip()}|{','.join(sorted(tags))}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def set(self, query, tags, response):
        key = self._generate_key(query, tags)
        self.cache[key] = {
            "response": response,
            "timestamp": time.time()
        }

    def get(self, query, tags):
        key = self._generate_key(query, tags)
        item = self.cache.get(key)
        if item:
            if time.time() - item["timestamp"] < self.ttl:
                return item["response"]
            else:
                del self.cache[key]
        return None

    def clean(self):
        now = time.time()
        keys_to_delete = [k for k, v in self.cache.items() if now - v["timestamp"] >= self.ttl]
        for k in keys_to_delete:
            del self.cache[k]
EOF

# --- chat_manager.py ---
cat > "$ROOT/chat_manager.py" << 'EOF'
import streamlit as st
import pickle
import json
import numpy as np
from llama_cpp import Llama
from web_search import busca_google
from cache_manager import CacheManager
from datetime import datetime
import os

def load_model_path():
    with open("config/model_config.json") as f:
        return "./models/" + json.load(f)["model_name"]

def remove_repetidas(text):
    linhas = []
    repetidas = set()
    for linha in text.split('\n'):
        l = linha.strip()
        if l and l in linhas:
            repetidas.add(l)
            break
        if l and l not in linhas:
            linhas.append(l)
    return '\n'.join(linhas[:10])

def resposta_repetitiva(final_text):
    tokens = final_text.lower().split()
    if not tokens:
        return False
    from collections import Counter
    c = Counter(tokens)
    mais_comum, freq = c.most_common(1)[0]
    if freq / max(1, len(tokens)) > 0.3 and freq > 10:
        return True
    if "fim" in c and c["fim"] > 10:
        return True
    return False

def log_prompt(user, prompt, query, tags, advanced):
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "prompts.log")
    data = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "query": query,
        "tags": tags,
        "advanced_mode": advanced,
        "prompt": prompt,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

class ChatManager:
    def __init__(self):
        self.llm = Llama(
            model_path=load_model_path(),
            n_ctx=4096,
            embedding=True,
            max_tokens=2000
        )
        self.index = self.load_pickle("db/faiss.index")
        self.documents = self.load_pickle("db/documents.pkl")
        self.meta = self.load_pickle("db/meta.pkl")
        self.cache = CacheManager(ttl=300)

    def load_pickle(self, path):
        with open(path, "rb") as f:
            return pickle.load(f)

    def build_prompt(self, contexto, user_prompt, system_prompt, use_advanced, user_full_prompt):
        if not isinstance(contexto, str):
            contexto = str(contexto)
        if use_advanced and user_full_prompt:
            return user_full_prompt.format(contexto=contexto)
        prompt = f"{system_prompt.strip()}\n\n"
        if user_prompt.strip():
            prompt += f"Instrução do usuário: {user_prompt.strip()}\n\n"
        prompt += f"{contexto.strip()}\n"
        return prompt

    def run_chat_interface(self):
        all_tags = sorted({t for m in self.meta for t in m["tags"]})
        selected_tags = st.multiselect("Filtrar por tags", all_tags)
        query = st.text_input("Pergunta:")

        default_system_prompt = (
            "Você é um assistente especializado em Perícia Médica Federal do Ministério da Previdência Social do Brasil. "
            "Responda usando apenas o texto dos documentos, em tom institucional, sem FAQ, sem exemplos, sem repetição, sem frases genéricas, sem auto-referência. "
            "Se faltar informação, afirme que não consta no texto. Limite-se a até 10 linhas."
        )

        use_advanced = st.checkbox("Modo avançado: editar prompt completo")
        if use_advanced:
            user_full_prompt = st.text_area(
                "Prompt completo (use {contexto} para o texto dos documentos)",
                value="Responda usando apenas o texto a seguir: {contexto}\nPergunta: " + query
            )
            system_prompt = ""
            user_prompt = ""
        else:
            user_prompt = st.text_input(
                "Instrução extra (opcional, exemplo: Explique, Resuma, Destaque, etc.):", value=""
            )
            system_prompt = default_system_prompt
            user_full_prompt = ""

        # Botão de debug para listar chunks das tags
        if selected_tags:
            if st.button("Mostrar todos os chunks das tags selecionadas (debug)"):
                for i, meta in enumerate(self.meta):
                    if set(selected_tags).issubset(set(meta["tags"])):
                        st.write(f"Chunk {i} - Arquivo: {meta['file']}")
                        st.code(self.documents[i][:350] + "...", language="markdown")
                        st.write(f"TAGS: {meta['tags']}")

        # Gera a prévia da pergunta
        if st.button("Gerar Prévia do Prompt"):
            contexto = self.get_context_for_preview(query, selected_tags)
            prompt_final = self.build_prompt(
                contexto, user_prompt, system_prompt, use_advanced, user_full_prompt
            )
            st.session_state["prompt_final"] = prompt_final
            st.session_state["contexto_for_prompt"] = contexto
            st.success("Prévia gerada! Revise/edite e clique em 'Enviar pergunta' para continuar.")

        # Exibe controles se a prévia foi gerada
        if st.session_state.get("prompt_final"):
            st.text_area(
                "Pergunta (edição final antes de enviar)",
                value=query,
                key="final_user_query"
            )
            with st.expander("Mostrar contexto utilizado (chunks)", expanded=False):
                st.text_area(
                    "Contexto utilizado",
                    value=st.session_state["contexto_for_prompt"],
                    height=200,
                    disabled=True,
                    key="contexto_expander"
                )
            with st.expander("Mostrar prompt completo (debug)", expanded=False):
                st.text_area(
                    "Prompt enviado ao modelo (debug)",
                    value=st.session_state["prompt_final"],
                    height=250,
                    disabled=False,
                    key="prompt_expander"
                )

            if st.button("Enviar pergunta"):
                user_edited_query = st.session_state.get("final_user_query", query)
                self.process_query(
                    user_edited_query,
                    selected_tags,
                    system_prompt,
                    user_prompt,
                    use_advanced,
                    user_full_prompt,
                    prompt_preview=st.session_state["prompt_final"],
                    contexto_preview=st.session_state["contexto_for_prompt"],
                )
                st.session_state["prompt_final"] = ""
                st.session_state["contexto_for_prompt"] = ""

    def get_context_for_preview(self, query, selected_tags, return_chunks=False):
        filtered_idx = [
            i for i, m in enumerate(self.meta)
            if set(selected_tags).issubset(set(m["tags"]))
        ]
        if selected_tags and not filtered_idx:
            st.warning("Nenhum documento com as tags selecionadas.")
            return "", []
        resp = self.llm.embed(query)
        if isinstance(resp, dict):
            if "data" in resp and isinstance(resp["data"], list):
                emb_list = resp["data"][0].get("embedding") or resp["data"][0].get("data")
            else:
                emb_list = resp.get("embedding") or resp.get("data")
        elif isinstance(resp, list):
            emb_list = resp
        else:
            raise RuntimeError(f"Formato inesperado de embed(): {type(resp)}")
        emb_arr = np.array(emb_list, dtype=np.float32)
        dim = self.index.d
        emb_arr = emb_arr.reshape(-1, dim)
        q_emb = emb_arr.mean(axis=0, keepdims=True)
        D, I = self.index.search(q_emb, 10)
        raw_hits = I[0]
        hits = [i for i in raw_hits if i in filtered_idx]
        if not hits:
            st.warning("Nenhum conteúdo encontrado com essas tags para sua pergunta.")
            return "", []
        contexto_chunks = [self.documents[i] for i in hits[:2]]
        for idx in hits[:2]:
            st.info(f"Chunk {idx} - TAGS: {self.meta[idx]['tags']} | Arquivo: {self.meta[idx]['file']}")
        contexto = "\n\n".join(contexto_chunks)
        if return_chunks:
            return contexto, contexto_chunks
        return contexto

    def process_query(
        self,
        query,
        selected_tags,
        system_prompt,
        user_prompt,
        use_advanced,
        user_full_prompt,
        prompt_preview=None,
        contexto_preview=None
    ):
        try:
            cached = self.cache.get(query, selected_tags)
            if cached:
                st.write("✅ Resposta em cache:")
                st.write(cached)
                return

            contexto = contexto_preview if contexto_preview is not None else self.get_context_for_preview(query, selected_tags)
            prompt_final = prompt_preview if prompt_preview is not None else self.build_prompt(
                contexto, user_prompt, system_prompt, use_advanced, user_full_prompt
            )

            user = "anonimo"
            log_prompt(user, prompt_final, query, selected_tags, use_advanced)

            resposta = self.llm(
                prompt_final,
                max_tokens=1400,
                temperature=0.3,
                stop=["</s>", "```"]
            )
            st.write("---DEBUG resposta local---")
            st.write(resposta)
            if isinstance(resposta, dict):
                final_text = resposta["choices"][0]["text"]
            else:
                final_text = str(resposta)
            final_text = remove_repetidas(final_text)

            # Se a resposta é fraca ou repetitiva, faz fallback para busca web
            resposta_vazia_ou_ruim = (
                not final_text or len(final_text.strip()) < 40
                or "não encontrei" in final_text.lower()
                or "não foi possível" in final_text.lower()
                or "responda apenas à pergunta" in final_text.lower()
                or resposta_repetitiva(final_text)
            )

            if resposta_vazia_ou_ruim:
                st.info("🔎 Buscando informações complementares no Google (fallback automático por resposta repetitiva ou vazia)...")
                contexto_web = busca_google(f"{query} Ministério da Previdência Social")
                if contexto_web:
                    prompt_web = self.build_prompt(
                        contexto_web, user_prompt, system_prompt, use_advanced, user_full_prompt
                    )
                    log_prompt(user, prompt_web, query, selected_tags, use_advanced)
                    resposta_web = self.llm(
                        prompt_web,
                        max_tokens=1400,
                        temperature=0.3,
                        stop=["</s>", "```"]
                    )
                    st.write("---DEBUG resposta web---")
                    st.write(resposta_web)
                    if isinstance(resposta_web, dict):
                        final_text_web = resposta_web["choices"][0]["text"]
                    else:
                        final_text_web = str(resposta_web)
                    final_text_web = remove_repetidas(final_text_web)
                    # Só mostra a resposta web, não a local
                    st.write(final_text_web)
                    self.cache.set(query, selected_tags, final_text_web)
                    self.cache.clean()
                    return
                else:
                    st.warning("Não foi possível encontrar informações complementares no Google.")
                    # Se falhou a busca web, mostra a local (mesmo ruim)

            # Só chega aqui se a resposta local for boa ou a web não trouxe nada
            st.write(final_text)
            self.cache.set(query, selected_tags, final_text)
            self.cache.clean()

        except Exception as e:
            st.error(f"Erro durante a geração da resposta: {e}")
            import traceback
            st.write(traceback.format_exc())


if __name__ == "__main__":
    st.set_page_config(page_title="⚡ Thunderstruck Oracle")
    st.title("⚡ Thunderstruck Oracle")
    st.caption("Desenvolvido por Gustavo de Tarso")
    cm = ChatManager()
    cm.run_chat_interface()
EOF

# --- docker-compose.yml ---
cat > "$ROOT/docker-compose.yml" << 'EOF'
services:
  app:
    build: .
    container_name: thunderstruck-oracle_app
    ports:
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
      - ./db:/app/db
      - ./models:/app/models
      - ./data:/app/data
      - ./config:/app/config
    depends_on:
      - caddy
    restart: unless-stopped
    environment:
      - SERPAPI_KEY   # <- só referência, não coloque o valor aqui!

  # Se o indexer for usar a busca web, adicione igual:
  indexer:
    build:
      context: .
    container_name: thunderstruck-oracle_indexer
    command: python indexer.py
    volumes:
      - ./data:/app/data
      - ./db:/app/db
      - ./models:/app/models
      - ./tags.json:/app/tags.json
    profiles:
      - index
    restart: unless-stopped
    environment:
      - SERPAPI_KEY

  caddy:
    image: caddy:latest
    container_name: thunderstruck-oracle_caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    restart: unless-stopped
EOF

# --- docker-compose.override.yml ---
cat > "$ROOT/docker-compose.override.yml" << 'EOF'
services:
  app:
    volumes:
      - .:/app  # Hot reload do código no desenvolvimento

  indexer:
    volumes:
      - .:/app  # Hot reload do código no desenvolvimento
EOF

# --- Dockerfile ---
cat > "$ROOT/Dockerfile" << 'EOF'
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Atualize pip, set -e para fail fast, e instale as dependências
RUN set -e && \
    apt-get update && \
    apt-get install -y build-essential sqlite3 python3-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --force-reinstall --no-cache-dir google-search-results && \
    pip list

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

# --- Caddyfile ---
cat > "$ROOT/Caddyfile" << 'EOF'
gustavodetarso.com {
    reverse_proxy app:8501
}
EOF

# --- generate_tags_json.py ---
cat > "$ROOT/generate_tags_json.py" << 'EOF'
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
EOF

# --- indexer.py ---
cat > "$ROOT/indexer.py" << 'EOF'
from index_manager import IndexManager

if __name__ == "__main__":
    indexer = IndexManager()
    indexer.run_indexer()
EOF

# --- index_manager.py ---
cat > "$ROOT/index_manager.py" << 'EOF'
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
EOF

# --- requirements.txt ---
cat > "$ROOT/requirements.txt" << 'EOF'
streamlit
bcrypt
faiss-cpu
llama-cpp-python
langchain
langchain-community
unstructured[docx,odt,excel]
pandas
pypdf
google-search-results
EOF

# --- tag_debug.py ---
cat > "$ROOT/tag_debug.py" << 'EOF'
import pickle

with open("db/meta.pkl", "rb") as f:
    meta = pickle.load(f)

tag_to_chunks = {}
for i, m in enumerate(meta):
    for t in m['tags']:
        tag_to_chunks.setdefault(t, []).append((i, m['file']))

for tag, lst in tag_to_chunks.items():
    print(f"TAG: {tag} | Total chunks: {len(lst)}")
    for idx, fname in lst:
        print(f"   - Chunk {idx}: {fname}")
    print()
EOF

# --- tags.json ---
cat > "$ROOT/tags.json" << 'EOF'
[
  {
    "file": "crm_teleatendimento/rsl2314_CFM_2022.pdf",
    "tags": [
      "crm_teleatendimento"
    ]
  },
  {
    "file": "crm_teleatendimento/rsl2325_CFM_2022.pdf",
    "tags": [
      "crm_teleatendimento"
    ]
  },
  {
    "file": "pericia_conectada/ptjnt_MPS_INSS-perícia_conectada.pdf",
    "tags": [
      "pericia_conectada"
    ]
  },
  {
    "file": "pericia_conectada/ptj2_MPS_INSS_20230912.pdf",
    "tags": [
      "pericia_conectada"
    ]
  },
  {
    "file": "pericia_conectada/ptcj9_MPS-INSS-comite_acompanhamento_pericia_conectada.pdf",
    "tags": [
      "pericia_conectada"
    ]
  }
]
EOF

# --- web_search.py ---
cat > "$ROOT/web_search.py" << 'EOF'
from serpapi import GoogleSearch
import os

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def busca_google(query, lang="pt"):
    if not SERPAPI_KEY:
        raise RuntimeError("Chave SERPAPI_KEY não encontrada nas variáveis de ambiente.")
    params = {
        "q": query,
        "hl": lang,
        "gl": "br",
        "num": 3,
        "api_key": SERPAPI_KEY,
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    snippets = []
    for res in results.get("organic_results", []):
        snippet = res.get("snippet") or res.get("title")
        link = res.get("link")
        if snippet:
            if link:
                snippets.append(f"{snippet} (Fonte: {link})")
            else:
                snippets.append(snippet)
    return "\n".join(snippets)
EOF

# --- model_config.json ---
cat > "$ROOT/config/model_config.json" << 'EOF'
{"model_name": "Meta-Llama-3-8B-Instruct-Q8_0.gguf"}
EOF

# Copiando arquivos binários e scripts com permissão de execução
install -m 755 "auth.db" "$ROOT/config/auth.db"
install -m 755 "run_app_with_log.sh" "$ROOT/run_app_with_log.sh"
install -m 755 "run_indexer_with_log.sh" "$ROOT/run_indexer_with_log.sh"
install -m 755 "backup_volumes.sh" "$ROOT/backup_volumes.sh"
install -m 755 "build_docker.sh" "$ROOT/build_docker.sh"

echo "✅ Projeto thunderstruck-oracle reconstruído com sucesso."