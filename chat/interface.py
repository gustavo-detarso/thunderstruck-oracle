# chat/interface.py

import streamlit as st
from rag.rag_manager import RAGManager

class ChatManager:
    def __init__(self):
        self.rag = RAGManager()

    def run_chat_interface(self):
        st.title("🧠 Oráculo MPS - Perguntas")

        pergunta = st.text_area("Digite sua pergunta:", height=100)
        if st.button("Enviar"):
            with st.spinner("Buscando resposta..."):
                resposta, fontes, score = self.rag.responder_pergunta(pergunta, return_score=True)
                st.markdown(f"**Resposta:**\n\n{resposta}")
                st.markdown("---")
                st.markdown(f"**Fontes:** {', '.join(fontes)}")
                st.markdown(f"**Confiabilidade estimada:** {round(score * 100, 1)}%")

