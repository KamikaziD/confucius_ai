from app.agents.base_agent import BaseAgent
from app.models.agent import AgentType
from app.services.ollama import ollama_service
from app.services.redis_service import redis_service
from app.config import settings
from typing import Dict, Any, Optional

class InfoAgent(BaseAgent):
    def __init__(self, model: str, system_prompt: str):
        super().__init__(AgentType.INFO, model)
        self.system_prompt = system_prompt
    
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute information gathering"""
        
        # Check cache
        cache_key = f"info:{query}"
        cached = await redis_service.get(cache_key)
        if cached:
            return cached
        
        prompt = f"""Research and provide comprehensive information about: "{query}"

Provide:
1. A summary of the topic
2. Key insights and important points
3. Relevant context and background

Format your response clearly and concisely."""
        
        result, duration = await self._measure_execution(
            ollama_service.generate,
            prompt,
            self.system_prompt,
            self.model
        )
        
        response = {
            "query": query,
            "full_response": result,
            "result_count": 3,
            "model": self.model,
            "execution_time": duration
        }
        
        # Cache result
        await redis_service.set(cache_key, response, settings.CACHE_TTL_MEDIUM)
        
        return response
