from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .constraints import PriceConstraints
from .profit_function import profit
from .demand_model import clamp


def optimize_price(
    current_price: float,
    unit_cost: float,
    a: float,
    b: float,
    constraints: PriceConstraints,
) -> dict:
    """Optimize a single SKU price under constraints (L-BFGS-B)."""
    constraints.validate()

    lo = max(constraints.price_floor, current_price * (1.0 - constraints.max_change_pct))
    hi = min(constraints.price_ceiling, current_price * (1.0 + constraints.max_change_pct))

    if lo >= hi:
        p_star = clamp(current_price, constraints.price_floor, constraints.price_ceiling)
        cur = profit(p_star, unit_cost, a, b)
        return {
            "optimal_price": float(p_star),
            "current_profit": float(cur),
            "optimal_profit": float(cur),
            "uplift_pct": 0.0,
            "status": "bounds_invalid_fallback",
        }

    def objective(x: np.ndarray) -> float:
        p = float(x[0])
        return -profit(p, unit_cost, a, b)

    x0 = np.array([clamp(current_price, lo, hi)], dtype=float)
    res = minimize(objective, x0=x0, bounds=[(lo, hi)], method="L-BFGS-B")

    p_star = float(res.x[0])
    cur_profit = profit(float(current_price), unit_cost, a, b)
    opt_profit = profit(p_star, unit_cost, a, b)

    uplift_pct = 0.0
    if abs(cur_profit) > 1e-9:
        uplift_pct = (opt_profit - cur_profit) / abs(cur_profit) * 100.0

    return {
        "optimal_price": p_star,
        "current_profit": float(cur_profit),
        "optimal_profit": float(opt_profit),
        "uplift_pct": float(uplift_pct),
        "status": "ok" if res.success else f"opt_failed: {res.message}",
    }
