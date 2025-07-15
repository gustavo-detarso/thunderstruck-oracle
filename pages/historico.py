import streamlit as st
from collections import defaultdict

def pagina_historico():
    st.title("📜 Histórico da sessão")

    historico = st.session_state.get("chat_history", [])
    if not historico:
        st.info("Nenhuma interação registrada ainda.")
        return

    for h in reversed(historico):
        st.markdown(f"**{h['usuario']} perguntou:** {h['pergunta']}")
        st.markdown(f"**Resposta:** {h['resposta']}")
        st.markdown(f"**Score:** {h['score']:.2f}")
        st.markdown(f"**Tags:** {', '.join(h['tags']) if h['tags'] else 'Nenhuma'}")
        st.markdown(f"**Fontes:** {', '.join(h['fontes']) if h['fontes'] else 'Desconhecidas'}")
        st.markdown("---")

    if st.button("📥 Exportar histórico em Markdown"):
        texto_md = "\n\n".join([
            f"### {h['usuario']}\n\n**Pergunta:** {h['pergunta']}\n\n**Resposta:** {h['resposta']}\n\n**Score:** {h['score']:.2f}"
            for h in historico
        ])
        st.download_button(
            "Baixar histórico",
            texto_md,
            file_name="historico_oraculo.md",
            mime="text/markdown"
        )

