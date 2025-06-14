"""
unit tests for ev maker strategy
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from models.fill_prob import FillProbabilityModel
from strategy.ev_maker import quote_prices


class TestEVMaker(unittest.TestCase):
    """test cases for ev maker strategy"""

    def setUp(self):
        """set up test fixtures"""
        self.mid_price = Decimal("50000")
        self.best_bid = Decimal("49990")
        self.best_ask = Decimal("50010")
        self.bids = [["49990", "1.0"], ["49980", "2.0"]]
        self.asks = [["50010", "1.0"], ["50020", "2.0"]]
        self.fill_model = MagicMock(spec=FillProbabilityModel)

    def test_quote_prices_min_spread(self):
        """test that quotes maintain minimum spread"""
        # mock fill model to return high probabilities
        # need to provide enough values for all price points
        self.fill_model.predict.side_effect = [
            0.8
        ] * 20  # 10 points for bid side + 10 for ask side

        bid_price, ask_price, bid_size, ask_size = quote_prices(
            self.mid_price,
            self.best_bid,
            self.best_ask,
            self.bids,
            self.asks,
            self.fill_model,
            min_spread=Decimal("0.001"),  # 0.1% min spread
        )

        # verify spread is maintained
        self.assertGreaterEqual(ask_price - bid_price, Decimal("0.001"))
        self.assertEqual(bid_size, Decimal("0.001"))
        self.assertEqual(ask_size, Decimal("0.001"))

    def test_quote_prices_ev_optimization(self):
        """test that quotes optimize expected value"""
        # mock fill model to return different probabilities for each price point
        # for 3 bid points: closest to mid gets highest prob, further gets lower
        # for 3 ask points: closest to mid gets lowest prob, further gets higher
        self.fill_model.predict.side_effect = [0.9, 0.5, 0.1, 0.1, 0.5, 0.9]

        bid_price, ask_price, bid_size, ask_size = quote_prices(
            self.mid_price,
            self.best_bid,
            self.best_ask,
            self.bids,
            self.asks,
            self.fill_model,
            min_spread=Decimal("0.0005"),
            max_spread=Decimal("0.002"),
            num_points=3,  # fewer points for faster test
        )

        # verify bid is closer to mid (higher prob)
        self.assertLess(
            abs(bid_price - self.mid_price), abs(ask_price - self.mid_price)
        )

    def test_quote_prices_size(self):
        """test that quote sizes are correct"""
        # mock fill model to return high probabilities
        # need to provide enough values for all price points
        self.fill_model.predict.side_effect = [
            0.8
        ] * 20  # 10 points for bid side + 10 for ask side

        bid_price, ask_price, bid_size, ask_size = quote_prices(
            self.mid_price,
            self.best_bid,
            self.best_ask,
            self.bids,
            self.asks,
            self.fill_model,
            base_size=Decimal("0.002"),
        )

        self.assertEqual(bid_size, Decimal("0.002"))
        self.assertEqual(ask_size, Decimal("0.002"))


if __name__ == "__main__":
    unittest.main()
