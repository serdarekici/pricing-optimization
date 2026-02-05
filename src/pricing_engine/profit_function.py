from __future__ import annotations

from .demand_model import demand_power_law


def profit(price: float, unit_cost: float, a: float, b: float) -> float:
    """Profit(P) = (P - C) * Demand(P)"""
    d = demand_power_law(price, a, b)
    return float((price - unit_cost) * d)
