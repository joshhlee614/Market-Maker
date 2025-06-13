"""
test script for market data recording system
"""

import asyncio
import json
import os
import redis.asyncio as redis
from data_feed.recorder import MessageRecorder


async def monitor_redis_stream(
    redis_client: redis.Redis, stream_key: str, count: int = 5
):
    """monitor redis stream for messages

    args:
        redis_client: redis client
        stream_key: stream key to monitor
        count: number of messages to monitor
    """
    print(f"\nMonitoring Redis stream: {stream_key}")
    print("Waiting for messages...\n")

    messages_received = 0
    last_id = "0-0"  # start from beginning

    while messages_received < count:
        # read new messages from stream
        messages = await redis_client.xread(
            streams={stream_key: last_id}, count=1, block=1000
        )

        if messages:
            # update last_id for next read
            stream_messages = messages[0][1]
            for message_id, fields in stream_messages:
                last_id = message_id

                # parse message data
                data = json.loads(fields[b"data"])

                # print formatted depth update
                print(f"Message #{messages_received + 1}:")
                print(f"Event Time: {data['E']}")
                print(f"Symbol: {data['s']}")
                print("Top 5 Bids:")
                for i, (price, qty) in enumerate(data["b"][:5]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("Top 5 Asks:")
                for i, (price, qty) in enumerate(data["a"][:5]):
                    print(f"  {i+1}. Price: {price}, Quantity: {qty}")
                print("-" * 50)

                messages_received += 1


async def main():
    """main function"""
    # Set venue to VISION which we know works
    os.environ["BINANCE_VENUE"] = "VISION"

    print("\nStarting market data recorder (VISION venue)...")

    # Create recorder and redis client
    recorder = MessageRecorder()
    redis_client = redis.from_url("redis://localhost:6379")

    try:
        # Run recorder and monitor in parallel with shorter timeout
        await asyncio.gather(
            recorder.start(),
            monitor_redis_stream(
                redis_client=redis_client,
                stream_key="stream:lob:btcusdt",
                count=5,  # Stop after 5 messages
            ),
        )
    except KeyboardInterrupt:
        print("\nStopping test...")
    finally:
        await recorder.stop()
        await redis_client.close()
        print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(main())
