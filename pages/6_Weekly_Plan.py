import streamlit as st
import pandas as pd
from finance.db import init_db, load_weekly_plan, upsert_weekly_plan, clear_weekly_plan
from finance.auth import require_login
st.set_page_config(page_title="Weekly Plan", layout="wide")
st.title("Weekly Plan")

# Authentification
require_login()

init_db()


# Load once into session state
if "weekly_plan_df" not in st.session_state:
    st.session_state.weekly_plan_df = load_weekly_plan()

left, _ = st.columns([1, 4])
with left:
    if st.button("Clear plans", type="secondary"):
        clear_weekly_plan()
        st.session_state.weekly_plan_df = load_weekly_plan()
        st.toast("Plans cleared ✅")

st.caption("Fill in the boxes for Monday to Friday. Everything here is text.")

edited = st.data_editor(
    st.session_state.weekly_plan_df,
    use_container_width=True,
    hide_index=True,
    disabled=["Day"],
    key="weekly_plan_editor",
)

# Only write to DB when something changed (prevents constant writes)
if not edited.equals(st.session_state.weekly_plan_df):
    st.session_state.weekly_plan_df = edited
    upsert_weekly_plan(edited)
    st.toast("Saved ✅")
