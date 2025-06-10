"""
unit tests for parquet writer
"""
import datetime
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data_feed.parquet_writer import ParquetWriter, _convert_list_to_string, _convert_string_to_list

@pytest.fixture
def test_data_dir(tmp_path):
    """fixture for test data directory"""
    return tmp_path / "test_data"

@pytest.fixture
def sample_message():
    """fixture for sample depth update message"""
    return {
        "e": "depthUpdate",
        "E": int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000),
        "s": "BTCUSDT",
        "U": 1234567,
        "u": 1234568,
        "b": [["50000.00", "1.000"]],
        "a": [["50001.00", "1.000"]]
    }

def test_writer_initialization(test_data_dir):
    """test writer initialization"""
    writer = ParquetWriter(base_path=test_data_dir)
    assert writer.symbol == "btcusdt"
    assert writer.base_path == test_data_dir
    assert writer.current_file is None
    assert writer.current_date is None
    assert writer.writer is None
    assert test_data_dir.exists()

def test_file_rotation(test_data_dir, sample_message):
    """test file rotation based on message time"""
    writer = ParquetWriter(base_path=test_data_dir)
    
    # Write message
    writer.write(sample_message)
    
    # Check file was created
    expected_date = datetime.datetime.fromtimestamp(
        sample_message["E"] / 1000.0,
        tz=datetime.UTC
    ).date()
    expected_file = test_data_dir / f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet"
    assert expected_file.exists()
    
    # Close writer
    writer.close()

def test_message_persistence(test_data_dir, sample_message):
    """test message is correctly written to parquet"""
    writer = ParquetWriter(base_path=test_data_dir)
    
    # Write message
    writer.write(sample_message)
    writer.close()
    
    # Read back and verify
    expected_date = datetime.datetime.fromtimestamp(
        sample_message["E"] / 1000.0,
        tz=datetime.UTC
    ).date()
    file_path = test_data_dir / f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet"
    
    df = pd.read_parquet(file_path)
    assert len(df) == 1
    assert df.iloc[0]["event_type"] == sample_message["e"]
    assert df.iloc[0]["event_time"] == sample_message["E"]
    assert df.iloc[0]["symbol"] == sample_message["s"]
    assert df.iloc[0]["first_update_id"] == sample_message["U"]
    assert df.iloc[0]["final_update_id"] == sample_message["u"]
    
    # Convert stored strings back to lists and compare
    stored_bids = _convert_string_to_list(df.iloc[0]["bids"])
    stored_asks = _convert_string_to_list(df.iloc[0]["asks"])
    
    assert stored_bids == sample_message["b"]
    assert stored_asks == sample_message["a"]

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

def test_multiple_messages(test_data_dir, sample_message):
    """test writing multiple messages"""
    writer = ParquetWriter(base_path=test_data_dir)
    
    # Write same message twice
    writer.write(sample_message)
    writer.write(sample_message)
    writer.close()
    
    # Verify file contains both messages
    expected_date = datetime.datetime.fromtimestamp(
        sample_message["E"] / 1000.0,
        tz=datetime.UTC
    ).date()
    file_path = test_data_dir / f"btcusdt_{expected_date.strftime('%Y%m%d')}.parquet"
    
    df = pd.read_parquet(file_path)
    assert len(df) == 2

def test_cleanup(test_data_dir, sample_message):
    """test proper cleanup of resources"""
    writer = ParquetWriter(base_path=test_data_dir)
    
    # Write message and close
    writer.write(sample_message)
    writer.close()
    
    # Verify writer state
    assert writer.writer is None
    assert writer.current_file is None
    assert writer.current_date is None 