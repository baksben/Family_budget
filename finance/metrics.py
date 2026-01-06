import pandas as pd
from finance.db import load_all_fx


def monthly_summary(all_lines: pd.DataFrame, starting_savings: float) -> pd.DataFrame:
    if all_lines.empty:
        return pd.DataFrame(columns=["month", "total_income", "total_expense", "net", "savings_end"])

    df = all_lines.copy()
    df["amount"] = df["amount"].astype(float)

    # Load FX rates
    fx = load_all_fx()  # month, rub_to_eur
    df = df.merge(fx, on="month", how="left")

    # Currency mapping (simple + explicit)
    # Treat amount for salary_moscow as RUB; convert to EUR using that month’s rate.
    is_rub = (df["line_type"] == "income") & (df["category"].str.lower().str.contains("salary_moscow", na=False))


    # If missing fx for any month where RUB exists, raise a helpful error later in UI
    df["amount_eur"] = df["amount"]
    df.loc[is_rub, "amount_eur"] = df.loc[is_rub, "amount"] * df.loc[is_rub, "rub_to_eur"]

    pivot = (
        df.groupby(["month", "line_type"], as_index=False)["amount_eur"].sum()
        .pivot(index="month", columns="line_type", values="amount_eur")
        .fillna(0.0)
        .reset_index()
        .sort_values("month")
    )

    if "income" not in pivot.columns:
        pivot["income"] = 0.0
    if "expense" not in pivot.columns:
        pivot["expense"] = 0.0

    pivot = pivot.rename(columns={"income": "total_income", "expense": "total_expense"})
    pivot["net"] = pivot["total_income"] - pivot["total_expense"]

    savings = []
    cur = float(starting_savings)
    for net in pivot["net"].tolist():
        cur += float(net)
        savings.append(cur)
    pivot["savings_end"] = savings

    return pivot[["month", "total_income", "total_expense", "net", "savings_end"]]


def category_breakdown(all_lines: pd.DataFrame, line_type: str) -> pd.DataFrame:
    """
    Returns wide format: month rows, categories columns
    """
    if all_lines.empty:
        return pd.DataFrame()

    df = all_lines[all_lines["line_type"] == line_type].copy()
    if df.empty:
        return pd.DataFrame()

    wide = (
        df.groupby(["month", "category"], as_index=False)["amount"].sum()
        .pivot(index="month", columns="category", values="amount")
        .fillna(0.0)
        .sort_index()
        .reset_index()
    )
    return wide
