"""
unit tests for binance websocket client
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from websockets.exceptions import ConnectionClosedOK

from data_feed.binance_ws import BinanceWebSocket


@pytest.fixture
def mock_websocket():
    """fixture for mocked websocket connection"""
    websocket = AsyncMock()
    websocket.__aenter__.return_value = websocket
    websocket.__aexit__.return_value = None
    return websocket


@pytest.mark.asyncio
async def test_binance_ws_initialization():
    """test websocket initialization"""
    ws = BinanceWebSocket(symbol="btcusdt")
    assert ws.symbol == "btcusdt"
    assert ws.url == "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"
    assert not ws._running


@pytest.mark.asyncio
async def test_binance_ws_connect(mock_websocket):
    """test websocket connection"""
    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        assert ws._ws == mock_websocket


@pytest.mark.asyncio
async def test_binance_ws_disconnect(mock_websocket):
    """test websocket disconnection"""
    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        await ws.disconnect()
        assert ws._ws is None
        mock_websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_binance_ws_subscribe(mock_websocket):
    """test websocket subscription"""
    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        await ws.subscribe()
        mock_websocket.send.assert_called_once()


@pytest.mark.asyncio
async def test_binance_ws_unsubscribe(mock_websocket):
    """test websocket unsubscription"""
    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        await ws.unsubscribe()
        mock_websocket.send.assert_called_once()


@pytest.mark.asyncio
async def test_binance_ws_receive(mock_websocket):
    """test websocket message reception"""
    test_message = {"test": "message"}
    mock_websocket.recv.return_value = json.dumps(test_message)

    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        message = await ws.receive()
        assert message == test_message


@pytest.mark.asyncio
async def test_binance_ws_receive_connection_closed(mock_websocket):
    """test websocket connection closed handling"""
    mock_websocket.recv.side_effect = ConnectionClosedOK(None, None)

    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        message = await ws.receive()
        assert message is None


@pytest.mark.asyncio
async def test_binance_ws_receive_invalid_json(mock_websocket):
    """test websocket invalid json handling"""
    mock_websocket.recv.return_value = "invalid json"

    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        await ws.connect()
        message = await ws.receive()
        assert message is None


@pytest.mark.asyncio
async def test_binance_ws_is_connected(mock_websocket):
    """test websocket connection status"""
    with patch("websockets.connect", return_value=mock_websocket):
        ws = BinanceWebSocket()
        assert not ws.is_connected()
        await ws.connect()
        assert ws.is_connected()
        await ws.disconnect()
        assert not ws.is_connected()
