"""
naive fixed-spread quoting logic
"""

from decimal import Decimal


def quote_prices(mid_price: Decimal, spread: Decimal) -> tuple[Decimal, Decimal]:
    """
    quote bid and ask prices at a fixed spread around the mid price

    args:
        mid_price: current mid price
        spread: fixed spread to use

    returns:
        tuple of (bid_price, ask_price)
    """
    half_spread = spread / Decimal("2.0")
    bid_price = mid_price - half_spread
    ask_price = mid_price + half_spread
    return bid_price, ask_price
