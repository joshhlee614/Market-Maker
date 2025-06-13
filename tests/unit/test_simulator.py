"""
test module for simulator

this module contains tests for the Simulator class which:
1. verifies correct replay of parquet data
2. ensures deterministic order book state
3. tests error handling and edge cases
"""

import datetime
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pyarrow import Table, schema

from backtest.simulator import Simulator
from lob.order_book import OrderBook
from strategy.naive_maker import quote_prices


@pytest.fixture
def test_data_dir(tmp_path):
    """create temporary directory with test parquet files"""
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def sample_messages():
    """create sample market data messages"""
    return [
        {
            "event_type": "depthUpdate",
            "event_time": 1234567890000,
            "symbol": "btcusdt",
            "first_update_id": 1,
            "final_update_id": 1,
            "bids": ["100.0,1.0", "99.0,2.0"],
            "asks": ["101.0,1.0", "102.0,2.0"],
        },
        {
            "event_type": "depthUpdate",
            "event_time": 1234567890001,
            "symbol": "btcusdt",
            "first_update_id": 2,
            "final_update_id": 2,
            "bids": ["100.0,2.0", "99.0,1.0"],
            "asks": ["101.0,2.0", "102.0,1.0"],
        },
    ]


@pytest.fixture
def sample_parquet_file(test_data_dir, sample_messages):
    """create sample parquet file with test data"""
    # create schema
    sch = schema(
        [
            ("event_type", pa.string()),
            ("event_time", pa.int64()),
            ("symbol", pa.string()),
            ("first_update_id", pa.int64()),
            ("final_update_id", pa.int64()),
            ("bids", pa.list_(pa.string())),
            ("asks", pa.list_(pa.string())),
        ]
    )

    # create table
    table = Table.from_pylist(sample_messages, schema=sch)

    # write to parquet
    date = datetime.date(2024, 1, 1)
    file_path = test_data_dir / f"btcusdt_{date.strftime('%Y%m%d')}.parquet"
    pq.write_table(table, file_path)

    return file_path


def test_simulator_initialization(test_data_dir):
    """test simulator initialization"""
    simulator = Simulator(
        symbol="btcusdt", data_path=str(test_data_dir), strategy=quote_prices
    )
    assert simulator.symbol == "btcusdt"
    assert simulator.data_path == test_data_dir
    assert simulator.strategy == quote_prices


def test_simulator_custom_order_book(test_data_dir):
    """test simulator with custom order book"""
    order_book = OrderBook()
    simulator = Simulator(
        symbol="btcusdt", data_path=str(test_data_dir), strategy=quote_prices
    )
    simulator.order_book = order_book
    assert simulator.order_book == order_book


def test_replay_date(sample_parquet_file):
    """test replaying messages for a single date"""
    simulator = Simulator(
        symbol="btcusdt",
        data_path=str(sample_parquet_file.parent),
        strategy=quote_prices,
    )
    date = datetime.date(2024, 1, 1)
    simulator.replay_date(date)

    # verify order book state
    bids, asks = simulator.get_order_book_state()
    assert len(bids) == 2
    assert len(asks) == 2
    assert bids[0] == ["100.0", "2.0"]  # most recent update
    assert asks[0] == ["101.0", "2.0"]  # most recent update


def test_replay_date_range(test_data_dir, sample_parquet_file):
    """test replaying messages for a date range"""
    simulator = Simulator(
        symbol="btcusdt", data_path=str(test_data_dir), strategy=quote_prices
    )
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 1, 1)
    simulator.replay_date_range(start_date, end_date)

    # verify order book state
    bids, asks = simulator.get_order_book_state()
    assert len(bids) == 2
    assert len(asks) == 2
    assert bids[0] == ["100.0", "2.0"]
    assert asks[0] == ["101.0", "2.0"]


def test_replay_missing_file(test_data_dir):
    """test handling of missing parquet files"""
    simulator = Simulator(
        symbol="btcusdt", data_path=str(test_data_dir), strategy=quote_prices
    )
    date = datetime.date(2024, 1, 1)

    # should not raise exception
    simulator.replay_date_range(date, date)

    # verify order book is empty
    bids, asks = simulator.get_order_book_state()
    assert len(bids) == 0
    assert len(asks) == 0


def test_deterministic_state(sample_parquet_file):
    """test that replay produces deterministic order book state"""
    simulator1 = Simulator(
        symbol="btcusdt",
        data_path=str(sample_parquet_file.parent),
        strategy=quote_prices,
    )
    simulator2 = Simulator(
        symbol="btcusdt",
        data_path=str(sample_parquet_file.parent),
        strategy=quote_prices,
    )

    date = datetime.date(2024, 1, 1)
    simulator1.replay_date(date)
    simulator2.replay_date(date)

    # verify both simulators have identical state
    assert simulator1.get_order_book_state() == simulator2.get_order_book_state()


def test_naive_maker_integration(tmp_path):
    """test naive maker integration with simulator

    this test:
    1. creates a test parquet file with market data
    2. runs simulator with naive maker
    3. verifies fills and P&L tracking
    """
    # create test data directory
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)

    # create test parquet file
    test_data = {
        "event_type": ["depthUpdate"] * 3,
        "event_time": [1000, 2000, 3000],
        "symbol": ["btcusdt"] * 3,
        "first_update_id": [1, 2, 3],
        "final_update_id": [1, 2, 3],
        "bids": [
            ["10000.0,1.0", "9999.0,1.0"],  # first snapshot
            ["10001.0,1.0", "10000.0,1.0"],  # second snapshot - our bid should fill
            ["10002.0,1.0", "10001.0,1.0"],  # third snapshot - our ask should fill
        ],
        "asks": [
            ["10001.0,1.0", "10002.0,1.0"],  # first snapshot
            ["10002.0,1.0", "10003.0,1.0"],  # second snapshot
            ["10003.0,1.0", "10004.0,1.0"],  # third snapshot
        ],
    }

    df = pd.DataFrame(test_data)
    test_file = data_dir / "btcusdt_20240101.parquet"
    df.to_parquet(test_file)

    # run simulator with a spread that matches the book spread to ensure fills
    sim = Simulator(
        symbol="btcusdt",
        data_path=str(data_dir),
        strategy=quote_prices,
        spread=Decimal("1.0"),  # spread matches book spread
    )

    # replay test data
    sim.replay_date(datetime.date(2024, 1, 1))

    # verify fills
    fills_df = sim.get_fills_df()
    assert len(fills_df) == 6  # 3 snapshots, both buy and sell per snapshot

    # verify alternating buy/sell and correct prices
    expected = [
        (
            "buy",
            Decimal("10000.3"),
            Decimal("0.001"),  # base size
        ),  # mid_price - half_spread
        (
            "sell",
            Decimal("10000.7"),
            Decimal("0.001"),  # base size
        ),  # mid_price + half_spread
        ("buy", Decimal("10001.3"), Decimal("0.001")),
        ("sell", Decimal("10001.7"), Decimal("0.001")),
        ("buy", Decimal("10002.3"), Decimal("0.001")),
        ("sell", Decimal("10002.7"), Decimal("0.001")),
    ]
    for i, (side, price, size) in enumerate(expected):
        assert fills_df.iloc[i]["side"] == side
        assert fills_df.iloc[i]["price"] == price
        assert fills_df.iloc[i]["size"] == size

    # verify P&L summary
    pnl_summary = sim.get_pnl_summary()
    assert pnl_summary["num_fills"] == 6
    assert abs(pnl_summary["final_position"]) < 1e-9  # should be flat


def test_backtest_produces_pnl_csv(tmp_path):
    """test that backtest run produces a basic P&L CSV file"""
    # create test data directory
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)

    # create test parquet file
    test_data = {
        "event_type": ["depthUpdate"] * 3,
        "event_time": [1000, 2000, 3000],
        "symbol": ["btcusdt"] * 3,
        "first_update_id": [1, 2, 3],
        "final_update_id": [1, 2, 3],
        "bids": [
            ["10000.0,1.0", "9999.0,1.0"],  # first snapshot
            ["10001.0,1.0", "10000.0,1.0"],  # second snapshot
            ["10002.0,1.0", "10001.0,1.0"],  # third snapshot
        ],
        "asks": [
            ["10001.0,1.0", "10002.0,1.0"],  # first snapshot
            ["10002.0,1.0", "10003.0,1.0"],  # second snapshot
            ["10003.0,1.0", "10004.0,1.0"],  # third snapshot
        ],
    }

    df = pd.DataFrame(test_data)
    test_file = data_dir / "btcusdt_20240101.parquet"
    df.to_parquet(test_file)

    # run simulator with a spread that matches the book spread
    sim = Simulator(
        symbol="btcusdt",
        data_path=str(data_dir),
        strategy=quote_prices,
        spread=Decimal("1.0"),  # spread matches book spread
    )

    # replay test data
    sim.replay_date(datetime.date(2024, 1, 1))

    # get P&L summary and export to CSV
    pnl_summary = sim.get_pnl_summary()
    pnl_csv_path = tmp_path / "pnl_summary.csv"
    pd.DataFrame([pnl_summary]).to_csv(pnl_csv_path, index=False)

    # verify that the CSV file exists and contains expected columns
    assert pnl_csv_path.exists()
    pnl_df = pd.read_csv(pnl_csv_path)
    expected_columns = ["num_fills", "final_position", "total_pnl"]
    for col in expected_columns:
        assert col in pnl_df.columns
