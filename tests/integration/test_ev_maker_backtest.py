"""
integration test for ev maker backtest performance
"""

import datetime
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from backtest.simulator import Simulator
from models.fill_prob import FillProbabilityModel
from strategy.ev_maker import quote_prices as ev_quote_prices
from strategy.naive_maker import quote_prices as naive_quote_prices


def ev_strategy(mid_price, best_bid, best_ask, spread, fill_model):
    """wrapper for ev maker strategy"""
    # get current order book state
    bids = [[str(best_bid), "1.0"]]  # simplified for test
    asks = [[str(best_ask), "1.0"]]

    return ev_quote_prices(
        mid_price,
        best_bid,
        best_ask,
        bids,
        asks,
        fill_model,
        base_size=Decimal("0.001"),
        min_spread=Decimal("0.0005"),
        max_spread=Decimal("0.005"),
    )


def naive_strategy(mid_price, best_bid, best_ask, spread, fill_model):
    """wrapper for naive maker strategy"""
    return naive_quote_prices(
        mid_price,
        best_bid,
        best_ask,
        spread=Decimal("0.001"),
        aggressiveness=Decimal("0.2"),
    )


class TestEVMakerBacktest(unittest.TestCase):
    """test cases for ev maker backtest performance"""

    def setUp(self):
        """set up test fixtures"""
        self.data_path = Path("data/raw")
        self.symbol = "btcusdt"
        self.test_date = datetime.date(2025, 6, 12)  # using test data file

        # create mock fill probability model
        self.fill_model = MagicMock(spec=FillProbabilityModel)
        # mock predict to return higher probability for bids closer to mid
        self.fill_model.predict.side_effect = lambda bids, asks, price, size, side: (
            0.9
            if side == "buy"
            and abs(price - (Decimal(bids[0][0]) + Decimal(asks[0][0])) / Decimal("2"))
            < Decimal("0.001")
            else 0.1
        )

    def test_ev_vs_naive_performance(self):
        """test that ev maker outperforms naive maker"""
        # run ev maker backtest
        ev_sim = Simulator(
            self.symbol,
            str(self.data_path),
            lambda **kwargs: ev_strategy(
                kwargs["mid_price"],
                kwargs["best_bid"],
                kwargs["best_ask"],
                kwargs["spread"],
                self.fill_model,
            ),
        )
        ev_sim.replay_date(self.test_date)
        ev_pnl = ev_sim.get_pnl_summary()

        # run naive maker backtest
        naive_sim = Simulator(
            self.symbol,
            str(self.data_path),
            lambda **kwargs: naive_strategy(
                kwargs["mid_price"],
                kwargs["best_bid"],
                kwargs["best_ask"],
                kwargs["spread"],
                self.fill_model,
            ),
        )
        naive_sim.replay_date(self.test_date)
        naive_pnl = naive_sim.get_pnl_summary()

        # verify ev maker outperforms
        self.assertGreater(ev_pnl["total_pnl"], naive_pnl["total_pnl"])
        self.assertGreater(ev_pnl["sharpe_ratio"], naive_pnl["sharpe_ratio"])

        # verify reasonable performance metrics
        self.assertGreater(ev_pnl["total_pnl"], 0)
        self.assertGreater(ev_pnl["sharpe_ratio"], 0)
        self.assertLess(ev_pnl["max_drawdown"], 0.1)  # max 10% drawdown

        # print performance comparison
        print("\nperformance comparison:")
        print(f"ev maker pnl: {ev_pnl['total_pnl']:.2f}")
        print(f"naive maker pnl: {naive_pnl['total_pnl']:.2f}")
        print(f"ev maker sharpe: {ev_pnl['sharpe_ratio']:.2f}")
        print(f"naive maker sharpe: {naive_pnl['sharpe_ratio']:.2f}")


if __name__ == "__main__":
    unittest.main()
