"""
naive market making strategy with dynamic spread and size
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple, Tuple


class Quote(NamedTuple):
    """quote with price and size"""

    price: Decimal
    size: Decimal


@dataclass
class NaiveMakerConfig:
    """configuration for naive maker strategy"""

    spread: Decimal = Decimal("0.001")  # 0.1% default spread
    aggressiveness: Decimal = Decimal("0.2")  # How aggressive to be (0-1)
    base_size: Decimal = Decimal("0.001")  # 0.001 BTC base size


class NaiveMaker:
    """naive market making strategy"""

    def __init__(self, config: NaiveMakerConfig):
        """initialize naive maker with config"""
        self.config = config

    def quote_prices(
        self,
        mid_price: Decimal,
        volatility: Decimal = None,  # not used but required for interface
        bid_probability: Decimal = None,  # not used but required for interface
        ask_probability: Decimal = None,  # not used but required for interface
        inventory: Decimal = Decimal("0"),  # not used but required for interface
        best_bid: Decimal = None,
        best_ask: Decimal = None,
        bids: list = None,  # not used but required for interface
        asks: list = None,  # not used but required for interface
        fill_model=None,  # not used but required for interface
    ) -> Tuple[Quote, Quote]:
        """
        quote bid and ask prices and sizes with dynamic spread

        args:
            mid_price: current mid price
            volatility: current volatility estimate (not used)
            bid_probability: probability of bid fill (not used)
            ask_probability: probability of ask fill (not used)
            inventory: current inventory position (not used)
            best_bid: current best bid
            best_ask: current best ask
            bids: list of [price, quantity] pairs (not used)
            asks: list of [price, quantity] pairs (not used)
            fill_model: trained fill probability model (not used)

        returns:
            tuple of (bid_quote, ask_quote)
        """
        if best_bid is None or best_ask is None:
            # If no market quotes, use fixed spread around mid
            half_spread = self.config.spread / Decimal("2")
            bid_price = mid_price - half_spread
            ask_price = mid_price + half_spread
        else:
            # Calculate current market spread
            market_spread = best_ask - best_bid

            # Use tighter spread when market spread is wider
            effective_spread = min(self.config.spread, market_spread * Decimal("0.5"))

            # Place orders more aggressively inside the spread
            half_spread = (
                effective_spread
                * (Decimal("1") - self.config.aggressiveness)
                / Decimal("2")
            )

            # Calculate prices
            bid_price = mid_price - half_spread
            ask_price = mid_price + half_spread

        # Use fixed base size
        bid_size = self.config.base_size
        ask_size = self.config.base_size

        return Quote(bid_price, bid_size), Quote(ask_price, ask_size)
