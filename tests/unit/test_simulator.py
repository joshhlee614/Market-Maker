"""
test module for simulator

this module contains tests for the Simulator class which:
1. verifies correct replay of parquet data
2. ensures deterministic order book state
3. tests error handling and edge cases
"""

import datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pyarrow import Table, schema

from backtest.simulator import Simulator
from lob.order_book import OrderBook


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
    simulator = Simulator(data_path=str(test_data_dir))
    assert simulator.symbol == "btcusdt"
    assert simulator.data_path == test_data_dir
    assert isinstance(simulator.order_book, OrderBook)


def test_simulator_custom_order_book(test_data_dir):
    """test simulator with custom order book"""
    order_book = OrderBook()
    simulator = Simulator(data_path=str(test_data_dir), order_book=order_book)
    assert simulator.order_book is order_book


def test_replay_date(sample_parquet_file):
    """test replaying messages for a single date"""
    simulator = Simulator(data_path=str(sample_parquet_file.parent))
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
    simulator = Simulator(data_path=str(test_data_dir))
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
    simulator = Simulator(data_path=str(test_data_dir))
    date = datetime.date(2024, 1, 1)

    # should not raise exception
    simulator.replay_date_range(date, date)

    # verify order book is empty
    bids, asks = simulator.get_order_book_state()
    assert len(bids) == 0
    assert len(asks) == 0


def test_deterministic_state(sample_parquet_file):
    """test that replay produces deterministic order book state"""
    simulator1 = Simulator(data_path=str(sample_parquet_file.parent))
    simulator2 = Simulator(data_path=str(sample_parquet_file.parent))

    date = datetime.date(2024, 1, 1)
    simulator1.replay_date(date)
    simulator2.replay_date(date)

    # verify both simulators have identical state
    assert simulator1.get_order_book_state() == simulator2.get_order_book_state()
