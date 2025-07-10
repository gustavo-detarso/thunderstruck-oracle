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
