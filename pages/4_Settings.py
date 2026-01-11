import streamlit as st
# from finance.db import get_settings, set_setting
from finance.db import init_db, get_or_create_settings, set_setting

init_db()
settings = get_or_create_settings()


st.title("⚙️ Settings")

# settings = get_settings()

st.subheader("Starting savings")
starting = st.number_input(
    "Starting savings (used for the first month running balance)",
    value=float(settings.get("starting_savings", "0")),
    step=100.0
)
if st.button("Save starting savings"):
    set_setting("starting_savings", str(starting))
    st.success("Saved.")
    st.rerun()

st.markdown("---")
st.subheader("Categories")

expense_str = st.text_area(
    "Expense categories (comma-separated)",
    value=settings.get("expense_categories", "")
)

income_str = st.text_area(
    "Income categories (comma-separated)",
    value=settings.get("income_categories", "")
)

if st.button("Save categories"):
    set_setting("expense_categories", expense_str)
    set_setting("income_categories", income_str)
    st.success("Saved. Go to **Add Month** to see updated categories.")
    st.rerun()

st.markdown("---")
st.subheader("Simple passcode protection (for sharing)")

enabled = st.checkbox("Enable passcode", value=(settings.get("app_passcode_enabled", "0") == "1"))
passcode = st.text_input("Passcode", type="password", value=settings.get("app_passcode", ""))

if st.button("Save passcode settings"):
    set_setting("app_passcode_enabled", "1" if enabled else "0")
    set_setting("app_passcode", passcode)
    st.success("Saved.")
    st.rerun()
