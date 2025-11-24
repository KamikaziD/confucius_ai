from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
import uuid
import logging

from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter()


logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self, redis_service_instance):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis_service = redis_service_instance
        self.pubsub = None  # Initialize pubsub in startup method

    async def startup(self):
        """Initialize pubsub and start the global listener"""
        if not self.pubsub:
            self.pubsub = self.redis_service.redis.pubsub()
            await self.pubsub.psubscribe("agent_results:*", "agent_activity:*")  # Subscribe to both
            asyncio.create_task(self.run_pubsub_listener())
            logger.info(
                "ConnectionManager startup: Pub/Sub initialized and listener started, subscribed to 'agent_results:*' and 'agent_activity:*'.")

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except RuntimeError as e:
                logger.warning(
                    f"Failed to send message to client {client_id}: {e}. Disconnecting.")
                self.disconnect(client_id)
        else:
            logger.warning(
                f"Attempted to send message to disconnected client: {client_id}")

    async def run_pubsub_listener(self):
        if not self.pubsub:
            logger.error(
                "run_pubsub_listener called before pubsub was initialized.")
            return
        # Subscribe to all agent_results channels
        # await self.pubsub.psubscribe("agent_results:*") # Subscribed in startup
        logger.info(
            "Redis Pub/Sub listener started, subscribed to 'agent_results:*'")
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')

                    # Extract client_id from channel name (e.g., "agent_results:client_id_uuid" or "agent_activity:client_id_uuid")
                    parts = channel.split(':')
                    if len(parts) == 2 and (parts[0] == 'agent_results' or parts[0] == 'agent_activity'):
                        client_id = parts[1]
                        print(
                            f"Dispatching Redis message from channel {channel} to client {client_id}")
                        logger.debug(
                            f"Dispatching Redis message from channel {channel} to client {client_id}")
                        await self.send_personal_message(data, client_id)
                    else:
                        logger.warning(
                            f"Received Redis message on unexpected channel format: {channel}")
                await asyncio.sleep(0.01)  # Yield control to event loop
            except asyncio.TimeoutError:
                pass  # No message in the last timeout period, continue loop
            except Exception as e:
                logger.error(
                    f"Error in Redis Pub/Sub listener: {e}", exc_info=True)
                # Wait before retrying to prevent busy-looping on persistent errors
                await asyncio.sleep(5)


manager = ConnectionManager(redis_service)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            if client_id not in manager.active_connections: # Explicitly check if client is still active
                break
            message = await websocket.receive() # Receive any message type
            if message["type"] == "websocket.pong":
                await manager.receive_pong(client_id)
            # else: handle other incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected gracefully.")
        return # Ensure the coroutine exits
    except Exception as e:
        logger.error(
            f"WebSocket error for client {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)
