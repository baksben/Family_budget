import streamlit as st
from finance.db import init_db, get_or_create_settings

####################################################
# Log in gatekeeper
#####################################################
import streamlit as st
from finance.db import init_db, verify_user

init_db()

def require_login():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
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

require_login()
####################################################
# Main Dashboard
####################################################
st.set_page_config(
    page_title="The Bakwenye's Family Finance Dashboard",
    page_icon="💶",
    layout="wide",
)

init_db()
settings = get_or_create_settings()

st.title("💶 The Bakwenye's Family Finance Dashboard")

st.markdown("""
<style>
img {
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)


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


cl1, cl2 = st.columns([2, 1])
with cl1:
    st.markdown(
    """
    Use the pages in the sidebar:
    - **Add Month**: enter last month totals by category (income + expenses)
    - **Dashboard**: see summaries + charts
    - **Forecast**: project savings for future months
    - **Settings**: manage categories + starting savings + passcode
    - **Weekly Meal Ideas**: generate weekly meal plans with recipes
    - **Weekly Plan**: plan weekly activities for the family
    """
    )

    with cl2:
            st.image(
        "assets/family.jpg",
        caption="The Bakwenye Family ❤️",
        width=350
    )

