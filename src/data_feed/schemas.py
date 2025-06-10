"""
Data schemas for Binance WebSocket messages.
"""
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class DepthUpdate:
    """Schema for depth update messages from Binance WebSocket."""
    e: str  # Event type
    E: int  # Event time
    s: str  # Symbol
    U: int  # First update ID in event
    u: int  # Final update ID in event
    b: List[List[str]]  # Bids to be updated [price, quantity]
    a: List[List[str]]  # Asks to be updated [price, quantity] 