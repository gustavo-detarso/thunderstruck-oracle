import streamlit as st
import bcrypt
import sqlite3
import logging
import json

DB_FILE = "config/auth.db"

class AuthManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_db()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler("logs/app.log"),
                logging.StreamHandler()
            ]
        )

    def setup_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            approved INTEGER NOT NULL,
            role TEXT NOT NULL
        )
        """)
        self.conn.commit()

    def save_user(self, username, password_hash, approved, role):
        self.cursor.execute("""
        INSERT OR REPLACE INTO users (username, password_hash, approved, role)
        VALUES (?, ?, ?, ?)
        """, (username, password_hash, approved, role))
        self.conn.commit()

    def get_user(self, username):
        self.cursor.execute("SELECT username, password_hash, approved, role FROM users WHERE username=?", (username,))
        return self.cursor.fetchone()

    def get_pending_users(self):
        self.cursor.execute("SELECT username FROM users WHERE approved=0")
        return [row[0] for row in self.cursor.fetchall()]

    def get_all_users(self):
        self.cursor.execute("SELECT username, approved, role FROM users")
        return self.cursor.fetchall()

    def delete_user(self, username):
        self.cursor.execute("DELETE FROM users WHERE username=?", (username,))
        self.conn.commit()

    def handle_login(self):
        st.title("⚡ Thunderstruck Oracle")

        option = st.radio("Ação", ["Login", "Registrar", "Redefinir senha"])
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password") if option != "Redefinir senha" else None

        if option == "Login":
            if st.button("Entrar"):
                return self.login(username, password)
        elif option == "Registrar":
            if st.button("Registrar"):
                self.register(username, password)
        elif option == "Redefinir senha":
            self.reset_password(username)

        st.markdown(
            "<div style='text-align:center; margin-top: 2em; color: #888;'>"
            "Desenvolvido por <b>Gustavo de Tarso</b>"
            "</div>",
            unsafe_allow_html=True
        )

        return st.session_state.get("logged_in", False)

    def login(self, username, password):
        user = self.get_user(username)
        if not user:
            st.error("Usuário inválido")
            logging.warning(f"TENTATIVA LOGIN FALHOU | {username}")
        elif not bcrypt.checkpw(password.encode(), user[1].encode()):
            st.error("Senha incorreta")
            logging.warning(f"TENTATIVA LOGIN FALHOU | {username}")
        elif not user[2]:
            st.warning("Usuário pendente de aprovação.")
            logging.info(f"TENTATIVA LOGIN PENDENTE | {username}")
        else:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username
            st.session_state["role"] = user[3]
            logging.info(f"LOGIN OK | {username}")
            return True
        return False

    def register(self, username, password):
        if self.get_user(username):
            st.warning("Usuário já existe!")
            return
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.save_user(username, pw_hash, 0, "user")
        st.success("Cadastro realizado! Aguarde aprovação do administrador.")
        logging.info(f"NOVO CADASTRO | {username}")

    def reset_password(self, username):
        new_pw = st.text_input("Nova senha", type="password")
        confirm_pw = st.text_input("Confirme a nova senha", type="password")
        if st.button("Alterar senha"):
            if new_pw != confirm_pw:
                st.error("Senhas não coincidem.")
            else:
                user = self.get_user(username)
                if user:
                    pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                    self.save_user(username, pw_hash, user[2], user[3])
                    st.success("Senha alterada com sucesso!")
                    logging.info(f"RESET SENHA | {username}")
                else:
                    st.error("Usuário não encontrado.")

    def approve_users(self):
        st.subheader("Aprovar usuários pendentes")
        pending = self.get_pending_users()
        for u in pending:
            if st.button(f"Aprovar {u}"):
                user = self.get_user(u)
                self.save_user(user[0], user[1], 1, user[3])
                st.success(f"{u} aprovado!")
                logging.info(f"APROVADO | {u}")

    def export_users(self):
        st.subheader("Exportar usuários")
        users = self.get_all_users()
        export_data = [{"username": u[0], "approved": bool(u[1]), "role": u[2]} for u in users]
        st.download_button(
            "Baixar JSON",
            data=json.dumps(export_data, indent=2),
            file_name="usuarios_exportados.json",
            mime="application/json"
        )

    def delete_users(self):
        st.subheader("Excluir usuários")
        admin_user = st.session_state["current_user"]
        users = self.get_all_users()
        for u in users:
            if u[0] != admin_user:
                if st.button(f"Excluir {u[0]}"):
                    self.delete_user(u[0])
                    st.success(f"{u[0]} excluído")
                    logging.info(f"EXCLUSÃO | {u[0]}")

    def is_admin(self):
        return st.session_state.get("role") == "admin"
