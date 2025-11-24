from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.agent import AgentType
import time
from app.services.redis_service import redis_service # Import redis_service
import json # Import json
from datetime import datetime # Import datetime

class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType, model: str, client_id: Optional[str] = None):
        self.agent_type = agent_type
        self.model = model
        self.client_id = client_id # Store client_id
    
    @abstractmethod
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agent's task"""
        pass
    
    async def _measure_execution(self, func, *args, **kwargs) -> tuple[Any, float]:
        """Measure execution time"""
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        return result, duration
    
    def report_activity(self, message: str, is_error: bool = False):
        """Report agent activity to the client via Redis Pub/Sub"""
        if self.client_id:
            activity_message = {
                "type": "activity_update",
                "agent": self.agent_type.value,
                "message": message,
                "is_error": is_error,
                "timestamp": datetime.now().isoformat()
            }
            # Use publish_sync as this method might be called from sync contexts
            redis_service.publish_sync(f"agent_activity:{self.client_id}", json.dumps(activity_message))
