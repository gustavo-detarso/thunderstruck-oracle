import streamlit as st
from config.auth_manager import AuthManager

def pagina_auditoria():
    st.title("🛡️ Painel de Auditoria")

    if "role" not in st.session_state or st.session_state["role"] != "admin":
        st.warning("Acesso restrito. Apenas administradores podem visualizar esta página.")
        return

    auth = AuthManager()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔐 Aprovar usuários pendentes"):
            auth.approve_users()

    with col2:
        if st.button("📤 Exportar usuários"):
            auth.export_users()

    with col3:
        if st.button("🗑️ Excluir usuários"):
            auth.delete_users()

