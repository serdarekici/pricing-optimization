from __future__ import annotations

import pandas as pd

from .constraints import PriceConstraints
from .optimizer import optimize_price
from .profit_function import profit
from .demand_model import demand_power_law


def recommend_prices(
    sales_df: pd.DataFrame,
    elasticity_df: pd.DataFrame,
    ladder_df: pd.DataFrame,
    seasonality_df: pd.DataFrame | None = None,
    qty_col: str = "qty_sold",
) -> pd.DataFrame:
    """Generate price recommendations per SKU (demo)."""
    sales_df = sales_df.copy()
    sales_df["month"] = pd.to_datetime(sales_df["month"])
    current = sales_df.sort_values("month").groupby("sku").tail(1).copy()

    
    # Optional: attach a seasonality index for the most recent month to scale demand outputs back
    seasonal_current = None
    if seasonality_df is not None and len(seasonality_df) > 0:
        if "month_of_year" in seasonality_df.columns:
            seasonality_df = seasonality_df.copy()
            current["month_of_year"] = current["month"].dt.month
            seasonal_current = current[["sku", "month_of_year"]].merge(
                seasonality_df[["sku", "month_of_year", "seasonal_index", "strength"]],
                on=["sku", "month_of_year"],
                how="left",
            )
            seasonal_current = seasonal_current.set_index("sku")[["seasonal_index", "strength"]]
            current = current.drop(columns=["month_of_year"])
        else:
            seasonality_df = seasonality_df.copy()
            seasonal_current = current[["sku", "month"]].merge(
                seasonality_df.rename(columns={"month": "month"}),
                on=["sku", "month"],
                how="left",
            ).set_index("sku")[["seasonal_index", "strength"]]
    cur = current.merge(elasticity_df, on="sku", how="left").merge(ladder_df, on="price_ladder", how="left")

    out_rows = []
    for _, r in cur.iterrows():
        sku = r["sku"]
        cur_price = float(r["ticket_price"])
        cost = float(r["unit_cost"])

        a = r["a"]
        b = r["b"]
        if pd.isna(a) or pd.isna(b):
            qty = float(r.get(qty_col, 0.0))
            out_rows.append({
                "sku": sku,
                "current_price": cur_price,
                "optimal_price": cur_price,
                "expected_demand_current": qty,
                "expected_demand_optimal": qty,
                "current_profit": float((cur_price - cost) * qty),
                "optimal_profit": float((cur_price - cost) * qty),
                "uplift_pct": 0.0,
                "status": "no_elasticity_model",
                "seasonality_index": 1.0,
                "seasonality_strength": 0.0,
                "current_profit_seasonal": float((cur_price - cost) * qty),
                "optimal_profit_seasonal": float((cur_price - cost) * qty),
            })
            continue

        floor = max(cost * float(r["min_price_multiplier"]), 0.01)
        ceiling = max(cost * float(r["max_price_multiplier"]), floor * 1.01)
        max_change = float(r["max_change_pct"])

        cons = PriceConstraints(price_floor=floor, price_ceiling=ceiling, max_change_pct=max_change)
        res = optimize_price(cur_price, cost, float(a), float(b), cons)

        p_star = float(res["optimal_price"])
        d_cur = demand_power_law(cur_price, float(a), float(b))
        d_opt = demand_power_law(p_star, float(a), float(b))

        seas_idx = 1.0
        seas_strength = 0.0
        if seasonal_current is not None and sku in seasonal_current.index:
            si = seasonal_current.loc[sku].get("seasonal_index", 1.0)
            ss = seasonal_current.loc[sku].get("strength", 0.0)
            seas_idx = 1.0 if pd.isna(si) else float(si)
            seas_strength = 0.0 if pd.isna(ss) else float(ss)

        # Scale demand/profit back to the current month seasonality
        d_cur_seasonal = d_cur * seas_idx
        d_opt_seasonal = d_opt * seas_idx
        cur_profit_seasonal = (cur_price - cost) * d_cur_seasonal
        opt_profit_seasonal = (p_star - cost) * d_opt_seasonal

        out_rows.append({
            "sku": sku,
            "current_price": cur_price,
            "optimal_price": p_star,
                "expected_demand_current": d_cur_seasonal,
                "expected_demand_optimal": d_opt_seasonal,
                "seasonality_index": seas_idx,
                "seasonality_strength": seas_strength,
                "current_profit": profit(cur_price, cost, float(a), float(b)),
                "current_profit_seasonal": float(cur_profit_seasonal),
            "optimal_profit": profit(p_star, cost, float(a), float(b)),
                "optimal_profit_seasonal": float(opt_profit_seasonal),
            "uplift_pct": float(res["uplift_pct"]),
            "status": res["status"],
        })

    out = pd.DataFrame(out_rows)
    return out.sort_values("uplift_pct", ascending=False).reset_index(drop=True)
