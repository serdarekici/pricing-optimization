from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def estimate_elasticity_loglog(df: pd.DataFrame, qty_col: str = "qty_sold") -> pd.DataFrame:
    """Estimate per-SKU price elasticity via log-log regression.

    Model:
        ln(qty) = ln(a) + b * ln(price)

    Returns:
        DataFrame with columns: sku, a, b, r2, n_obs
    """
    required = {"sku", "ticket_price", qty_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = []
    for sku, g in df.groupby("sku"):
        g = g[(g["ticket_price"] > 0) & (g[qty_col] > 0)].copy()
        if len(g) < 6:
            out.append((sku, np.nan, np.nan, np.nan, len(g)))
            continue

        X = np.log(g["ticket_price"].astype(float).values).reshape(-1, 1)
        y = np.log(g[qty_col].astype(float).values)

        reg = LinearRegression()
        reg.fit(X, y)
        r2 = reg.score(X, y)

        b = float(reg.coef_[0])
        a = float(np.exp(reg.intercept_))
        out.append((sku, a, b, r2, len(g)))

    return pd.DataFrame(out, columns=["sku", "a", "b", "r2", "n_obs"])
