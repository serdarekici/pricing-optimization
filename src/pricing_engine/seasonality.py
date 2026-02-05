from __future__ import annotations

import pandas as pd
import numpy as np

try:
    # Optional dependency for more advanced decomposition
    from statsmodels.tsa.seasonal import STL  # type: ignore
except Exception:  # pragma: no cover
    STL = None  # type: ignore


def fit_month_of_year_index(
    sales_df: pd.DataFrame,
    qty_col: str = "qty_sold",
    date_col: str = "month",
    min_obs: int = 12,
) -> pd.DataFrame:
    """Fit a simple month-of-year seasonality index per SKU.

    Returns a long table:
        sku, month_of_year (1-12), seasonal_index, strength, method

    seasonal_index is normalized so that avg index per SKU is 1.0.
    strength is a [0,1] proxy: between-month variance / total variance.
    """
    df = sales_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["month_of_year"] = df[date_col].dt.month

    out = []
    for sku, g in df.groupby("sku"):
        g = g[[qty_col, "month_of_year"]].dropna()
        if len(g) < min_obs or g[qty_col].mean() <= 0:
            # fallback: no seasonality
            for m in range(1, 13):
                out.append((sku, m, 1.0, 0.0, "none"))
            continue

        mo_mean = g.groupby("month_of_year")[qty_col].mean()
        overall = float(g[qty_col].mean())
        idx = (mo_mean / overall).reindex(range(1, 13)).fillna(1.0).astype(float)

        # normalize so mean=1
        idx = idx / idx.mean()

        # strength proxy: variance explained by month-of-year
        total_var = float(g[qty_col].var(ddof=0)) if len(g) > 1 else 0.0
        between = float(((mo_mean - overall) ** 2).mean())
        strength = 0.0 if total_var <= 1e-12 else float(min(1.0, max(0.0, between / total_var)))

        for m, v in idx.items():
            out.append((sku, int(m), float(v), strength, "month_of_year"))
    return pd.DataFrame(out, columns=["sku", "month_of_year", "seasonal_index", "strength", "method"])


def fit_stl_index(
    sales_df: pd.DataFrame,
    qty_col: str = "qty_sold",
    date_col: str = "month",
    period: int = 12,
    min_obs: int = 24,
) -> pd.DataFrame:
    """Fit STL-based seasonality index per SKU (requires statsmodels).

    If statsmodels is not installed or not enough observations, returns empty df.
    Output: sku, timestamp(month start), seasonal_index, strength, method
    """
    if STL is None:
        return pd.DataFrame(columns=["sku", "month", "seasonal_index", "strength", "method"])

    df = sales_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(["sku", date_col])

    out = []
    for sku, g in df.groupby("sku"):
        gg = g[[date_col, qty_col]].dropna().copy()
        if len(gg) < min_obs or gg[qty_col].mean() <= 0:
            continue

        # ensure regular monthly index
        s = gg.set_index(date_col)[qty_col].asfreq("MS")
        if s.isna().mean() > 0.3:
            continue
        s = s.interpolate(limit_direction="both")

        stl = STL(s, period=period, robust=True)
        res = stl.fit()
        seasonal = res.seasonal

        # Convert additive seasonal to multiplicative-ish index by shifting
        base = float(s.mean())
        seasonal_index = (base + seasonal) / base
        seasonal_index = seasonal_index / seasonal_index.mean()

        # strength proxy: var(seasonal) / var(series)
        total_var = float(np.var(s.values)) if len(s) > 1 else 0.0
        seas_var = float(np.var(seasonal.values)) if len(seasonal) > 1 else 0.0
        strength = 0.0 if total_var <= 1e-12 else float(min(1.0, max(0.0, seas_var / total_var)))

        for t, v in seasonal_index.items():
            out.append((sku, pd.Timestamp(t), float(v), strength, "stl"))
    return pd.DataFrame(out, columns=["sku", "month", "seasonal_index", "strength", "method"])


def apply_seasonality_adjustment(
    sales_df: pd.DataFrame,
    seasonality_df: pd.DataFrame,
    qty_col: str = "qty_sold",
    date_col: str = "month",
    out_col: str = "qty_deseasonalized",
) -> pd.DataFrame:
    """Create a deseasonalized quantity column.

    If seasonality_df is month-of-year table, it uses month_of_year mapping.
    If it's STL table, it merges on exact month timestamps.
    """
    df = sales_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if "month_of_year" in seasonality_df.columns:
        df["month_of_year"] = df[date_col].dt.month
        merged = df.merge(
            seasonality_df[["sku", "month_of_year", "seasonal_index"]],
            on=["sku", "month_of_year"],
            how="left",
        )
        merged["seasonal_index"] = merged["seasonal_index"].fillna(1.0)
        merged[out_col] = merged[qty_col] / merged["seasonal_index"]
        return merged.drop(columns=["month_of_year"])
    else:
        merged = df.merge(
            seasonality_df[["sku", "month", "seasonal_index"]].rename(columns={"month": date_col}),
            on=["sku", date_col],
            how="left",
        )
        merged["seasonal_index"] = merged["seasonal_index"].fillna(1.0)
        merged[out_col] = merged[qty_col] / merged["seasonal_index"]
        return merged
