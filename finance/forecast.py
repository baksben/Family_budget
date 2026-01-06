import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def forecast_savings(
    monthly_df: pd.DataFrame,
    starting_savings: float,
    periods: int = 6,
    income_growth_pct: float = 0.0,
    expense_growth_pct: float = 0.0,
) -> pd.DataFrame:
    """
    Forecast future savings by forecasting net cashflow (income-expense).
    Uses ETS on net; applies scenario adjustments to income/expense totals first.
    Returns dataframe with historical + forecast rows:
    month, total_income, total_expense, net, savings_end, is_forecast, lower, upper
    """
    if monthly_df.empty:
        return pd.DataFrame()

    df = monthly_df.copy()
    df = df.sort_values("month")

    # Scenario-adjust income/expense (historical stays same; we adjust the forecast level by scaling net components)
    # We'll forecast income and expense separately if enough data, else net only.
    n = len(df)

    def _safe_ets(series: pd.Series):
        # Minimal ETS config: no seasonality unless >= 24 months
        season = 12 if len(series) >= 24 else None
        if season:
            model = ExponentialSmoothing(series, trend="add", seasonal="add", seasonal_periods=12)
        else:
            model = ExponentialSmoothing(series, trend="add", seasonal=None)
        fit = model.fit(optimized=True)
        return fit

    # Forecast income & expense if enough points; else forecast net only
    can_sep = n >= 6  # heuristic

    if can_sep:
        inc_fit = _safe_ets(df["total_income"])
        exp_fit = _safe_ets(df["total_expense"])
        inc_fc = inc_fit.forecast(periods)
        exp_fc = exp_fit.forecast(periods)

        inc_fc = inc_fc * (1.0 + income_growth_pct / 100.0)
        exp_fc = exp_fc * (1.0 + expense_growth_pct / 100.0)

        net_fc = inc_fc - exp_fc

        # uncertainty: use residual std of net (rough band)
        resid = (df["total_income"] - df["total_expense"]) - (inc_fit.fittedvalues - exp_fit.fittedvalues)
        sigma = float(np.nanstd(resid)) if len(resid) > 2 else float(np.nanstd(df["net"])) or 0.0
    else:
        net_fit = _safe_ets(df["net"])
        net_fc = net_fit.forecast(periods)
        # apply net-level scenario (approx) by scaling income and expense deltas
        net_fc = net_fc * (1.0 + (income_growth_pct - expense_growth_pct) / 100.0)

        resid = df["net"] - net_fit.fittedvalues
        sigma = float(np.nanstd(resid)) if len(resid) > 2 else float(np.nanstd(df["net"])) or 0.0

        inc_fc = pd.Series([np.nan] * periods)
        exp_fc = pd.Series([np.nan] * periods)

    # Build future months YYYY-MM
    last_month = df["month"].iloc[-1]
    y, m = map(int, last_month.split("-"))
    future_months = []
    for i in range(1, periods + 1):
        mm = m + i
        yy = y + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        future_months.append(f"{yy:04d}-{mm:02d}")

    # Compute savings forward
    savings_hist = []
    cur = float(starting_savings)
    for net in df["net"].tolist():
        cur += float(net)
        savings_hist.append(cur)

    df_out = df.copy()
    df_out["savings_end"] = savings_hist
    df_out["is_forecast"] = False
    df_out["lower"] = np.nan
    df_out["upper"] = np.nan

    # forecast savings
    savings_fc = []
    lower = []
    upper = []
    cur_fc = savings_hist[-1] if savings_hist else float(starting_savings)

    for k, netv in enumerate(net_fc.tolist()):
        cur_fc += float(netv)
        savings_fc.append(cur_fc)
        # simple band grows with sqrt(t)
        band = 1.96 * sigma * np.sqrt(k + 1)
        lower.append(cur_fc - band)
        upper.append(cur_fc + band)

    fc_df = pd.DataFrame({
        "month": future_months,
        "total_income": list(inc_fc) if can_sep else [np.nan]*periods,
        "total_expense": list(exp_fc) if can_sep else [np.nan]*periods,
        "net": list(net_fc),
        "savings_end": savings_fc,
        "is_forecast": True,
        "lower": lower,
        "upper": upper,
    })

    return pd.concat([df_out, fc_df], ignore_index=True)
