from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceConstraints:
    """Business constraints for pricing optimization."""

    price_floor: float
    price_ceiling: float
    max_change_pct: float  # e.g., 0.25 means +/-25% allowed vs current price

    def validate(self) -> None:
        if self.price_floor <= 0:
            raise ValueError("price_floor must be > 0")
        if self.price_ceiling <= 0:
            raise ValueError("price_ceiling must be > 0")
        if self.price_floor > self.price_ceiling:
            raise ValueError("price_floor cannot exceed price_ceiling")
        if not (0.0 < self.max_change_pct <= 1.0):
            raise ValueError("max_change_pct must be in (0, 1]")
