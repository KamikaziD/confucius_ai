import redis
import json
from typing import Optional, Any, List
from app.config import settings

class RedisService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.sync_redis: Optional[redis.Redis] = None # Synchronous client
    
    async def connect(self):
        """Connect to Redis (async)"""
        self.redis = redis.asyncio.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        # Ensure connection is established
        await self.redis.ping()
    
    def connect_sync(self):
        """Connect to Redis (sync)"""
        self.sync_redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        # Ensure connection is established
        self.sync_redis.ping()

    async def disconnect(self):
        """Disconnect from Redis (async)"""
        if self.redis:
            await self.redis.close()
    
    def disconnect_sync(self):
        """Disconnect from Redis (sync)"""
        if self.sync_redis:
            self.sync_redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (async)"""
        if not self.redis:
            await self.connect() # Auto-connect if not connected
        
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    def get_sync(self, key: str) -> Optional[Any]:
        """Get value from cache (sync)"""
        if not self.sync_redis:
            self.connect_sync() # Auto-connect if not connected
        
        value = self.sync_redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (async)"""
        if not self.redis:
            await self.connect() # Auto-connect if not connected
        
        serialized = json.dumps(value) if not isinstance(value, str) else value
        
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)
        
        return True
    
    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (sync)"""
        if not self.sync_redis:
            self.connect_sync() # Auto-connect if not connected
        
        serialized = json.dumps(value) if not isinstance(value, str) else value
        
        if ttl:
            self.sync_redis.setex(key, ttl, serialized)
        else:
            self.sync_redis.set(key, serialized)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache (async)"""
        if not self.redis:
            return False
        
        result = await self.redis.delete(key)
        return result > 0
    
    def delete_sync(self, key: str) -> bool:
        """Delete key from cache (sync)"""
        if not self.sync_redis:
            return False
        
        result = self.sync_redis.delete(key)
        return result > 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (async)"""
        if not self.redis:
            return []
        
        return await self.redis.keys(pattern)
    
    def keys_sync(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (sync)"""
        if not self.sync_redis:
            return []
        
        return self.sync_redis.keys(pattern)
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel (async)"""
        if not self.redis:
            await self.connect() # Auto-connect if not connected
        
        serialized = json.dumps(message) if not isinstance(message, str) else message
        return await self.redis.publish(channel, serialized)
    
    def publish_sync(self, channel: str, message: Any) -> int:
        """Publish message to channel (sync)"""
        if not self.sync_redis:
            self.connect_sync() # Auto-connect if not connected
        
        serialized = json.dumps(message) if not isinstance(message, str) else message
        return self.sync_redis.publish(channel, serialized)
    
    async def ping(self) -> bool:
        """Check if Redis is connected (async)"""
        if not self.redis:
            return False
        
        try:
            return await self.redis.ping()
        except:
            return False
    
    def ping_sync(self) -> bool:
        """Check if Redis is connected (sync)"""
        if not self.sync_redis:
            return False
        
        try:
            return self.sync_redis.ping()
        except:
            return False

redis_service = RedisService()
