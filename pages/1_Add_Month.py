import streamlit as st
import pandas as pd
from finance.db import get_settings, upsert_month_lines, load_month_lines
from finance.db import get_fx_rate, upsert_fx_rate
from finance.db import init_db
init_db()



st.title("➕ Add Month (Enter totals for previous month)")

settings = get_settings()
expense_cats = [c.strip() for c in settings["expense_categories"].split(",") if c.strip()]
income_cats = [c.strip() for c in settings["income_categories"].split(",") if c.strip()]

month = st.text_input("Month to add (YYYY-MM)", value="2025-12", help="Example: 2025-11")
st.subheader("Exchange rate for this month")

existing_fx = get_fx_rate(month) if month else None

rub_to_eur = st.number_input(
    "RUB → EUR rate (EUR per 1 RUB). Example: 0.0102",
    min_value=0.0,
    value=float(existing_fx) if existing_fx is not None else 0.0,
    step=0.0001,
    format="%.6f",
    help="If you have salary_moscow in RUB for this month, this rate is required."
)


col1, col2 = st.columns(2)

existing = pd.DataFrame()
if month:
    existing = load_month_lines(month)

def make_editor_df(categories, existing_df, line_type):
    base = pd.DataFrame({"category": categories, "amount": 0.0})
    if not existing_df.empty:
        ex = existing_df[existing_df["line_type"] == line_type][["category", "amount"]]
        if not ex.empty:
            base = base.merge(ex, on="category", how="left", suffixes=("", "_old"))
            base["amount"] = base["amount_old"].fillna(base["amount"])
            base = base.drop(columns=["amount_old"])
    return base

with col1:
    st.subheader("Income")
    inc_df = make_editor_df(income_cats, existing, "income")
    inc_edit = st.data_editor(
        inc_df,
        hide_index=True,
        column_config={
            "category": st.column_config.TextColumn(disabled=True),
            "amount": st.column_config.NumberColumn(step=10.0, format="%.2f"),
        },
        use_container_width=True,
        key="inc_editor"
    )

# with col2:
#     st.subheader("Expenses")
#     exp_df = make_editor_df(expense_cats, existing, "expense")
#     exp_edit = st.data_editor(
#         exp_df,
#         hide_index=True,
#         column_config={
#             "category": st.column_config.TextColumn(disabled=True),
#             "amount": st.column_config.NumberColumn(step=10.0, format="%.2f"),
#         },
#         use_container_width=True,
#         key="exp_editor"
#     )
#     st.caption("Tip: Use negative values only for corrections/refunds (e.g., -150).")

#     neg_exp = (exp_edit["amount"] < 0).any()
#     if neg_exp:
#         st.info("You have negative expense entries. These will reduce total expenses (treated as corrections/refunds).")

with col2:
    st.subheader("Expenses")

    # Load separately from DB
    exp_tat_df = make_editor_df(expense_cats, existing, "expense_tatiana")
    exp_ben_df = make_editor_df(expense_cats, existing, "expense_ben")

    t1, t2 = st.columns(2)

    with t1:
        st.markdown("**Tatiana**")
        exp_tat_edit = st.data_editor(
            exp_tat_df,
            hide_index=True,
            column_config={
                "category": st.column_config.TextColumn(disabled=True),
                "amount": st.column_config.NumberColumn(step=10.0, format="%.2f"),
            },
            use_container_width=True,
            key="exp_tat_editor"
        )

    with t2:
        st.markdown("**Ben**")
        exp_ben_edit = st.data_editor(
            exp_ben_df,
            hide_index=True,
            column_config={
                "category": st.column_config.TextColumn(disabled=True),
                "amount": st.column_config.NumberColumn(step=10.0, format="%.2f"),
            },
            use_container_width=True,
            key="exp_ben_editor"
        )

    st.caption("Tip: Use negative values only for corrections/refunds (e.g., -150).")

    neg_exp = (exp_tat_edit["amount"] < 0).any() or (exp_ben_edit["amount"] < 0).any()
    if neg_exp:
        st.info("You have negative expense entries. These will reduce total expenses (treated as corrections/refunds).")

    # Combined expenses (for totals / later saving if needed)
    exp_edit = exp_tat_edit.copy()
    exp_edit["amount"] = exp_tat_edit["amount"].astype(float) + exp_ben_edit["amount"].astype(float)



# Raw totals
total_income_raw = float(inc_edit["amount"].sum())
total_expense_eur_raw = float(exp_edit["amount"].sum())

# def is_rub_income_category(cat: str) -> bool:
#     c = (cat or "").strip().lower()
#     return ("_moscow" in c or "moscow" in c)  # matches Tatiana_salary_moscow, Ben_salary_moscow, salary_moscow, credit moscow etc.

def is_rub_income_category(cat: str) -> bool:
    return "moscow" in (cat or "").strip().lower()


# Sum all RUB incomes (any category containing salary_moscow)
rub_mask = inc_edit["category"].apply(is_rub_income_category)
rub_mask_exp = exp_edit["category"].apply(is_rub_income_category)

moscow_rub_inc = float(inc_edit.loc[rub_mask, "amount"].sum())
moscow_rub_exp = float(exp_edit.loc[rub_mask_exp, "amount"].sum())

income_ex_moscow_eur = total_income_raw - moscow_rub_inc
expenses_ex_moscow_eur = total_expense_eur_raw - moscow_rub_exp

# Convert RUB -> EUR
moscow_eur = moscow_rub_inc * float(rub_to_eur) if rub_to_eur and rub_to_eur > 0 else 0.0
moscow_exp_eur = moscow_rub_exp * float(rub_to_eur) if rub_to_eur and rub_to_eur > 0 else 0.0


total_income_eur = income_ex_moscow_eur + moscow_eur
total_expense_eur = expenses_ex_moscow_eur + moscow_exp_eur
net_eur = total_income_eur - total_expense_eur

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total income (EUR)", f"{total_income_eur:,.2f} €")
c2.metric("Total expense (EUR)", f"{total_expense_eur:,.2f} €")
c3.metric("Net (EUR)", f"{net_eur:,.2f} €")

# Optional but useful transparency:
c4.metric("Moscow salary (EUR)", f"{moscow_eur:,.2f} €")


save = st.button("💾 Save month", type="primary", disabled=not bool(month))
if save:
    # Basic validation
    if len(month) != 7 or month[4] != "-":
        st.error("Month must be in format YYYY-MM (e.g., 2025-11).")
        st.stop()

    inc_lines = [(r["category"], float(r["amount"])) for _, r in inc_edit.iterrows()]
    exp_tat_lines = [(r["category"], float(r["amount"])) for _, r in exp_tat_edit.iterrows()]
    exp_ben_lines = [(r["category"], float(r["amount"])) for _, r in exp_ben_edit.iterrows()]
    exp_lines = [(r["category"], float(r["amount"])) for _, r in exp_edit.iterrows()]
    
    upsert_month_lines(month, "expense", exp_lines)
    upsert_month_lines(month, "expense_tatiana", exp_tat_lines)
    upsert_month_lines(month, "expense_ben", exp_ben_lines)
    upsert_month_lines(month, "income", inc_lines)

    # Save FX rate if provided
    # Only enforce if salary_moscow > 0 in the income table
    # moscow_rub = float(inc_edit.loc[inc_edit["category"] == "salary_moscow", "amount"].sum()) if "salary_moscow" in inc_edit["category"].values else 0.0
    rub_mask = inc_edit["category"].apply(is_rub_income_category)
    moscow_rub = float(inc_edit.loc[rub_mask, "amount"].sum())


    if moscow_rub > 0 and rub_to_eur <= 0:
        st.error("You entered salary_moscow (RUB) but the RUB→EUR rate is missing/zero.")
        st.stop()

    if rub_to_eur > 0:
        upsert_fx_rate(month, rub_to_eur)

    st.success(f"Saved {month}.")
    st.rerun()
