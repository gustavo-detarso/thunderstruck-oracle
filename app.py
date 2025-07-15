import streamlit as st
from config.auth_manager import AuthManager
from chat.interface import ChatManager as ChatUI
from config.layout import configurar_interface, inicializar_sessao
from pages.estatisticas import pagina_estatisticas as exibir_estatisticas
from pages.historico import pagina_historico as exibir_historico

configurar_interface()
inicializar_sessao()

auth = AuthManager()

if not st.session_state.logged_in:
    auth.handle_login()
else:
    menu = st.sidebar.radio(
        "Menu",
        ["Fazer pergunta", "Histórico", "Estatísticas"] + (["Admin"] if auth.is_admin() else [])
    )

    if menu == "Fazer pergunta":
        chat_ui = ChatUI()
        chat_ui.run_chat_interface()

    elif menu == "Histórico":
        exibir_historico()

    elif menu == "Estatísticas":
        exibir_estatisticas()

    elif menu == "Admin":
        st.title("👤 Administração")
        auth.approve_users()
        auth.export_users()
        auth.delete_users()

