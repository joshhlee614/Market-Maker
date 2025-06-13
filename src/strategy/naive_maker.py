"""
naive market making strategy with dynamic spread and size
"""

from decimal import Decimal
from typing import Tuple


def quote_prices(
    mid_price: Decimal,
    best_bid: Decimal,
    best_ask: Decimal,
    spread: Decimal = Decimal("0.001"),  # 0.1% default spread
    aggressiveness: Decimal = Decimal("0.2"),  # How aggressive to be (0-1)
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    quote bid and ask prices and sizes with dynamic spread

    args:
        mid_price: current mid price
        best_bid: current best bid
        best_ask: current best ask
        spread: base spread to use
        aggressiveness: how aggressive to be (0-1)

    returns:
        tuple of (bid_price, ask_price, bid_size, ask_size)
    """
    # Calculate current market spread
    market_spread = best_ask - best_bid

    # Use tighter spread when market spread is wider
    effective_spread = min(spread, market_spread * Decimal("0.5"))

    # Place orders more aggressively inside the spread
    half_spread = effective_spread * (Decimal("1") - aggressiveness) / Decimal("2")

    # Calculate prices
    bid_price = mid_price - half_spread
    ask_price = mid_price + half_spread

    # Calculate sizes based on market depth
    # Use smaller sizes when spread is tighter
    base_size = Decimal("0.001")  # 0.001 BTC base size
    bid_size = base_size
    ask_size = base_size

    return bid_price, ask_price, bid_size, ask_size
