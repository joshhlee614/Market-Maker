"""
expected value market making strategy with inventory skew

this strategy uses a fill probability model to optimize quote distances
by maximizing expected value (fill probability * spread) while managing
inventory risk through dynamic quote and size adjustments
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, NamedTuple, Tuple

from models.fill_prob import FillProbabilityModel
from models.inventory_skew import InventorySkew, InventorySkewConfig
from models.size_calculator import SizeCalculator, SizeConfig


def default_inventory_config() -> InventorySkewConfig:
    """create default inventory skew config"""
    return InventorySkewConfig(
        max_position=1.0,  # 1 btc max position
        skew_factor=0.5,  # moderate skew
        min_spread_bps=1.0,  # 1 bps minimum spread
        spread_factor=1.0,  # linear spread increase
        continuity_clip=0.1,  # max 0.10 move per side
    )


@dataclass
class EVConfig:
    """configuration for ev maker strategy"""

    # minimum spread to maintain
    min_spread: Decimal = Decimal("0.0005")  # 0.05% minimum spread
    # maximum spread to consider
    max_spread: Decimal = Decimal("0.005")  # 0.5% maximum spread
    # number of points to evaluate for each side
    num_points: int = 10
    # inventory skew configuration
    inventory_config: InventorySkewConfig = field(
        default_factory=default_inventory_config
    )


class Quote(NamedTuple):
    """quote with price and size"""

    price: Decimal
    size: Decimal


class EVMaker:
    """expected value market making strategy"""

    def __init__(self, config: EVConfig, size_config: SizeConfig):
        """initialize ev maker with config"""
        self.config = config
        self.size_config = size_config
        self.inventory_skew = InventorySkew(config.inventory_config)
        self.size_calculator = SizeCalculator(size_config)

    def quote_prices(
        self,
        mid_price: Decimal,
        volatility: Decimal,
        bid_probability: Decimal,
        ask_probability: Decimal,
        inventory: Decimal = Decimal("0"),
        best_bid: Decimal = None,
        best_ask: Decimal = None,
        bids: List[List[str]] = None,
        asks: List[List[str]] = None,
        fill_model: FillProbabilityModel = None,
    ) -> Tuple[Quote, Quote]:
        """
        quote bid and ask prices and sizes using fill probability model

        args:
            mid_price: current mid price
            volatility: current volatility estimate
            bid_probability: probability of bid fill
            ask_probability: probability of ask fill
            inventory: current inventory position
            best_bid: current best bid (optional)
            best_ask: current best ask (optional)
            bids: list of [price, quantity] pairs, sorted descending (optional)
            asks: list of [price, quantity] pairs, sorted ascending (optional)
            fill_model: trained fill probability model (optional)

        returns:
            tuple of (bid_quote, ask_quote)
        """
        # get inventory-skewed base prices
        base_bid, base_ask = self.inventory_skew.apply_skew(
            float(mid_price), float(inventory)
        )

        # convert to decimal for consistency
        base_bid_dec = Decimal(str(base_bid))
        base_ask_dec = Decimal(str(base_ask))

        # log base prices and initial spread
        base_spread = base_ask_dec - base_bid_dec
        print("\nev optimization starting points:")
        print(f"base bid: {base_bid_dec}")
        print(f"base ask: {base_ask_dec}")
        print(f"base spread: {base_spread}")

        # calculate price points to evaluate around skewed base prices
        # spread grid now centered on skewed base prices
        bid_spreads = [
            Decimal(
                str(i * float(self.config.max_spread) / (self.config.num_points - 1))
            )
            for i in range(self.config.num_points)
        ]
        ask_spreads = [
            Decimal(
                str(i * float(self.config.max_spread) / (self.config.num_points - 1))
            )
            for i in range(self.config.num_points)
        ]

        # evaluate expected value for each price point
        best_bid_ev = Decimal("-inf")
        best_ask_ev = Decimal("-inf")
        best_bid_price = base_bid_dec
        best_ask_price = base_ask_dec

        # track optimization progress
        print("\nbid optimization:")
        # evaluate bid prices
        for spread in bid_spreads:
            price = base_bid_dec - spread  # adjust down from base bid
            if fill_model is not None:
                fill_prob = fill_model.predict(
                    bids, asks, price, self.size_config.base_size, "buy"
                )
            else:
                fill_prob = bid_probability
            fill_prob_dec = Decimal(str(float(fill_prob)))
            ev = fill_prob_dec * spread
            print(
                f"  price: {price}, spread: {spread}, fill_prob: {fill_prob_dec}, ev: {ev}"
            )
            if ev > best_bid_ev:
                best_bid_ev = ev
                best_bid_price = price

        print("\nask optimization:")
        # evaluate ask prices
        for spread in ask_spreads:
            price = base_ask_dec + spread  # adjust up from base ask
            if fill_model is not None:
                fill_prob = fill_model.predict(
                    bids, asks, price, self.size_config.base_size, "sell"
                )
            else:
                fill_prob = ask_probability
            fill_prob_dec = Decimal(str(float(fill_prob)))
            ev = fill_prob_dec * spread
            print(
                f"  price: {price}, spread: {spread}, fill_prob: {fill_prob_dec}, ev: {ev}"
            )
            if ev > best_ask_ev:
                best_ask_ev = ev
                best_ask_price = price

        # ensure we maintain minimum spread
        if best_ask_price - best_bid_price < self.config.min_spread:
            mid = (best_ask_price + best_bid_price) / Decimal("2")
            best_bid_price = mid - self.config.min_spread / Decimal("2")
            best_ask_price = mid + self.config.min_spread / Decimal("2")

        # calculate inventory-adjusted sizes
        bid_size, ask_size = self.size_calculator.get_sizes(inventory)

        # final quote summary
        print("\nfinal quotes:")
        print(f"best bid: {best_bid_price} (ev: {best_bid_ev})")
        print(f"best ask: {best_ask_price} (ev: {best_ask_ev})")
        print(f"final spread: {best_ask_price - best_bid_price}")

        # verify optimization started from base prices
        assert (
            abs(base_bid_dec - best_bid_price) <= self.config.max_spread
        ), "bid moved too far from base"
        assert (
            abs(base_ask_dec - best_ask_price) <= self.config.max_spread
        ), "ask moved too far from base"

        return Quote(best_bid_price, bid_size), Quote(best_ask_price, ask_size)
