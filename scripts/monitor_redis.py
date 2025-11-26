import asyncio
import redis.asyncio as redis
import os
import pprint

# Configuration - you can change these or use environment variables
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
CHANNELS = ["agent_activity:*", "agent_results:*"]


async def main():
    """
    Connects to Redis and listens for messages on specified pub/sub channels.
    """
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    try:
        r = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
        await r.ping()
        print("Connection successful.")
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        print(
            "Please ensure Redis is running and accessible at the specified host and port.")
        return

    pubsub = r.pubsub()

    try:
        # psubscribe allows for pattern matching on channel names
        await pubsub.psubscribe(*CHANNELS)
        print(f"Subscribed to channels: {', '.join(CHANNELS)}")
        print("Listening for messages... Press Ctrl+C to stop.")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
            if message:
                channel = message['channel'].decode('utf-8')
                data = message['data'].decode('utf-8')
                print(f"\n--- New Message ---")
                print(f"Channel: {channel}")
                pprint.pprint({data}, indent=4)
                print(f"-------------------")

    except asyncio.CancelledError:
        print("\nListener cancelled.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing connection.")
        await pubsub.close()
        await r.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
