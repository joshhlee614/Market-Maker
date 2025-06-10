"""
unit tests for parquet writer
"""

import datetime
import json
from unittest.mock import AsyncMock, patch

import pandas as pd
import pyarrow as pa
import pytest

from src.data_feed.parquet_writer import (
    ParquetWriter,
    _convert_list_to_string,
    _convert_string_to_list,
)


@pytest.fixture
def test_data_dir(tmp_path):
    """fixture for test data directory"""
    return tmp_path / "test_data"


@pytest.fixture
def sample_depth_update():
    """fixture for sample depth update message"""
    return {
        "e": "depthUpdate",
        "E": 1623456789000,
        "s": "BTCUSDT",
        "U": 1234567,
        "u": 1234568,
        "b": [["50000.00", "1.000"]],
        "a": [["50001.00", "1.000"]],
    }


@pytest.fixture
def mock_parquet_writer():
    """fixture for mocked parquet writer"""
    writer = AsyncMock()
    writer.write = AsyncMock()
    writer.close = AsyncMock()
    return writer


def test_writer_initialization(test_data_dir):
    """test writer initialization"""
    writer = ParquetWriter(base_path=test_data_dir)
    assert writer.symbol == "btcusdt"
    assert writer.base_path == test_data_dir
    assert writer.current_file is None
    assert writer.current_date is None
    assert writer.writer is None
    assert test_data_dir.exists()


def test_file_rotation(test_data_dir, sample_depth_update):
    """test file rotation based on message time"""
    writer = ParquetWriter(base_path=test_data_dir)

    # Write message
    writer.write(sample_depth_update)

    # Check file was created
    expected_date = datetime.datetime.fromtimestamp(
        sample_depth_update["E"] / 1000.0, tz=datetime.UTC
    ).date()
    expected_file = test_data_dir / (
        f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet"
    )
    assert expected_file.exists()

    # Close writer
    writer.close()


def test_message_persistence(test_data_dir, sample_depth_update):
    """test message is correctly written to parquet"""
    writer = ParquetWriter(base_path=test_data_dir)

    # Write message
    writer.write(sample_depth_update)
    writer.close()

    # Read back and verify
    expected_date = datetime.datetime.fromtimestamp(
        sample_depth_update["E"] / 1000.0, tz=datetime.UTC
    ).date()
    file_path = test_data_dir / (f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet")

    df = pd.read_parquet(file_path)
    assert len(df) == 1
    assert df.iloc[0]["event_type"] == sample_depth_update["e"]
    assert df.iloc[0]["event_time"] == sample_depth_update["E"]
    assert df.iloc[0]["symbol"] == sample_depth_update["s"]
    assert df.iloc[0]["first_update_id"] == sample_depth_update["U"]
    assert df.iloc[0]["final_update_id"] == sample_depth_update["u"]

    # Convert stored strings back to lists and compare
    stored_bids = _convert_string_to_list(df.iloc[0]["bids"])
    stored_asks = _convert_string_to_list(df.iloc[0]["asks"])

    assert stored_bids == sample_depth_update["b"]
    assert stored_asks == sample_depth_update["a"]


def test_list_conversion():
    """test list conversion functions"""
    test_list = [["50000.00", "1.000"], ["49999.00", "2.000"]]

    # Convert to strings
    str_list = _convert_list_to_string(test_list)
    assert str_list == ["50000.00,1.000", "49999.00,2.000"]

    # Convert back to list
    back_to_list = _convert_string_to_list(str_list)
    assert back_to_list == test_list


def test_invalid_message_handling(test_data_dir):
    """test handling of invalid messages"""
    writer = ParquetWriter(base_path=test_data_dir)

    # Try to write invalid message
    invalid_message = {"invalid": "message"}
    with pytest.raises(Exception):
        writer.write(invalid_message)

    # Verify no file was created
    assert len(list(test_data_dir.glob("*.parquet"))) == 0

    writer.close()


def test_multiple_messages(test_data_dir, sample_depth_update):
    """test writing multiple messages"""
    writer = ParquetWriter(base_path=test_data_dir)

    # Write same message twice
    writer.write(sample_depth_update)
    writer.write(sample_depth_update)
    writer.close()

    # Verify file contains both messages
    expected_date = datetime.datetime.fromtimestamp(
        sample_depth_update["E"] / 1000.0, tz=datetime.UTC
    ).date()
    file_path = test_data_dir / (f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet")

    df = pd.read_parquet(file_path)
    assert len(df) == 2


def test_cleanup(test_data_dir, sample_depth_update):
    """test proper cleanup of resources"""
    writer = ParquetWriter(base_path=test_data_dir)

    # Write message and close
    writer.write(sample_depth_update)
    writer.close()

    # Verify writer state
    assert writer.writer is None
    assert writer.current_file is None
    assert writer.current_date is None


@pytest.mark.asyncio
async def test_parquet_writer_initialization():
    """test parquet writer initialization"""
    writer = ParquetWriter(symbol="btcusdt")
    assert writer.symbol == "btcusdt"
    assert writer.base_path == "data/parquet"
    assert writer.current_date is not None
    assert writer.current_writer is None


@pytest.mark.asyncio
async def test_parquet_writer_write_message(mock_parquet_writer, sample_depth_update):
    """test writing message to parquet file"""
    with patch("pyarrow.parquet.ParquetWriter", return_value=mock_parquet_writer):
        writer = ParquetWriter()
        await writer.write_message(sample_depth_update)
        mock_parquet_writer.write.assert_called_once()


@pytest.mark.asyncio
async def test_parquet_writer_write_invalid_message(mock_parquet_writer):
    """test writing invalid message to parquet file"""
    with patch("pyarrow.parquet.ParquetWriter", return_value=mock_parquet_writer):
        writer = ParquetWriter()
        await writer.write_message({"invalid": "message"})
        mock_parquet_writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_parquet_writer_close(mock_parquet_writer):
    """test closing parquet writer"""
    with patch("pyarrow.parquet.ParquetWriter", return_value=mock_parquet_writer):
        writer = ParquetWriter()
        await writer.close()
        mock_parquet_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_parquet_writer_file_rotation(mock_parquet_writer):
    """test parquet file rotation"""
    with patch("pyarrow.parquet.ParquetWriter", return_value=mock_parquet_writer):
        writer = ParquetWriter()
        initial_date = writer.current_date
        writer.current_date = None  # Force rotation
        await writer.write_message({"test": "message"})
        assert writer.current_date != initial_date


@pytest.mark.asyncio
async def test_parquet_writer_schema_creation():
    """test parquet schema creation"""
    writer = ParquetWriter()
    schema = writer._create_schema()
    assert isinstance(schema, pa.Schema)
    assert "timestamp" in schema.names
    assert "data" in schema.names


@pytest.mark.asyncio
async def test_parquet_writer_message_to_record(sample_depth_update):
    """test converting message to record"""
    writer = ParquetWriter()
    record = writer._message_to_record(sample_depth_update)
    assert "timestamp" in record
    assert "data" in record
    assert isinstance(record["data"], str)
    assert json.loads(record["data"]) == sample_depth_update
