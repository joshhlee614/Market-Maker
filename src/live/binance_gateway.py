"""
Binance REST API gateway for order management

This module provides a client for interacting with Binance's REST API
for placing and canceling orders on the testnet.
"""

import hashlib
import hmac
import logging
import time
import urllib.parse
from decimal import Decimal
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BinanceGateway:
    """Binance REST API client for order management"""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """Initialize Binance gateway

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use testnet (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Base URLs
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for API request"""
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)

    async def _request(
        self, method: str, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make authenticated request to Binance API"""
        if not self.session:
            raise RuntimeError("Gateway not initialized. Use async context manager.")

        # Add timestamp
        params["timestamp"] = self._get_timestamp()

        # Create query string
        query_string = urllib.parse.urlencode(params)

        # Generate signature
        signature = self._generate_signature(query_string)
        params["signature"] = signature

        # Headers
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "POST":
                async with self.session.post(
                    url, data=params, headers=headers
                ) as response:
                    result = await response.json()
                    if response.status != 200:
                        logger.error(f"API error: {result}")
                        raise Exception(f"Binance API error: {result}")
                    return result
            elif method == "DELETE":
                async with self.session.delete(
                    url, params=params, headers=headers
                ) as response:
                    result = await response.json()
                    if response.status != 200:
                        logger.error(f"API error: {result}")
                        raise Exception(f"Binance API error: {result}")
                    return result
            elif method == "GET":
                async with self.session.get(
                    url, params=params, headers=headers
                ) as response:
                    result = await response.json()
                    if response.status != 200:
                        logger.error(f"API error: {result}")
                        raise Exception(f"Binance API error: {result}")
                    return result
            else:
                raise ValueError(f"Unsupported method: {method}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            raise

    async def post_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """Post a new order to Binance

        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            side: Order side ("BUY" or "SELL")
            order_type: Order type ("LIMIT", "MARKET", etc.)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force ("GTC", "IOC", "FOK")

        Returns:
            Order response from Binance API
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "timeInForce": time_in_force,
        }

        if price is not None:
            params["price"] = str(price)

        logger.info(f"Posting order: {params}")

        try:
            result = await self._request("POST", "/api/v3/order", params)
            logger.info(f"Order posted successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to post order: {e}")
            raise

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel an existing order

        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            order_id: Binance order ID
            orig_client_order_id: Original client order ID

        Returns:
            Cancel response from Binance API
        """
        if not order_id and not orig_client_order_id:
            raise ValueError("Either order_id or orig_client_order_id must be provided")

        params = {"symbol": symbol.upper()}

        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        logger.info(f"Canceling order: {params}")

        try:
            result = await self._request("DELETE", "/api/v3/order", params)
            logger.info(f"Order canceled successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    async def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders

        Args:
            symbol: Trading symbol (optional, gets all symbols if None)

        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        try:
            result = await self._request("GET", "/api/v3/openOrders", params)
            return result
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise

    async def get_order_status(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get order status

        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            order_id: Binance order ID
            orig_client_order_id: Original client order ID

        Returns:
            Order status from Binance API
        """
        if not order_id and not orig_client_order_id:
            raise ValueError("Either order_id or orig_client_order_id must be provided")

        params = {"symbol": symbol.upper()}

        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        try:
            result = await self._request("GET", "/api/v3/order", params)
            return result
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            raise

    async def get_account_trades(
        self,
        symbol: str,
        limit: int = 100,
        from_id: Optional[int] = None,
    ) -> list:
        """Get account trade list

        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            limit: Number of trades to retrieve (max 1000)
            from_id: TradeId to fetch from (optional)

        Returns:
            List of recent trades
        """
        params = {
            "symbol": symbol.upper(),
            "limit": limit,
        }

        if from_id:
            params["fromId"] = from_id

        try:
            result = await self._request("GET", "/api/v3/myTrades", params)
            return result
        except Exception as e:
            logger.error(f"Failed to get account trades: {e}")
            raise
