import streamlit as st
import pandas as pd
import plotly.express as px

from finance.db import get_settings, load_all_lines, load_all_fx
from finance.auth import require_login

# Authentification
require_login()



# -----------------------------
# Helpers
# -----------------------------
def is_moscow_category(cat: str) -> bool:
    return "moscow" in (cat or "").strip().lower()


def apply_fx_to_lines(lines: pd.DataFrame) -> pd.DataFrame:
    """
    Add amount_eur column:
      - If category contains 'moscow' => treat amount as RUB and convert using month FX
      - Else treat amount as already EUR
    If FX missing for a Moscow line, convert to 0.0 EUR (and we warn in UI).
    """
    if lines is None or lines.empty:
        return pd.DataFrame(columns=list(lines.columns) + ["amount_eur"]) if lines is not None else pd.DataFrame()

    fx = load_all_fx()
    fx_map = {}
    if fx is not None and not fx.empty:
        # Expect fx columns: month, rub_to_eur (or second column storing the rate)
        if "rub_to_eur" in fx.columns:
            fx_map = dict(zip(fx["month"], fx["rub_to_eur"]))
        else:
            # Fallback: assume second column is the rate
            rate_col = [c for c in fx.columns if c != "month"][0]
            fx_map = dict(zip(fx["month"], fx[rate_col]))

    df = lines.copy()

    def to_eur(row):
        amt = float(row["amount"])
        if is_moscow_category(row.get("category", "")):
            rate = float(fx_map.get(row.get("month", ""), 0.0))
            return amt * rate if rate > 0 else 0.0
        return amt

    df["amount_eur"] = df.apply(to_eur, axis=1)
    return df


def monthly_summary_eur(lines_eur: pd.DataFrame, starting_savings: float) -> pd.DataFrame:
    """
    Compute monthly totals using amount_eur.
    Uses ONLY line_type == 'expense' (the combined table) to avoid double counting.
    """
    if lines_eur.empty:
        return pd.DataFrame()

    income = (
        lines_eur[lines_eur["line_type"] == "income"]
        .groupby("month")["amount_eur"].sum()
        .rename("total_income")
    )
    expense = (
        lines_eur[lines_eur["line_type"] == "expense"]
        .groupby("month")["amount_eur"].sum()
        .rename("total_expense")
    )

    out = pd.concat([income, expense], axis=1).fillna(0.0).reset_index()
    out = out.sort_values("month")

    out["net"] = out["total_income"] - out["total_expense"]
    out["savings_start"] = starting_savings + out["net"].cumsum() - out["net"]
    out["savings_end"] = starting_savings + out["net"].cumsum()

    # Optional formatting / ordering
    out = out[["month", "total_income", "total_expense", "net", "savings_start", "savings_end"]]
    return out


def category_breakdown_eur(lines_eur: pd.DataFrame, line_type: str) -> pd.DataFrame:
    """
    Pivot monthly category totals using amount_eur.
    For expenses, pass line_type='expense' (combined) to match your totals.
    """
    df = lines_eur[lines_eur["line_type"] == line_type].copy()
    if df.empty:
        return pd.DataFrame()

    wide = (
        df.pivot_table(
            index="month",
            columns="category",
            values="amount_eur",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    return wide


# -----------------------------
# UI
# -----------------------------
st.title("📊 Dashboard")

settings = get_settings()
starting_savings = float(settings.get("starting_savings", "0"))

lines = load_all_lines()
if lines is None or lines.empty:
    st.info("No data yet. Go to **Add Month** and enter your first month.")
    st.stop()

# Convert to EUR the same way as Add Month
lines_eur = apply_fx_to_lines(lines)

# Warn if any Moscow lines exist but FX missing for that month
if not lines.empty:
    fx = load_all_fx()
    fx_months = set(fx["month"].tolist()) if fx is not None and not fx.empty and "month" in fx.columns else set()

    moscow_months_income = lines[
        (lines["line_type"] == "income")
        & (lines["category"].astype(str).str.lower().str.contains("moscow", na=False))
        & (lines["amount"] > 0)
    ]["month"].unique().tolist()

    moscow_months_expense = lines[
        (lines["line_type"] == "expense")
        & (lines["category"].astype(str).str.lower().str.contains("moscow", na=False))
        & (lines["amount"] > 0)
    ]["month"].unique().tolist()

    moscow_months = sorted(set(moscow_months_income + moscow_months_expense))
    missing = [m for m in moscow_months if m not in fx_months]

    if missing:
        st.warning(
            "Missing RUB→EUR rate for months: "
            + ", ".join(missing)
            + ". Add it in **Add Month** to get correct totals."
        )

summary = monthly_summary_eur(lines_eur, starting_savings)
if summary.empty:
    st.info("No data yet. Go to **Add Month** and enter your first month.")
    st.stop()

# Summary table
st.subheader("Monthly summary (EUR)")
st.dataframe(summary, use_container_width=True)

# Savings line
st.subheader("Savings over time")
fig = px.line(summary, x="month", y="savings_end", markers=True)
st.plotly_chart(fig, use_container_width=True)

# Income/Expense bars
c1, c2 = st.columns(2)
with c1:
    st.subheader("Income vs Expense")
    melt = summary.melt(
        id_vars=["month"],
        value_vars=["total_income", "total_expense"],
        var_name="type",
        value_name="amount",
    )
    fig2 = px.bar(melt, x="month", y="amount", color="type", barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.subheader("Net cashflow")
    fig3 = px.bar(summary, x="month", y="net")
    st.plotly_chart(fig3, use_container_width=True)

# Category breakdown
st.subheader("Category breakdown (EUR)")
tab1, tab2 = st.tabs(["Expenses", "Income"])

with tab1:
    # IMPORTANT: use "expense" (combined) so it matches your totals
    wide_exp = category_breakdown_eur(lines_eur, "expense")
    if wide_exp.empty:
        st.info("No expenses yet.")
    else:
        long_exp = wide_exp.melt(id_vars=["month"], var_name="category", value_name="amount")
        long_exp = long_exp[long_exp["amount"] > 0]
        fig4 = px.bar(long_exp, x="month", y="amount", color="category", barmode="stack")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(wide_exp, use_container_width=True)

with tab2:
    wide_inc = category_breakdown_eur(lines_eur, "income")
    if wide_inc.empty:
        st.info("No income yet.")
    else:
        long_inc = wide_inc.melt(id_vars=["month"], var_name="category", value_name="amount")
        long_inc = long_inc[long_inc["amount"] > 0]
        fig5 = px.bar(long_inc, x="month", y="amount", color="category", barmode="stack")
        st.plotly_chart(fig5, use_container_width=True)
        st.dataframe(wide_inc, use_container_width=True)
