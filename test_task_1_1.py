"""
Test script for Task 1.1 - Connect to Binance L2 WS API
"""

import asyncio
import logging
from data_feed.binance_ws import BinanceWebSocket

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def main():
    """Connect to Binance WS and log 10 messages"""
    ws = BinanceWebSocket(symbol="btcusdt")

    try:
        # Connect to WebSocket
        await ws.connect()
        await ws.subscribe()

        # Receive and log 10 messages
        messages_received = 0
        while messages_received < 10:
            message = await ws.receive()
            if message:
                print(f"\nMessage #{messages_received + 1}:")
                print(f"Event Time: {message['E']}")
                print(f"Symbol: {message['s']}")
                print("Top Bids:")
                for i, (price, qty) in enumerate(message["b"][:3]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("Top Asks:")
                for i, (price, qty) in enumerate(message["a"][:3]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("-" * 50)
                messages_received += 1

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await ws.unsubscribe()
        await ws.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
