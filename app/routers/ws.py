from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
import uuid
import logging

from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.pubsub = redis_service.redis.pubsub() # Use async redis client for pubsub

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")
        # Subscribe to client-specific channel
        await self.pubsub.subscribe(f"agent_results:{client_id}")
        # Start listening for messages in the background
        asyncio.create_task(self.listen_for_redis_messages(client_id))

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")
            # Unsubscribe from client-specific channel
            # self.pubsub.unsubscribe(f"agent_results:{client_id}") # Pubsub unsubscribe is sync

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
        else:
            logger.warning(f"Attempted to send message to disconnected client: {client_id}")

    async def listen_for_redis_messages(self, client_id: str):
        while client_id in self.active_connections:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    logger.info(f"Received Redis message on channel {channel}: {data}")
                    await self.send_personal_message(data, client_id)
            except asyncio.TimeoutError:
                # No message in the last timeout period, continue loop
                pass
            except Exception as e:
                logger.error(f"Error listening for Redis messages for client {client_id}: {e}", exc_info=True)
                break # Exit loop on error

manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive, or handle incoming messages if needed
            # For now, we primarily send messages from backend to frontend
            await websocket.receive_text() # This will block until a message is received or connection closed
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)
