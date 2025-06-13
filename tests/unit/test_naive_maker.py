"""
unit tests for naive market making strategy
"""

from decimal import Decimal

from strategy.naive_maker import quote_prices


def test_quote_prices_zero_spread():
    """test quoting with zero spread"""
    mid_price = Decimal("100.0")
    best_bid = Decimal("99.0")
    best_ask = Decimal("101.0")
    spread = Decimal("0.0")
    bid_price, ask_price, bid_size, ask_size = quote_prices(
        mid_price, best_bid, best_ask, spread
    )
    assert bid_price == mid_price
    assert ask_price == mid_price
    assert bid_size > 0
    assert ask_size > 0


def test_quote_prices_positive_spread():
    """test quoting with positive spread"""
    mid_price = Decimal("100.0")
    best_bid = Decimal("99.0")
    best_ask = Decimal("101.0")
    spread = Decimal("1.0")
    bid_price, ask_price, bid_size, ask_size = quote_prices(
        mid_price, best_bid, best_ask, spread
    )
    assert bid_price < mid_price
    assert ask_price > mid_price
    assert bid_size > 0
    assert ask_size > 0


def test_quote_prices_negative_mid():
    """test quoting with negative mid price"""
    mid_price = Decimal("-100.0")
    best_bid = Decimal("-101.0")
    best_ask = Decimal("-99.0")
    spread = Decimal("1.0")
    bid_price, ask_price, bid_size, ask_size = quote_prices(
        mid_price, best_bid, best_ask, spread
    )
    assert bid_price < mid_price
    assert ask_price > mid_price
    assert bid_size > 0
    assert ask_size > 0
