import streamlit as st
from finance.db import verify_user, init_db

def require_login():
    init_db()  # safe to call; creates tables if missing

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    # Optional: logout button in sidebar when logged in
    if st.session_state.get("auth_ok"):
        with st.sidebar:
            st.caption(f"Logged in as: {st.session_state.get('user_email','')}")
            if st.button("Logout"):
                st.session_state.auth_ok = False
                st.session_state.user_email = None
                st.rerun()
        return

    # Login screen
    st.title("🔐 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        if verify_user(email, password):
            st.session_state.auth_ok = True
            st.session_state.user_email = email.lower().strip()
            st.success("Logged in ✅")
            st.rerun()
        else:
            st.error("Invalid email or password")

    st.stop()
