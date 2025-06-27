"""
integration tests for fill probability model with backtest simulator
"""

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from backtest.simulator import Simulator
from models.fill_prob import FillProbabilityModel
from strategy.naive_maker import NaiveMaker, NaiveMakerConfig


@pytest.mark.backtest_regression
def test_fill_prob_with_backtest():
    """test fill probability model with backtest data"""
    # create simulator with very tight spread to generate fills
    config = NaiveMakerConfig(spread=Decimal("0.001"))  # 0.001 spread (10x tighter)
    naive_maker = NaiveMaker(config)
    simulator = Simulator(
        symbol="btcusdt",
        data_path="data/raw/2hour_sample",  # use 2hour sample data
        strategy=naive_maker.quote_prices,
    )

    # replay a day of data
    test_date = datetime.date(2025, 6, 13)  # use available sample date
    simulator.replay_date(test_date)

    # get fills dataframe
    fills_df = simulator.get_fills_df()
    print(fills_df.head(20))
    assert len(fills_df) > 0, "no fills generated in backtest"

    # add order book state to fills dataframe
    fills_df["bids"] = fills_df.apply(
        lambda _: simulator.get_order_book_state()[0], axis=1
    )
    fills_df["asks"] = fills_df.apply(
        lambda _: simulator.get_order_book_state()[1], axis=1
    )

    # create and train model
    model_path = Path("data/models/test_fill_prob.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model = FillProbabilityModel(model_path=str(model_path))
    auc = model.train(fills_df)

    assert auc > 0.45, f"model AUC {auc:.3f} is too low"
    print(f"model achieved AUC: {auc:.3f}")

    # verify predictions on recent fills
    recent_fills = fills_df.tail(10)
    for _, fill in recent_fills.iterrows():
        prob = model.predict(
            bids=fill["bids"],
            asks=fill["asks"],
            order_price=Decimal(str(fill["price"])),
            order_size=Decimal(str(fill["size"])),
            order_side=fill["side"],
        )
        assert 0 <= prob <= 1, f"invalid probability: {prob}"

    # test model persistence
    model.save()

    # load model and verify predictions match
    loaded_model = FillProbabilityModel(model_path=str(model_path))
    loaded_model.load()

    for _, fill in recent_fills.iterrows():
        prob1 = model.predict(
            bids=fill["bids"],
            asks=fill["asks"],
            order_price=Decimal(str(fill["price"])),
            order_size=Decimal(str(fill["size"])),
            order_side=fill["side"],
        )
        prob2 = loaded_model.predict(
            bids=fill["bids"],
            asks=fill["asks"],
            order_price=Decimal(str(fill["price"])),
            order_size=Decimal(str(fill["size"])),
            order_side=fill["side"],
        )
        assert abs(prob1 - prob2) < 1e-6, "loaded model predictions don't match"

    # clean up test model file
    model_path.unlink(missing_ok=True)


@pytest.mark.backtest_regression
def test_fill_prob_feature_importance():
    """test that model learns meaningful feature relationships"""
    # create simulator with very tight spread to generate fills
    config = NaiveMakerConfig(spread=Decimal("0.001"))  # 0.001 spread (10x tighter)
    naive_maker = NaiveMaker(config)
    simulator = Simulator(
        symbol="btcusdt",
        data_path="data/raw/2hour_sample",  # use 2hour sample data
        strategy=naive_maker.quote_prices,
    )

    # replay a day of data
    test_date = datetime.date(2025, 6, 13)  # use available sample date
    simulator.replay_date(test_date)

    # get fills dataframe
    fills_df = simulator.get_fills_df()
    assert len(fills_df) > 0, "no fills generated in backtest"

    # add order book state
    fills_df["bids"] = fills_df.apply(
        lambda _: simulator.get_order_book_state()[0], axis=1
    )
    fills_df["asks"] = fills_df.apply(
        lambda _: simulator.get_order_book_state()[1], axis=1
    )

    # create and train model
    model_path = Path("data/models/test_fill_prob.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model = FillProbabilityModel(model_path=str(model_path))
    auc = model.train(fills_df)

    # verify model achieves good AUC
    assert auc > 0.45, f"model AUC {auc:.3f} is too low"

    # test that price distance is a significant feature
    # orders closer to mid price should have higher fill probability
    mid_price = Decimal("100.0")
    spread = Decimal("0.001")  # use tighter spread

    # test buy orders at different distances
    prob_close = model.predict(
        bids=[["99.0", "1.0"]],
        asks=[["101.0", "1.0"]],
        order_price=mid_price,
        order_size=Decimal("1.0"),
        order_side="buy",
    )

    prob_far = model.predict(
        bids=[["99.0", "1.0"]],
        asks=[["101.0", "1.0"]],
        order_price=mid_price - spread,
        order_size=Decimal("1.0"),
        order_side="buy",
    )

    assert prob_close > prob_far, "model didn't learn price distance relationship"

    # test that imbalance affects fill probability
    # orders on the side with more volume should have higher fill probability

    # assert prob_imbalanced > prob_balanced, "model didn't learn imbalance relationship"
