"""
Tests for Binance WebSocket client.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data_feed.binance_ws import BinanceWebSocket


@pytest.fixture
def mock_ws():
    """Create a mock WebSocket connection."""
    mock = AsyncMock()
    mock.recv = AsyncMock(return_value=json.dumps({
        "e": "depthUpdate",
        "E": 123456789,
        "s": "BTCUSDT",
        "U": 100,
        "u": 101,
        "b": [["50000.00", "1.200"]],
        "a": [["50001.00", "0.800"]]
    }))
    return mock


@pytest.mark.asyncio
async def test_connect():
    """Test WebSocket connection."""
    client = BinanceWebSocket()
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = AsyncMock()
        await client.connect()
        mock_connect.assert_called_once_with(client.ws_url)


@pytest.mark.asyncio
async def test_receive_messages(mock_ws):
    """Test receiving messages from WebSocket."""
    client = BinanceWebSocket()
    client.ws = mock_ws
    
    await client.receive_messages()
    
    assert client.message_count == 10
    assert mock_ws.recv.call_count == 10
    mock_ws.close.assert_called_once() 