"""
Unit tests for Binance REST API gateway
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from live.binance_gateway import BinanceGateway


@pytest.fixture
def gateway():
    """Create a test gateway instance"""
    return BinanceGateway(
        api_key="test_api_key", api_secret="test_api_secret", testnet=True
    )


@pytest.mark.asyncio
async def test_gateway_initialization(gateway):
    """Test gateway initialization"""
    assert gateway.api_key == "test_api_key"
    assert gateway.api_secret == "test_api_secret"
    assert gateway.testnet is True
    assert gateway.base_url == "https://testnet.binance.vision"
    assert gateway.session is None


@pytest.mark.asyncio
async def test_gateway_context_manager():
    """Test gateway async context manager"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    async with gateway as g:
        assert g.session is not None
        assert isinstance(g.session, aiohttp.ClientSession)

    # Session should be closed after exiting context
    assert gateway.session.closed


@pytest.mark.asyncio
async def test_signature_generation(gateway):
    """Test HMAC signature generation"""
    query_string = (
        "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1.0&"
        "price=50000.0&timestamp=1234567890"
    )
    signature = gateway._generate_signature(query_string)

    # Should return a 64-character hex string
    assert len(signature) == 64
    assert isinstance(signature, str)

    # Same input should produce same signature
    signature2 = gateway._generate_signature(query_string)
    assert signature == signature2


@pytest.mark.asyncio
async def test_timestamp_generation(gateway):
    """Test timestamp generation"""
    timestamp = gateway._get_timestamp()

    # Should be a reasonable timestamp (after 2020)
    assert timestamp > 1577836800000  # Jan 1, 2020
    assert isinstance(timestamp, int)


@pytest.mark.asyncio
async def test_post_order_success():
    """Test successful order posting"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    # Mock response
    mock_response = {
        "symbol": "BTCUSDT",
        "orderId": 123456,
        "status": "NEW",
        "side": "BUY",
    }

    with patch.object(gateway, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        result = await gateway.post_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=Decimal("1.0"),
            price=Decimal("50000.0"),
        )

        assert result == mock_response


@pytest.mark.asyncio
async def test_post_order_without_price():
    """Test posting market order without price"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    mock_response = {"orderId": 123456, "status": "FILLED"}

    with patch.object(gateway, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        result = await gateway.post_order(
            symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity=Decimal("1.0")
        )

        assert result == mock_response
        # Check that price is not included in params
        call_args = mock_request.call_args[0]
        params = call_args[2]
        assert "price" not in params


@pytest.mark.asyncio
async def test_cancel_order_success():
    """Test successful order cancellation"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    mock_response = {"status": "CANCELED"}

    with patch.object(gateway, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        result = await gateway.cancel_order(symbol="BTCUSDT", order_id=123456)

        assert result == mock_response


@pytest.mark.asyncio
async def test_cancel_order_no_id_raises_error():
    """Test that canceling without order ID raises error"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    with pytest.raises(
        ValueError, match="Either order_id or orig_client_order_id must be provided"
    ):
        await gateway.cancel_order(symbol="BTCUSDT")


@pytest.mark.asyncio
async def test_get_open_orders():
    """Test getting open orders"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    mock_response = [
        {"orderId": 123456, "symbol": "BTCUSDT", "status": "NEW"},
        {"orderId": 123457, "symbol": "BTCUSDT", "status": "NEW"},
    ]

    with patch.object(gateway, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        result = await gateway.get_open_orders(symbol="BTCUSDT")

        assert result == mock_response
        mock_request.assert_called_once_with(
            "GET", "/api/v3/openOrders", {"symbol": "BTCUSDT"}
        )


@pytest.mark.asyncio
async def test_get_open_orders_all_symbols():
    """Test getting open orders for all symbols"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    mock_response = []

    with patch.object(gateway, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        result = await gateway.get_open_orders()

        assert result == mock_response
        mock_request.assert_called_once_with("GET", "/api/v3/openOrders", {})


@pytest.mark.asyncio
async def test_request_without_session_raises_error():
    """Test that making request without session raises error"""
    gateway = BinanceGateway("key", "secret", testnet=True)

    with pytest.raises(RuntimeError, match="Gateway not initialized"):
        await gateway._request("GET", "/test", {})


@pytest.mark.asyncio
async def test_mainnet_url():
    """Test that mainnet URL is used when testnet=False"""
    gateway = BinanceGateway("key", "secret", testnet=False)
    assert gateway.base_url == "https://api.binance.com"
