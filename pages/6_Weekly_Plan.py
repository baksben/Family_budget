# import streamlit as st
# import pandas as pd
# import json
# from pathlib import Path

# PLAN_PATH = Path("data/weekly_plan.json")
# PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)

# #==============================
# ## Helpers
# #==============================
# def load_week_df() -> pd.DataFrame:
#     if PLAN_PATH.exists():
#         data = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
#         df = pd.DataFrame(data)
#         # ensure correct columns/order (in case file is old)
#         df = df[["Day"] + COLS]
#         return df
#     return default_week_df()

# def save_week_df(df: pd.DataFrame) -> None:
#     PLAN_PATH.write_text(df.to_json(orient="records"), encoding="utf-8")



# st.set_page_config(page_title="Weekly Plan", layout="wide")

# st.title("Weekly Plan")

# DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
# COLS = ["Anna drop off", "Anna pick up", "Other plans"]

# def default_week_df() -> pd.DataFrame:
#     return pd.DataFrame(
#         {
#             "Day": DAYS,
#             "Anna drop off": [""] * len(DAYS),
#             "Anna pick up": [""] * len(DAYS),
#             "Other plans": [""] * len(DAYS),
#         }
#     )

# # Init state once
# if "weekly_plan_df" not in st.session_state:
#     st.session_state.weekly_plan_df = load_week_df()


# # Clear button
# left, right = st.columns([1, 4])
# with left:
#     if st.button("Clear plans", type="secondary", use_container_width=True):
#         st.session_state.weekly_plan_df = default_week_df()
#         save_week_df(st.session_state.weekly_plan_df)
#         st.toast("Plans cleared ✅")


# st.caption("Fill in the boxes for Monday to Friday. Everything here is text.")

# # Editable table
# edited = st.data_editor(
#     st.session_state.weekly_plan_df,
#     use_container_width=True,
#     hide_index=True,
#     disabled=["Day"],  # lock the Day column
#     column_config={
#         "Day": st.column_config.TextColumn("Day"),
#         "Anna drop off": st.column_config.TextColumn("Anna drop off", width="medium"),
#         "Anna pick up": st.column_config.TextColumn("Anna pick up", width="medium"),
#         "Other plans": st.column_config.TextColumn("Other plans", width="large"),
#     },
#     key="weekly_plan_editor",
# )

# # Save edits back to session state
# st.session_state.weekly_plan_df = edited
# save_week_df(edited)
# st.toast("Saved ✅")

import streamlit as st
import pandas as pd
from finance.db import init_db, load_weekly_plan, upsert_weekly_plan, clear_weekly_plan

init_db()

st.set_page_config(page_title="Weekly Plan", layout="wide")
st.title("Weekly Plan")

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
