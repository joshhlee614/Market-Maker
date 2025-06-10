"""
Test script to run the recorder and verify Redis stream
"""
import asyncio
import signal
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_feed.recorder import MessageRecorder

async def main():
    """Run the recorder"""
    recorder = MessageRecorder(symbol="btcusdt")
    
    def handle_signal(signum, frame):
        print("\nStopping recorder...")
        asyncio.create_task(recorder.stop())
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_signal)
    
    try:
        print("Starting recorder... Press Ctrl+C to stop")
        await recorder.start()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await recorder.stop()

if __name__ == "__main__":
    asyncio.run(main()) 