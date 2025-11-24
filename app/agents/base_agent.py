from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.agent import AgentType
import time

class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType, model: str):
        self.agent_type = agent_type
        self.model = model
    
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
