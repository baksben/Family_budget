import streamlit as st
import pandas as pd

st.set_page_config(page_title="Weekly Plan", layout="wide")

st.title("Weekly Plan")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
COLS = ["Anna drop off", "Anna pick up", "Other plans"]

def default_week_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Day": DAYS,
            "Anna drop off": [""] * len(DAYS),
            "Anna pick up": [""] * len(DAYS),
            "Other plans": [""] * len(DAYS),
        }
    )

# Init state once
if "weekly_plan_df" not in st.session_state:
    st.session_state.weekly_plan_df = default_week_df()

# Clear button
left, right = st.columns([1, 4])
with left:
    if st.button("Clear plans", type="secondary", use_container_width=True):
        st.session_state.weekly_plan_df = default_week_df()
        st.toast("Plans cleared ✅")

st.caption("Fill in the boxes for Monday to Friday. Everything here is text.")

# Editable table
edited = st.data_editor(
    st.session_state.weekly_plan_df,
    use_container_width=True,
    hide_index=True,
    disabled=["Day"],  # lock the Day column
    column_config={
        "Day": st.column_config.TextColumn("Day"),
        "Anna drop off": st.column_config.TextColumn("Anna drop off", width="medium"),
        "Anna pick up": st.column_config.TextColumn("Anna pick up", width="medium"),
        "Other plans": st.column_config.TextColumn("Other plans", width="large"),
    },
    key="weekly_plan_editor",
)

# Save edits back to session state
st.session_state.weekly_plan_df = edited


