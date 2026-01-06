import streamlit as st
from finance.db import init_db, get_or_create_settings

st.set_page_config(
    page_title="The Bakwenye's Family Finance Dashboard",
    page_icon="💶",
    layout="wide",
)

init_db()
settings = get_or_create_settings()

st.title("💶 The Bakwenye's Family Finance Dashboard")

if settings.get("app_passcode_enabled", "0") == "1":
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        st.info("This dashboard is protected. Enter the passcode.")
        code = st.text_input("Passcode", type="password")
        if code and code == settings.get("app_passcode", ""):
            st.session_state.auth_ok = True
            st.success("Access granted.")
            st.rerun()
        elif code:
            st.error("Wrong passcode.")
        st.stop()

st.markdown(
    """
Use the pages in the sidebar:
- **Add Month**: enter last month totals by category (income + expenses)
- **Dashboard**: see summaries + charts
- **Forecast**: project savings for future months
- **Settings**: manage categories + starting savings + passcode
"""
)
