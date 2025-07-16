import streamlit as st
from config.auth_manager import AuthManager
from config.layout import configurar_interface, inicializar_sessao
from rag.rag_manager import RAGManager
import pandas as pd

# ========== PÁGINA PERGUNTA ==========
def pagina_pergunta():
    st.title("🧠 Oráculo MPS - Perguntas")
    rag = RAGManager()
    pergunta = st.text_area("Digite sua pergunta:", height=100)
    if st.button("Enviar"):
        with st.spinner("Buscando resposta..."):
            resposta, fontes, score = rag.responder_pergunta(pergunta, return_score=True)
            lista = None
            uf_nome = None

            # TRATA tupla (lista, estado) ou lista
            if isinstance(resposta, tuple) and isinstance(resposta[0], list):
                lista = resposta[0]
                uf_nome = resposta[1]
            elif isinstance(resposta, list):
                lista = resposta

            if lista and all(isinstance(x, str) and ':' in x for x in lista):
                municipios, unidades = [], []
                for linha in lista:
                    partes = linha.split(':', 1)
                    municipios.append(partes[0].strip())
                    unidades.append(partes[1].strip() if len(partes) > 1 else "")
                df_tabela = pd.DataFrame({"Município": municipios, "Unidade": unidades})
                titulo = f"Unidades de Teleatendimento no {uf_nome.capitalize() if uf_nome else ''}"
                st.markdown("**Resposta:**")
                st.markdown(f"### {titulo}")
                st.table(df_tabela)
            else:
                st.markdown(f"**Resposta:**\n\n{resposta}")

            st.markdown("---")
            st.markdown(f"**Fontes:** {', '.join(fontes)}")
            st.markdown(f"**Confiabilidade estimada:** {round(score * 100, 1)}%")

# ========== PÁGINA ESTATÍSTICAS ==========
def pagina_estatisticas():
    st.title("📊 Estatísticas")
    st.info("Página de estatísticas. (Cole aqui o código de estatísticas.py)")

# ========== PÁGINA HISTÓRICO ==========
def pagina_historico():
    st.title("📚 Histórico")
    st.info("Página de histórico. (Cole aqui o código de historico.py)")

# ========== PÁGINA AUDITORIA ==========
def pagina_auditoria():
    st.title("🕵️ Auditoria")
    st.info("Página de auditoria. (Cole aqui o código de auditoria.py)")

# ========== APP PRINCIPAL ==========
configurar_interface()
inicializar_sessao()
auth = AuthManager()

if not st.session_state.logged_in:
    auth.handle_login()
    st.stop()
else:
    menu_opcoes = ["Fazer pergunta"]
    if auth.is_admin():
        menu_opcoes += ["Histórico", "Estatísticas", "Auditoria"]

    menu = st.sidebar.radio("Menu", menu_opcoes)

    if menu == "Fazer pergunta":
        pagina_pergunta()
    elif menu == "Histórico" and auth.is_admin():
        pagina_historico()
    elif menu == "Estatísticas" and auth.is_admin():
        pagina_estatisticas()
    elif menu == "Auditoria" and auth.is_admin():
        pagina_auditoria()

