import streamlit as st
from collections import Counter

def pagina_estatisticas():
    st.title("📊 Estatísticas da sessão")

    historico = st.session_state.get("chat_history", [])
    if not historico:
        st.info("Nenhuma interação registrada ainda.")
        return

    # Contagem por dia
    dias = [h["timestamp"][:10] for h in historico]
    contagem_dias = dict(Counter(dias))
    st.markdown("**📅 Perguntas por dia:**")
    st.json(contagem_dias)

    # Usuários ativos
    usuarios = [h["usuario"] for h in historico]
    contagem_usuarios = dict(Counter(usuarios))
    st.markdown("**👤 Usuários ativos:**")
    st.json(contagem_usuarios)

    # Score médio
    scores = [h["score"] for h in historico]
    score_medio = sum(scores) / len(scores) if scores else 0
    st.markdown(f"**📈 Score médio:** `{score_medio:.2f}`")

    # Tags mais usadas
    tags = [tag for h in historico for tag in h["tags"]]
    contagem_tags = dict(Counter(tags))
    st.markdown("**🏷️ Tags mais usadas:**")
    st.json(contagem_tags)

