"""
test script for parquet writing
"""
import asyncio
import os
from src.data_feed.recorder import MessageRecorder

async def main():
    """main function"""
    # Set venue to VISION which we know works
    os.environ["BINANCE_VENUE"] = "VISION"
    
    print("\nStarting market data recorder (VISION venue)...")
    
    # Create recorder
    recorder = MessageRecorder()
    
    try:
        # Run for 10 seconds
        await asyncio.wait_for(recorder.start(), timeout=10.0)
    except asyncio.TimeoutError:
        print("\nTest complete - recorded 10 seconds of data")
    finally:
        await recorder.stop()
        print("\nRecorder stopped cleanly")

if __name__ == "__main__":
    asyncio.run(main()) 