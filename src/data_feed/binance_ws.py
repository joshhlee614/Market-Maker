"""
Binance WebSocket client for L2 order book data.
"""
import asyncio
import json
import logging
from dataclasses import asdict
from typing import Optional

import websockets
from websockets.client import WebSocketClientProtocol

from .schemas import DepthUpdate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceWebSocket:
    """WebSocket client for Binance L2 order book data."""
    
    def __init__(self, symbol: str = "btcusdt"):
        """Initialize the WebSocket client.
        
        Args:
            symbol: Trading pair symbol (default: btcusdt)
        """
        self.symbol = symbol.lower()
        self.ws: Optional[WebSocketClientProtocol] = None
        # Using the data stream endpoint which is recommended for market data only
        self.ws_url = f"wss://data-stream.binance.vision/ws/{self.symbol}@depth@100ms"
        self.message_count = 0
        self.max_messages = 10  # Stop after 10 messages for the test
        self.last_ping = 0
        self.ping_interval = 20  # Ping every 20 seconds
        self.pong_wait_time = 60  # Wait 60 seconds for pong before disconnecting
        self._running = False
    
    async def connect(self) -> None:
        """Connect to the Binance WebSocket stream."""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self._running = True
            print(f"\nConnected to Binance WebSocket stream for {self.symbol}\n")
            # Start ping/pong handler
            asyncio.create_task(self._ping_handler())
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    async def _ping_handler(self) -> None:
        """Handle ping/pong to keep connection alive."""
        while self._running and self.ws and not self.ws.closed:
            try:
                await self.ws.ping()
                self.last_ping = asyncio.get_event_loop().time()
                await asyncio.sleep(self.ping_interval)
            except Exception as e:
                logger.error(f"Error in ping handler: {e}")
                break
    
    async def receive_messages(self) -> None:
        """Receive and process messages from the WebSocket stream."""
        if not self.ws:
            raise RuntimeError("WebSocket connection not established")
        
        try:
            print("\nStarting to receive depth updates:\n")
            while self.message_count < self.max_messages:
                message = await self.ws.recv()
                data = json.loads(message)
                
                # Parse message into DepthUpdate dataclass
                update = DepthUpdate(**data)
                
                # Print a clear, formatted depth update to stdout
                print(f"Depth Update #{self.message_count + 1}:")
                print(f"Symbol: {update.s}")
                print(f"Event Time: {update.E}")
                print("Top 5 Bids:")
                for i, (price, qty) in enumerate(update.b[:5]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("Top 5 Asks:")
                for i, (price, qty) in enumerate(update.a[:5]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("-" * 50)
                
                self.message_count += 1

                # Check if we haven't received a pong in time
                if self.last_ping and (asyncio.get_event_loop().time() - self.last_ping) > self.pong_wait_time:
                    logger.error("No pong received in time, closing connection")
                    break
            
            print("\nReceived 10 messages, stopping.\n")
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            raise
        finally:
            await self.close()
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._running = False
        if self.ws:
            await self.ws.close()
            print("\nWebSocket connection closed\n")

async def main():
    """Main function to run the WebSocket client."""
    client = BinanceWebSocket()
    await client.connect()
    await client.receive_messages()

if __name__ == "__main__":
    asyncio.run(main()) 