import streamlit as st
from rag.rag_manager import RAGManager
import pandas as pd

class ChatManager:
    def __init__(self):
        self.rag = RAGManager()

    def run_chat_interface(self):
        st.title("🧠 Oráculo MPS - Perguntas")

        pergunta = st.text_area("Digite sua pergunta:", height=100)
        if st.button("Enviar"):
            with st.spinner("Buscando resposta..."):
                resposta, fontes, score = self.rag.responder_pergunta(pergunta, return_score=True)

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

