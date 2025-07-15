import streamlit as st
import pickle
import json
import numpy as np
from llama_cpp import Llama
from chat.web_search import busca_google
from cache_manager import CacheManager
from datetime import datetime
import os
import tiktoken
import re

# Parâmetros principais para controle de tamanho do contexto e resposta
LLAMA_N_CTX = 4096  # Janela de contexto (ajuste se seu modelo suportar mais)
LLAMA_MAX_TOKENS = 1500  # Tokens máximos para resposta (ajuste conforme a necessidade/modelo)

from preprocessing.ufs import NOME_PARA_UF

def load_model_path():
    with open("config/model_config.json") as f:
        return "./models/" + json.load(f)["model_name"]

def contar_tokens(texto):
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(texto))
    except Exception:
        return len(texto.split())

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
    return freq / max(1, len(tokens)) > 0.3 and freq > 10

def log_prompt(user, prompt, query, tags, advanced):
    os.makedirs("./logs", exist_ok=True)
    with open("./logs/prompts.log", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "query": query,
            "tags": tags,
            "advanced_mode": advanced,
            "prompt": prompt,
        }, ensure_ascii=False) + "\n")

# ---------- NOVO: busca_tabela_estruturada (pré-processamento tabular) ----------
def busca_tabela_estruturada(pergunta, json_path="./db/tabelas_extraidas.json"):
    if not os.path.exists(json_path):
        return None
    uf = None
    uf_match = re.search(r"\b(?:no|na|em|do|da|de|para)\s+([A-Z]{2})\b", pergunta.upper())
    if uf_match:
        uf = uf_match.group(1)
    else:
        for nome_estado in NOME_PARA_UF:
            padrao = r"\b(?:no|na|em|do|da|de|para)\s+" + re.escape(nome_estado) + r"\b"
            if re.search(padrao, pergunta.lower()):
                uf = NOME_PARA_UF[nome_estado]
                break
    lista_cidades = []
    lista_unidades = []
    with open(json_path, "r", encoding="utf-8") as f:
        tabelas = json.load(f)
    for tab in tabelas:
        header = [h.lower() for h in tab['header']]
        for row in tab['rows']:
            linha = dict(zip(header, row))
            if uf and 'uf' in linha and linha['uf'].strip().upper() != uf:
                continue
            if any(t in pergunta.lower() for t in ["cidade", "cidades", "município", "municipio"]):
                cidade = linha.get('cidade') or linha.get('municipio') or linha.get('município')
                if cidade:
                    lista_cidades.append(cidade.strip())
            elif any(t in pergunta.lower() for t in ["unidade", "aps", "teleatendimento"]):
                unidade = linha.get('unidade', '')
                cidade = linha.get('cidade', '') or linha.get('municipio', '') or linha.get('município', '')
                if unidade and cidade:
                    lista_unidades.append(f"{cidade.strip()}: {unidade.strip()}")
                elif unidade:
                    lista_unidades.append(unidade.strip())
                elif cidade:
                    lista_unidades.append(cidade.strip())
    if lista_cidades:
        return sorted(set(lista_cidades))
    if lista_unidades:
        return sorted(set(lista_unidades))
    return None

# -----------------------------------------------------------------------------

class ChatManager:
    def __init__(self):
        self.llm = Llama(
            model_path=load_model_path(),
            n_ctx=LLAMA_N_CTX,
            embedding=True,
            max_tokens=LLAMA_MAX_TOKENS
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

        if selected_tags:
            if st.button("Mostrar todos os chunks das tags selecionadas (debug)"):
                for i, meta in enumerate(self.meta):
                    if set(selected_tags).issubset(set(meta["tags"])):
                        st.write(f"Chunk {i} - Arquivo: {meta['file']}")
                        st.code(self.documents[i][:350] + "...", language="markdown")
                        st.write(f"TAGS: {meta['tags']}")

        if st.button("Gerar Prévia do Prompt"):
            contexto = self.get_context_for_preview(query, selected_tags)
            prompt_final = self.build_prompt(contexto, user_prompt, system_prompt, use_advanced, user_full_prompt)

            n_tokens = contar_tokens(prompt_final)
            st.info(f"Prompt tem {n_tokens} tokens. Limite do modelo: {self.llm.n_ctx}")
            if n_tokens > self.llm.n_ctx:
                st.error(f"Prompt ultrapassa o limite de tokens do modelo! ({n_tokens} > {self.llm.n_ctx})")
                return

            st.session_state["prompt_final"] = prompt_final
            st.session_state["contexto_for_prompt"] = contexto
            st.success("Prévia gerada! Revise/edite e clique em 'Enviar pergunta' para continuar.")

        if st.session_state.get("prompt_final"):
            st.text_area("Pergunta (edição final antes de enviar)", value=query, key="final_user_query")
            with st.expander("Mostrar contexto utilizado (chunks)", expanded=False):
                st.text_area("Contexto utilizado", value=st.session_state["contexto_for_prompt"], height=200, disabled=True)
            with st.expander("Mostrar prompt completo (debug)", expanded=False):
                st.text_area("Prompt enviado ao modelo", value=st.session_state["prompt_final"], height=250, disabled=False)

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
        filtered_idx = [i for i, m in enumerate(self.meta) if set(selected_tags).issubset(set(m["tags"]))]
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
            st.warning("Nenhum conteúdo encontrado com as tags selecionadas para sua pergunta.")
            return "", []
        contexto_chunks = [self.documents[i] for i in hits[:4]]
        for idx in hits[:4]:
            st.info(f"Chunk {idx} - TAGS: {self.meta[idx]['tags']} | Arquivo: {self.meta[idx]['file']}")
        contexto = "\n\n".join(contexto_chunks)
        if return_chunks:
            return contexto, contexto_chunks
        return contexto

    def process_query(self, query, selected_tags, system_prompt, user_prompt, use_advanced, user_full_prompt, prompt_preview=None, contexto_preview=None):
        try:
            cached = self.cache.get(query, selected_tags)
            if cached:
                st.write("✅ Resposta em cache:")
                st.write(cached)
                return

            # Busca tabular estruturada antes de qualquer coisa
            tabular_resposta = busca_tabela_estruturada(query)
            if tabular_resposta and any(p in query.lower() for p in [
                "quais", "liste", "listar", "cidades", "unidades", "municipios", "municípios", "tabela"
            ]):
                resposta_formatada = "\n".join(tabular_resposta)
                st.success("Resposta baseada em tabela estruturada extraída dos documentos:")
                st.markdown('\n'.join([f"{i+1}. {linha}" for i, linha in enumerate(tabular_resposta)]))
                self.cache.set(query, selected_tags, resposta_formatada)
                self.cache.clean()
                return

            contexto = contexto_preview if contexto_preview is not None else self.get_context_for_preview(query, selected_tags)
            prompt_final = prompt_preview if prompt_preview is not None else self.build_prompt(contexto, user_prompt, system_prompt, use_advanced, user_full_prompt)

            n_tokens = contar_tokens(prompt_final)
            if n_tokens > self.llm.n_ctx:
                st.error(f"O prompt ({n_tokens} tokens) excede o limite do modelo ({self.llm.n_ctx}). Edite ou reduza o contexto.")
                return

            user = "anonimo"
            log_prompt(user, prompt_final, query, selected_tags, use_advanced)

            # Chamada ao modelo com max_tokens amplo
            resposta = self.llm(prompt_final, max_tokens=LLAMA_MAX_TOKENS, temperature=0.3)
            # Extrai texto e motivo de parada (finish_reason)
            if isinstance(resposta, dict):
                final_text = resposta["choices"][0]["text"]
                finish_reason = resposta["choices"][0].get("finish_reason", "")
            else:
                final_text = str(resposta)
                finish_reason = "unknown"
            final_text = remove_repetidas(final_text)
            st.code(final_text, language="markdown")
            st.info(f"Motivo de parada do modelo: **{finish_reason}**")
            if finish_reason == "length":
                st.warning("⚠️ Resposta truncada por limite de tokens. Considere aumentar LLAMA_MAX_TOKENS ou diminuir contexto.")

            resposta_fraca = (
                not final_text or len(final_text.strip()) < 40
                or "não encontrei" in final_text.lower()
                or "não foi possível" in final_text.lower()
                or "responda apenas à pergunta" in final_text.lower()
                or resposta_repetitiva(final_text)
            )

            if resposta_fraca:
                st.info("🔎 Buscando informações complementares no Google...")
                contexto_web = busca_google(f"{query} Ministério da Previdência Social")
                if contexto_web:
                    prompt_web = self.build_prompt(contexto_web, user_prompt, system_prompt, use_advanced, user_full_prompt)
                    log_prompt(user, prompt_web, query, selected_tags, use_advanced)
                    resposta_web = self.llm(prompt_web, max_tokens=LLAMA_MAX_TOKENS, temperature=0.3)
                    if isinstance(resposta_web, dict):
                        final_text_web = resposta_web["choices"][0]["text"]
                        finish_reason_web = resposta_web["choices"][0].get("finish_reason", "")
                    else:
                        final_text_web = str(resposta_web)
                        finish_reason_web = "unknown"
                    final_text_web = remove_repetidas(final_text_web)
                    st.code(final_text_web, language="markdown")
                    st.info(f"Motivo de parada do modelo (web): **{finish_reason_web}**")
                    if finish_reason_web == "length":
                        st.warning("⚠️ Resposta web truncada por limite de tokens.")
                    st.write(final_text_web)
                    self.cache.set(query, selected_tags, final_text_web)
                    self.cache.clean()
                    return
                else:
                    st.warning("Não foi possível encontrar informações no fallback web.")

            st.write(final_text)
            self.cache.set(query, selected_tags, final_text)
            self.cache.clean()

        except Exception as e:
            st.error(f"Erro durante a geração da resposta: {e}")
            import traceback
            st.code(traceback.format_exc(), language="python")

