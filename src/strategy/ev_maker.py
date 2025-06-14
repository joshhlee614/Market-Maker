"""
expected value market making strategy

this strategy uses a fill probability model to optimize quote distances
by maximizing expected value (fill probability * spread)
"""

from decimal import Decimal
from typing import List, Tuple

from models.fill_prob import FillProbabilityModel


def quote_prices(
    mid_price: Decimal,
    best_bid: Decimal,
    best_ask: Decimal,
    bids: List[List[str]],
    asks: List[List[str]],
    fill_model: FillProbabilityModel,
    base_size: Decimal = Decimal("0.001"),  # 0.001 BTC base size
    min_spread: Decimal = Decimal("0.0005"),  # 0.05% minimum spread
    max_spread: Decimal = Decimal("0.005"),  # 0.5% maximum spread
    num_points: int = 10,  # number of points to evaluate for each side
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    quote bid and ask prices and sizes using fill probability model

    args:
        mid_price: current mid price
        best_bid: current best bid
        best_ask: current best ask
        bids: list of [price, quantity] pairs, sorted descending
        asks: list of [price, quantity] pairs, sorted ascending
        fill_model: trained fill probability model
        base_size: base order size
        min_spread: minimum spread to maintain
        max_spread: maximum spread to consider
        num_points: number of price points to evaluate for each side

    returns:
        tuple of (bid_price, ask_price, bid_size, ask_size)
    """
    # calculate price points to evaluate for each side
    bid_spreads = [
        min_spread + (max_spread - min_spread) * i / (num_points - 1)
        for i in range(num_points)
    ]
    ask_spreads = [
        min_spread + (max_spread - min_spread) * i / (num_points - 1)
        for i in range(num_points)
    ]

    # evaluate expected value for each price point
    best_bid_ev = Decimal("-inf")
    best_ask_ev = Decimal("-inf")
    best_bid_price = mid_price - min_spread
    best_ask_price = mid_price + min_spread

    # evaluate bid prices
    for spread in bid_spreads:
        price = mid_price - spread
        fill_prob = fill_model.predict(bids, asks, price, base_size, "buy")
        # convert fill_prob to Decimal safely
        fill_prob_dec = Decimal(str(float(fill_prob)))
        ev = fill_prob_dec * spread
        if ev > best_bid_ev:
            best_bid_ev = ev
            best_bid_price = price

    # evaluate ask prices
    for spread in ask_spreads:
        price = mid_price + spread
        fill_prob = fill_model.predict(bids, asks, price, base_size, "sell")
        # convert fill_prob to Decimal safely
        fill_prob_dec = Decimal(str(float(fill_prob)))
        ev = fill_prob_dec * spread
        if ev > best_ask_ev:
            best_ask_ev = ev
            best_ask_price = price

    # ensure we maintain minimum spread
    if best_ask_price - best_bid_price < min_spread:
        mid = (best_ask_price + best_bid_price) / Decimal("2")
        best_bid_price = mid - min_spread / Decimal("2")
        best_ask_price = mid + min_spread / Decimal("2")

    return best_bid_price, best_ask_price, base_size, base_size
