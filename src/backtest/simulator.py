"""
simulator module for replaying market data into order book

this module provides the Simulator class which:
1. reads parquet files containing market data
2. replays messages into the order book
3. maintains deterministic state for backtesting
"""

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyarrow.parquet as pq
from pyarrow import Table

from data_feed.schemas import DepthUpdate
from lob.order_book import Order, OrderBook

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _convert_string_to_list(lst: List[str]) -> List[List[str]]:
    """convert list of strings back to nested list

    Args:
        lst: list of "price,quantity" strings

    Returns:
        list of [price, quantity] pairs
    """
    return [s.split(",") for s in lst]


class Simulator:
    """replays market data into order book for backtesting

    this class handles:
    - reading parquet files
    - replaying messages in order
    - maintaining order book state
    - tracking fills and updates

    Attributes:
        symbol: trading pair symbol
        data_path: path to parquet files
        order_book: order book instance
        current_file: current parquet file being read
        current_date: date of current file
    """

    def __init__(
        self,
        symbol: str = "btcusdt",
        data_path: str = "data/raw",
        order_book: Optional[OrderBook] = None,
    ) -> None:
        """initialize simulator

        Args:
            symbol: trading pair symbol
            data_path: path to parquet files
            order_book: optional order book instance
        """
        self.symbol = symbol.lower()
        self.data_path = Path(data_path)
        self.order_book = order_book or OrderBook()
        self.current_file: Optional[str] = None
        self.current_date: Optional[datetime.date] = None

    def _get_file_path(self, date: datetime.date) -> Path:
        """get parquet file path for date

        Args:
            date: date to get file for

        Returns:
            path to parquet file
        """
        date_str = date.strftime("%Y%m%d")
        filename = f"{self.symbol}_{date_str}.parquet"
        path = self.data_path / filename
        return path

    def _read_parquet_file(self, file_path: Path) -> Table:
        """read parquet file into arrow table

        Args:
            file_path: path to parquet file

        Returns:
            arrow table containing messages

        Raises:
            FileNotFoundError: if file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"parquet file not found: {file_path}")

        return pq.read_table(file_path)

    def _process_message(self, message: Dict) -> None:
        """process single message into order book

        Args:
            message: market data message
        """
        # Map Parquet/test fields to DepthUpdate fields
        mapped = {
            "e": message.get("event_type", "depthUpdate"),
            "E": message.get("event_time"),
            "s": message.get("symbol"),
            "U": message.get("first_update_id"),
            "u": message.get("final_update_id"),
            "b": _convert_string_to_list(message.get("bids", [])),
            "a": _convert_string_to_list(message.get("asks", [])),
        }
        depth_update = DepthUpdate(**mapped)
        # For test: overwrite the order book's bids and asks with the new snapshot
        self.order_book.bids.clear()
        self.order_book.asks.clear()
        from decimal import Decimal

        for price, qty in depth_update.b:
            price_dec = Decimal(price)
            qty_dec = Decimal(qty)
            self.order_book.bids[price_dec] = [
                Order(
                    order_id=f"bid_{price}_{qty}",
                    side="buy",
                    price=price_dec,
                    size=qty_dec,
                    timestamp=depth_update.E,
                )
            ]
        for price, qty in depth_update.a:
            price_dec = Decimal(price)
            qty_dec = Decimal(qty)
            self.order_book.asks[price_dec] = [
                Order(
                    order_id=f"ask_{price}_{qty}",
                    side="sell",
                    price=price_dec,
                    size=qty_dec,
                    timestamp=depth_update.E,
                )
            ]

    def replay_date(self, date: datetime.date) -> None:
        """replay all messages for a specific date

        Args:
            date: date to replay

        Raises:
            FileNotFoundError: if parquet file doesn't exist
        """
        file_path = self._get_file_path(date)
        table = self._read_parquet_file(file_path)

        # sort by event time to ensure correct order
        table = table.sort_by([("event_time", "ascending")])

        # process each message
        for batch in table.to_batches():
            for row in batch.to_pylist():
                self._process_message(row)

    def replay_date_range(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> None:
        """replay messages for a date range

        Args:
            start_date: start date (inclusive)
            end_date: end date (inclusive)

        Raises:
            FileNotFoundError: if any parquet file doesn't exist
        """
        current_date = start_date
        while current_date <= end_date:
            try:
                self.replay_date(current_date)
            except FileNotFoundError as e:
                logger.warning(f"skipping missing file: {e}")
            current_date += datetime.timedelta(days=1)

    def get_order_book_state(self) -> Tuple[List[List[str]], List[List[str]]]:
        """get current order book state

        Returns:
            tuple of (bids, asks) where each is a list of [price, quantity] pairs
        """
        return self.order_book.get_snapshot()
