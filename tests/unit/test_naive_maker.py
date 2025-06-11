"""
unit tests for naive fixed-spread quoting logic
"""

from decimal import Decimal

from strategy.naive_maker import quote_prices


def test_quote_prices_zero_spread():
    """test quoting with zero spread"""
    mid_price = Decimal("100.0")
    spread = Decimal("0.0")
    bid_price, ask_price = quote_prices(mid_price, spread)
    assert bid_price == mid_price
    assert ask_price == mid_price


def test_quote_prices_positive_spread():
    """test quoting with positive spread"""
    mid_price = Decimal("100.0")
    spread = Decimal("1.0")
    bid_price, ask_price = quote_prices(mid_price, spread)
    assert bid_price == Decimal("99.5")
    assert ask_price == Decimal("100.5")


def test_quote_prices_negative_mid():
    """test quoting with negative mid price"""
    mid_price = Decimal("-100.0")
    spread = Decimal("1.0")
    bid_price, ask_price = quote_prices(mid_price, spread)
    assert bid_price == Decimal("-100.5")
    assert ask_price == Decimal("-99.5")
