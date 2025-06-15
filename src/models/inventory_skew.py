from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class InventorySkewConfig:
    # maximum allowed inventory position (in base currency)
    max_position: float = 1.0
    # how aggressively to skew quotes based on inventory
    skew_factor: float = 0.5
    # minimum spread to maintain even at max inventory
    min_spread_bps: float = 1.0
    # optional widening as inventory grows
    spread_factor: float = 1.0
    # max price change per side between calls
    continuity_clip: float = 0.1

    def __post_init__(self):
        """validate config parameters"""
        if self.max_position <= 0:
            raise ValueError("max_position must be positive")
        if self.skew_factor <= 0:
            raise ValueError("skew_factor must be positive")
        if self.min_spread_bps <= 0:
            raise ValueError("min_spread_bps must be positive")
        if self.spread_factor <= 0:
            raise ValueError("spread_factor must be positive")
        if self.continuity_clip <= 0:
            raise ValueError("continuity_clip must be positive")


class InventorySkew:
    """computes quote adjustments based on current inventory position

    the skew logic follows a risk management approach where:
    - positive inventory -> lower bid, raise ask to encourage selling
    - negative inventory -> raise bid, lower ask to encourage buying
    - skew and spread increase as inventory moves away from 0
    """

    def __init__(self, config: InventorySkewConfig):
        self.config = config
        self._prev_bid = None
        self._prev_ask = None

    def apply_skew(self, mid_price: float, inventory: float) -> Tuple[float, float]:
        """Apply inventory-based skew to mid price to get bid/ask prices.

        Args:
            mid_price: Current mid price
            inventory: Current inventory level

        Returns:
            Tuple of (bid_price, ask_price)
        """
        # ------------------------------------------------------------------
        # 1. Normalise inventory to [-1, 1] so we never explode the quotes.
        inv = np.clip(inventory / self.config.max_position, -1.0, 1.0)

        # ------------------------------------------------------------------
        # 2. Spread calculation  (monotonic ↑ with |inv|, never < min_spread)
        min_spread = mid_price * self.config.min_spread_bps / 10_000.0
        # Use absolute value to ensure monotonic increase in both directions
        abs_inv = abs(inv)
        # Ensure spread increases with inventory magnitude
        spread = min_spread * (1.0 + abs_inv * self.config.spread_factor)
        half_spread = spread / 2.0

        # ------------------------------------------------------------------
        # 3. Centre-shift (skew)  (directional & inventory-proportional)
        #    * long  (+inv)  → shift centre DOWN  → bid↓  ask↑
        #    * short (-inv)  → shift centre UP    → bid↑  ask↓
        # Use raw inventory for directional skew
        centre_shift = -inv * self.config.skew_factor * spread

        # ------------------------------------------------------------------
        # 4. Raw bid/ask around shifted centre  (ask > bid always)
        # Ensure spread is maintained by applying half_spread symmetrically
        bid_price = mid_price + centre_shift - half_spread
        ask_price = mid_price + centre_shift + half_spread

        # ------------------------------------------------------------------
        # 5. Continuity guard  (max $0.10 move per side per call)
        if self._prev_bid is not None:
            lim = self.config.continuity_clip
            bid_price = self._prev_bid + np.clip(bid_price - self._prev_bid, -lim, lim)
            ask_price = self._prev_ask + np.clip(ask_price - self._prev_ask, -lim, lim)

        self._prev_bid, self._prev_ask = bid_price, ask_price

        return bid_price, ask_price
