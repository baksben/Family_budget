# import streamlit as st
# import plotly.express as px
# import plotly.graph_objects as go

# from finance.db import get_settings, load_all_lines
# from finance.metrics import monthly_summary
# from finance.forecast import forecast_savings

# st.title("🔮 Forecast")

# settings = get_settings()
# starting_savings = float(settings.get("starting_savings", "0"))

# lines = load_all_lines()
# summary = monthly_summary(lines, starting_savings)

# if summary.empty or len(summary) < 2:
#     st.info("Add at least 2 months to forecast.")
#     st.stop()

# c1, c2, c3 = st.columns(3)
# periods = c1.slider("Forecast months", min_value=3, max_value=24, value=6, step=1)
# income_growth = c2.slider("Income scenario (% per month approx)", -20.0, 20.0, 0.0, 0.5)
# expense_growth = c3.slider("Expense scenario (% per month approx)", -20.0, 20.0, 0.0, 0.5)

# fc = forecast_savings(
#     monthly_df=summary,
#     starting_savings=starting_savings,
#     periods=periods,
#     income_growth_pct=income_growth,
#     expense_growth_pct=expense_growth,
# )

# st.subheader("Forecast table")
# st.dataframe(fc, use_container_width=True)

# st.subheader("Savings forecast")
# hist = fc[fc["is_forecast"] == False]
# pred = fc[fc["is_forecast"] == True]

# fig = go.Figure()
# fig.add_trace(go.Scatter(x=hist["month"], y=hist["savings_end"], mode="lines+markers", name="Historical"))
# fig.add_trace(go.Scatter(x=pred["month"], y=pred["savings_end"], mode="lines+markers", name="Forecast"))

# # Uncertainty band
# fig.add_trace(go.Scatter(
#     x=list(pred["month"]) + list(pred["month"][::-1]),
#     y=list(pred["upper"]) + list(pred["lower"][::-1]),
#     fill="toself",
#     name="Approx. 95% band",
#     mode="lines",
#     line=dict(width=0),
#     showlegend=True,
# ))

# st.plotly_chart(fig, use_container_width=True)

# st.caption("Forecast uses Exponential Smoothing (ETS) on net cashflow (or income/expense if enough history) with a simple uncertainty band.")

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from finance.db import get_settings, load_all_lines, load_all_fx
from finance.forecast import forecast_savings
from finance.auth import require_login

# Authentification
require_login()



# -----------------------------
# Helpers (same rule as Add Month)
# -----------------------------
def is_moscow_category(cat: str) -> bool:
    return "moscow" in (cat or "").strip().lower()


def apply_fx_to_lines(lines: pd.DataFrame) -> pd.DataFrame:
    """
    Add amount_eur:
      - categories containing 'moscow' are treated as RUB and converted using monthly FX
      - everything else is treated as EUR already
    """
    if lines is None or lines.empty:
        return pd.DataFrame(columns=list(lines.columns) + ["amount_eur"]) if lines is not None else pd.DataFrame()

    fx = load_all_fx()
    fx_map = {}
    if fx is not None and not fx.empty:
        # Your DB table is monthly_fx; the loader should return columns like: month, rub_to_eur
        if "rub_to_eur" in fx.columns:
            fx_map = dict(zip(fx["month"], fx["rub_to_eur"]))
        else:
            # fallback if column named differently
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
    Monthly totals in EUR:
      - income: line_type == 'income'
      - expenses: line_type == 'expense' ONLY (combined) to avoid double counting
    """
    if lines_eur is None or lines_eur.empty:
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

    return out[["month", "total_income", "total_expense", "net", "savings_start", "savings_end"]]


# -----------------------------
# UI
# -----------------------------
st.title("🔮 Forecast")

settings = get_settings()
starting_savings = float(settings.get("starting_savings", "0"))

lines = load_all_lines()
if lines is None or lines.empty:
    st.info("No data yet. Add some months first.")
    st.stop()

# Convert raw lines -> EUR like Add Month
lines_eur = apply_fx_to_lines(lines)

# Warn if Moscow lines exist but FX missing for that month
fx = load_all_fx()
fx_months = set(fx["month"].tolist()) if fx is not None and not fx.empty and "month" in fx.columns else set()
moscow_months = sorted(set(
    lines[
        lines["category"].astype(str).str.lower().str.contains("moscow", na=False)
        & (lines["amount"] != 0)
    ]["month"].unique().tolist()
))
missing = [m for m in moscow_months if m not in fx_months]
if missing:
    st.warning(
        "Missing RUB→EUR rate for months: "
        + ", ".join(missing)
        + ". Add it in **Add Month** to get correct totals."
    )

summary = monthly_summary_eur(lines_eur, starting_savings)

if summary.empty or len(summary) < 2:
    st.info("Add at least 2 months to forecast.")
    st.stop()

c1, c2, c3 = st.columns(3)
periods = c1.slider("Forecast months", min_value=3, max_value=24, value=6, step=1)
income_growth = c2.slider("Income scenario (% per month approx)", -20.0, 20.0, 0.0, 0.5)
expense_growth = c3.slider("Expense scenario (% per month approx)", -20.0, 20.0, 0.0, 0.5)

fc = forecast_savings(
    monthly_df=summary,
    starting_savings=starting_savings,
    periods=periods,
    income_growth_pct=income_growth,
    expense_growth_pct=expense_growth,
)

st.subheader("Forecast table")
st.dataframe(fc, use_container_width=True)

st.subheader("Savings forecast")
hist = fc[fc["is_forecast"] == False]
pred = fc[fc["is_forecast"] == True]

fig = go.Figure()
fig.add_trace(go.Scatter(x=hist["month"], y=hist["savings_end"], mode="lines+markers", name="Historical"))
fig.add_trace(go.Scatter(x=pred["month"], y=pred["savings_end"], mode="lines+markers", name="Forecast"))

# Uncertainty band
fig.add_trace(go.Scatter(
    x=list(pred["month"]) + list(pred["month"][::-1]),
    y=list(pred["upper"]) + list(pred["lower"][::-1]),
    fill="toself",
    name="Approx. 95% band",
    mode="lines",
    line=dict(width=0),
    showlegend=True,
))

st.plotly_chart(fig, use_container_width=True)

st.caption("Forecast uses Exponential Smoothing (ETS) on net cashflow with a simple uncertainty band.")
