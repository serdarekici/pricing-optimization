from __future__ import annotations


def demand_power_law(price: float, a: float, b: float) -> float:
    """Demand(P) = a * P^b"""
    if price <= 0:
        return 0.0
    return float(a * (price ** b))


def clamp(value: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, value)))
