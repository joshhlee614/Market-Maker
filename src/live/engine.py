"""
live trading engine for market making

subscribes to redis tick stream and computes optimal quotes
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional

import redis.asyncio as redis

from data_feed.schemas import DepthUpdate
from features.imbalance import get_imbalance_features
from features.micro_price import calculate_microprice
from features.volatility import VolatilityCalculator
from models.size_calculator import SizeCalculator, SizeConfig
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
    ):
        """initialize live engine

        args:
            redis_url: redis connection url
            symbol: trading symbol
        """
        self.redis_client = redis.from_url(redis_url)
        self.symbol = symbol.lower()
        self.stream_key = f"stream:lob:{self.symbol}"

        # initialize strategy components
        self.ev_config = EVConfig()
        self.size_config = SizeConfig()
        self.ev_maker = EVMaker(self.ev_config, self.size_config)
        self.volatility_calc = VolatilityCalculator(window_size=100)

        # state
        self.current_inventory = Decimal("0")
        self.running = False

    async def start(self) -> None:
        """start the live engine loop"""
        logger.info(f"starting live engine for {self.symbol}")
        self.running = True

        try:
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

        except KeyboardInterrupt:
            logger.info("received keyboard interrupt")
        except Exception as e:
            logger.error(f"error in live engine: {e}")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """stop the live engine"""
        logger.info("stopping live engine")
        self.running = False

        if self.redis_client:
            await self.redis_client.aclose()

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

            # calculate features
            imbalance_features = get_imbalance_features(bids, asks)
            microprice_tuples = [
                (Decimal(price), Decimal(qty)) for price, qty in bids[:1]
            ] + [(Decimal(price), Decimal(qty)) for price, qty in asks[:1]]

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

            # print quote to stdout
            print(
                f"quote: bid={bid_quote.price}@{bid_quote.size} "
                f"ask={ask_quote.price}@{ask_quote.size} "
                f"mid={mid_price} spread={ask_quote.price - bid_quote.price}"
            )

        except Exception as e:
            logger.error(f"error processing message: {e}")


async def main():
    """main function for testing"""
    engine = LiveEngine()
    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
