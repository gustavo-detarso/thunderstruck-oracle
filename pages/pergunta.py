import streamlit as st
from datetime import datetime
from rag.rag_manager import RAGManager

def pagina_pergunta():
    st.title("🧠 Faça uma pergunta ao Oráculo")

    pergunta = st.text_input("Digite sua pergunta")
    tags = st.session_state.get("tags", [])
    temperatura = st.session_state.get("temperatura", 0.5)
    usuario = st.session_state.get("current_user", "anon")

    if st.button("Enviar"):
        rag = RAGManager()
        resposta, fontes, score = rag.responder_pergunta(
            pergunta,
            tags=tags,
            return_score=True,
            temperature=temperatura
        )

        # Registro da pergunta
        st.session_state.chat_history.append({
            "usuario": usuario,
            "pergunta": pergunta,
            "resposta": resposta,
            "tags": tags,
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "fontes": fontes
        })
        st.session_state.respostas.append((resposta, fontes, score))

    # Exibe as respostas mais recentes
    for i, (resposta, fontes, score) in enumerate(reversed(st.session_state.respostas)):
        if score < 0.5:
            st.error(f"⚠️ Resposta com confiabilidade baixa (score={score:.2f})")
        st.markdown(f"**Resposta {len(st.session_state.respostas)-i}:**")
        st.markdown(resposta)
        if fontes:
            st.markdown("**Fontes:**")
            for f in fontes:
                st.markdown(f"- `{f}`")

