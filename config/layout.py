import streamlit as st

def configurar_interface():
    st.set_page_config(page_title="Oráculo MPS", layout="wide")
    st.markdown("""
        <style>
            body {
                background-color: #0e1117;
                color: #ffffff;
            }
            .stButton>button {
                background-color: #1f77b4;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

def inicializar_sessao():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "role" not in st.session_state:
        st.session_state.role = "user"
    if "tags" not in st.session_state:
        st.session_state.tags = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "respostas" not in st.session_state:
        st.session_state.respostas = []

