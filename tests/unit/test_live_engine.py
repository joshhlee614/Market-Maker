"""
unit tests for live trading engine
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from live.engine import LiveEngine


class TestLiveEngine:
    """test cases for live engine"""

    @pytest.fixture
    def sample_message(self):
        """sample depth update message"""
        return {
            "e": "depthUpdate",
            "E": 1627846261000,
            "s": "BTCUSDT",
            "U": 1627846261,
            "u": 1627846261,
            "b": [["50000.00", "1.000"], ["49999.00", "2.000"]],
            "a": [["50001.00", "1.500"], ["50002.00", "0.500"]],
        }

    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """test that engine initializes correctly"""
        engine = LiveEngine(symbol="btcusdt")

        assert engine.symbol == "btcusdt"
        assert engine.stream_key == "stream:lob:btcusdt"
        assert engine.current_inventory == Decimal("0")
        assert not engine.running
        assert engine.gateway is None
        assert engine.current_bid_order_id is None
        assert engine.current_ask_order_id is None

        await engine.stop()

    @pytest.mark.asyncio
    async def test_engine_initialization_with_credentials(self):
        """test that engine initializes with binance credentials"""
        engine = LiveEngine(
            symbol="btcusdt", api_key="test_key", api_secret="test_secret", testnet=True
        )

        assert engine.api_key == "test_key"
        assert engine.api_secret == "test_secret"
        assert engine.testnet is True

        await engine.stop()

    @pytest.mark.asyncio
    async def test_process_message(self, sample_message):
        """test message processing generates quotes"""
        engine = LiveEngine(symbol="btcusdt")

        # prepare mock message fields
        message_fields = {b"data": json.dumps(sample_message).encode()}

        # capture stdout
        with patch("builtins.print") as mock_print:
            await engine._process_message(message_fields)

            # verify quote was printed (multiple calls due to debug output)
            assert mock_print.call_count > 0

            # check that the final call contains the quote
            final_call = mock_print.call_args_list[-1]
            output = final_call[0][0]
            assert "quote:" in output
            assert "bid=" in output
            assert "ask=" in output
            assert "mid=" in output

        await engine.stop()

    @pytest.mark.asyncio
    async def test_process_message_with_gateway(self, sample_message):
        """test message processing with binance gateway"""
        engine = LiveEngine(
            symbol="btcusdt", api_key="test_key", api_secret="test_secret"
        )

        # Mock the gateway
        mock_gateway = AsyncMock()
        engine.gateway = mock_gateway

        # prepare mock message fields
        message_fields = {b"data": json.dumps(sample_message).encode()}

        # Mock the order management
        with patch.object(
            engine, "_manage_orders", new_callable=AsyncMock
        ) as mock_manage:
            with patch("builtins.print") as mock_print:
                await engine._process_message(message_fields)

                # verify quote was printed
                assert mock_print.call_count > 0

                # verify order management was called
                mock_manage.assert_called_once()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_process_empty_message(self, sample_message):
        """test handling of empty bid/ask message"""
        engine = LiveEngine(symbol="btcusdt")

        empty_message = sample_message.copy()
        empty_message["b"] = []
        empty_message["a"] = []

        message_fields = {b"data": json.dumps(empty_message).encode()}

        with patch("builtins.print") as mock_print:
            await engine._process_message(message_fields)

            # should not print quote for empty message
            mock_print.assert_not_called()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """test engine start and stop lifecycle"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            engine = LiveEngine(symbol="btcusdt")

            # test that engine can be stopped without starting
            await engine.stop()

            # verify redis connection was closed
            mock_client.aclose.assert_called_once()
