"""
live trading engine for market making

subscribes to redis tick stream and computes optimal quotes
"""

import asyncio
import json
import logging
import os
from decimal import Decimal
from typing import Dict, Optional

import redis.asyncio as redis

from data_feed.schemas import DepthUpdate
from features.volatility import VolatilityCalculator
from live.binance_gateway import BinanceGateway
from models.size_calculator import SizeConfig
from strategy.ev_maker import EVConfig, EVMaker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LiveEngine:
    """live trading engine for market making"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        symbol: str = "btcusdt",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
    ):
        """initialize live engine

        args:
            redis_url: redis connection url
            symbol: trading symbol
            api_key: binance api key (from env if not provided)
            api_secret: binance api secret (from env if not provided)
            testnet: whether to use testnet
        """
        self.redis_client = redis.from_url(redis_url)
        self.symbol = symbol.lower()
        self.stream_key = f"stream:lob:{self.symbol}"

        # initialize strategy components
        self.ev_config = EVConfig()
        self.size_config = SizeConfig()
        self.ev_maker = EVMaker(self.ev_config, self.size_config)
        self.volatility_calc = VolatilityCalculator(window_size=100)

        # binance gateway
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.testnet = testnet
        self.gateway: Optional[BinanceGateway] = None

        # order tracking
        self.current_bid_order_id: Optional[str] = None
        self.current_ask_order_id: Optional[str] = None

        # state
        self.current_inventory = Decimal("0")
        self.running = False

        # fill tracking
        self.last_trade_id: Optional[int] = None
        self.position_key = f"position:{self.symbol}"
        self.pnl_key = f"pnl:{self.symbol}"

    async def start(self) -> None:
        """start the live engine loop"""
        logger.info(f"starting live engine for {self.symbol}")
        self.running = True

        # initialize binance gateway if credentials provided
        if self.api_key and self.api_secret:
            self.gateway = BinanceGateway(self.api_key, self.api_secret, self.testnet)
            logger.info("binance gateway initialized")
        else:
            logger.warning(
                "no binance credentials provided, running in simulation mode"
            )

        # initialize redis state
        await self._initialize_redis_state()

        try:
            if self.gateway:
                async with self.gateway:
                    await self._run_loop()
            else:
                await self._run_loop()
        except KeyboardInterrupt:
            logger.info("received keyboard interrupt")
        except Exception as e:
            logger.error(f"error in live engine: {e}")
        finally:
            await self.stop()

    async def _run_loop(self) -> None:
        """main engine loop"""
        while self.running:
            # read latest message from redis stream
            messages = await self.redis_client.xread(
                {self.stream_key: "$"},
                count=1,
                block=100,  # shorter block time for faster shutdown
            )

            if not messages:
                continue

            # process the latest message
            stream_name, stream_messages = messages[0]

            for message_id, fields in stream_messages:
                await self._process_message(fields)

    async def stop(self) -> None:
        """stop the live engine"""
        logger.info("stopping live engine")
        self.running = False

        if self.redis_client:
            await self.redis_client.aclose()

    async def _initialize_redis_state(self) -> None:
        """initialize redis position and pnl if they don't exist"""
        try:
            # check if position exists, if not initialize to 0
            position_exists = await self.redis_client.exists(self.position_key)
            if not position_exists:
                await self.redis_client.set(self.position_key, "0")
                logger.info(f"initialized position key {self.position_key} to 0")

            # check if pnl exists, if not initialize to 0
            pnl_exists = await self.redis_client.exists(self.pnl_key)
            if not pnl_exists:
                await self.redis_client.set(self.pnl_key, "0")
                logger.info(f"initialized pnl key {self.pnl_key} to 0")

            # load current inventory from redis
            position_str = await self.redis_client.get(self.position_key)
            if position_str:
                self.current_inventory = Decimal(position_str.decode())
                logger.info(f"loaded current inventory: {self.current_inventory}")

        except Exception as e:
            logger.error(f"error initializing redis state: {e}")

    async def _process_message(self, fields: Dict) -> None:
        """process a single message from redis stream"""
        try:
            # parse message data
            message_data = json.loads(fields[b"data"].decode())
            depth_update = DepthUpdate(**message_data)

            # convert to format expected by strategy
            bids = depth_update.b  # list of [price, qty] strings
            asks = depth_update.a  # list of [price, qty] strings

            if not bids or not asks:
                return

            # calculate mid price
            best_bid = Decimal(bids[0][0])
            best_ask = Decimal(asks[0][0])
            mid_price = (best_bid + best_ask) / Decimal("2")

            # update volatility
            volatility = self.volatility_calc.update(mid_price)

            # generate quotes using ev maker
            bid_quote, ask_quote = self.ev_maker.quote_prices(
                mid_price=mid_price,
                volatility=Decimal(str(volatility)),
                bid_probability=Decimal("0.5"),  # default probability
                ask_probability=Decimal("0.5"),  # default probability
                inventory=self.current_inventory,
                best_bid=best_bid,
                best_ask=best_ask,
                bids=bids,
                asks=asks,
            )

            # print quote to stdout (always do this)
            print(
                f"quote: bid={bid_quote.price}@{bid_quote.size} "
                f"ask={ask_quote.price}@{ask_quote.size} "
                f"mid={mid_price} spread={ask_quote.price - bid_quote.price}"
            )

            # place orders if gateway is available
            if self.gateway:
                await self._manage_orders(bid_quote, ask_quote)
                # check for fills after managing orders
                await self._check_for_fills()

        except Exception as e:
            logger.error(f"error processing message: {e}")

    async def _manage_orders(self, bid_quote, ask_quote) -> None:
        """manage orders on binance"""
        try:
            # cancel existing orders first
            await self._cancel_existing_orders()

            # place new orders
            symbol = self.symbol.upper()

            # place bid order
            try:
                bid_result = await self.gateway.post_order(
                    symbol=symbol,
                    side="BUY",
                    order_type="LIMIT",
                    quantity=bid_quote.size,
                    price=bid_quote.price,
                    time_in_force="GTC",
                )
                self.current_bid_order_id = str(bid_result.get("orderId"))
                logger.info(f"placed bid order: {bid_result}")
            except Exception as e:
                logger.error(f"failed to place bid order: {e}")

            # place ask order
            try:
                ask_result = await self.gateway.post_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="LIMIT",
                    quantity=ask_quote.size,
                    price=ask_quote.price,
                    time_in_force="GTC",
                )
                self.current_ask_order_id = str(ask_result.get("orderId"))
                logger.info(f"placed ask order: {ask_result}")
            except Exception as e:
                logger.error(f"failed to place ask order: {e}")

        except Exception as e:
            logger.error(f"error managing orders: {e}")

    async def _cancel_existing_orders(self) -> None:
        """cancel any existing orders"""
        try:
            symbol = self.symbol.upper()

            # cancel bid order
            if self.current_bid_order_id:
                try:
                    await self.gateway.cancel_order(
                        symbol, order_id=int(self.current_bid_order_id)
                    )
                    logger.info(f"canceled bid order: {self.current_bid_order_id}")
                except Exception as e:
                    logger.warning(f"failed to cancel bid order: {e}")
                finally:
                    self.current_bid_order_id = None

            # cancel ask order
            if self.current_ask_order_id:
                try:
                    await self.gateway.cancel_order(
                        symbol, order_id=int(self.current_ask_order_id)
                    )
                    logger.info(f"canceled ask order: {self.current_ask_order_id}")
                except Exception as e:
                    logger.warning(f"failed to cancel ask order: {e}")
                finally:
                    self.current_ask_order_id = None

        except Exception as e:
            logger.error(f"error canceling orders: {e}")

    async def _check_for_fills(self) -> None:
        """check for new fills and update position/pnl"""
        if not self.gateway:
            return

        try:
            symbol = self.symbol.upper()

            # get recent trades
            trades = await self.gateway.get_account_trades(
                symbol=symbol,
                limit=10,
                from_id=self.last_trade_id,
            )

            if not trades:
                return

            # process new trades
            for trade in trades:
                trade_id = int(trade["id"])

                # skip if we've already processed this trade
                if self.last_trade_id and trade_id <= self.last_trade_id:
                    continue

                await self._process_fill(trade)
                self.last_trade_id = trade_id

        except Exception as e:
            logger.error(f"error checking for fills: {e}")

    async def _process_fill(self, trade: Dict) -> None:
        """process a single fill and update position/pnl"""
        try:
            # extract trade details
            side = trade["isBuyer"]  # true if we were the buyer
            price = Decimal(trade["price"])
            qty = Decimal(trade["qty"])
            commission = Decimal(trade["commission"])

            # calculate position change
            if side:  # we bought
                position_change = qty
            else:  # we sold
                position_change = -qty

            # update current inventory
            self.current_inventory += position_change

            # calculate pnl impact (simplified - commission cost)
            pnl_change = -commission  # commission is always a cost

            # update redis
            await self._update_redis_state(
                position_change, pnl_change, price, qty, side
            )

            logger.info(
                f"fill processed: side={'BUY' if side else 'SELL'} "
                f"price={price} qty={qty} new_inventory={self.current_inventory}"
            )

        except Exception as e:
            logger.error(f"error processing fill: {e}")

    async def _update_redis_state(
        self,
        position_change: Decimal,
        pnl_change: Decimal,
        price: Decimal,
        qty: Decimal,
        is_buyer: bool,
    ) -> None:
        """update position and pnl in redis"""
        try:
            # update position
            await self.redis_client.set(self.position_key, str(self.current_inventory))

            # get current pnl and update
            current_pnl_str = await self.redis_client.get(self.pnl_key)
            current_pnl = (
                Decimal(current_pnl_str.decode()) if current_pnl_str else Decimal("0")
            )
            new_pnl = current_pnl + pnl_change
            await self.redis_client.set(self.pnl_key, str(new_pnl))

            logger.info(
                f"redis updated: position={self.current_inventory} pnl={new_pnl}"
            )

        except Exception as e:
            logger.error(f"error updating redis state: {e}")


async def main():
    """main function for testing"""
    engine = LiveEngine()
    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
