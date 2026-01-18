import streamlit as st
from finance.db import init_db, get_or_create_settings
from finance.auth import require_login

# Streamlit page config
st.set_page_config(
    page_title="The Bakwenye's Family Finance Dashboard",
    page_icon="💶",
    layout="wide",
)

# Enforce login (after set_page_config)
require_login()


# Init DB / settings
init_db()
settings = get_or_create_settings()

st.title("💶 The Bakwenye's Family Finance Dashboard")

# Display image with rounded corners and shadow
st.markdown("""
<style>
img {
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

# Layout with two columns
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

