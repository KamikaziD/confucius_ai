from fastapi import APIRouter, HTTPException
from app.agents.master_agent import MasterAgent
from app.models.agent import AgentRequest
from app.services.redis_service import redis_service
from typing import Dict, Any
import uuid
from datetime import datetime

router = APIRouter()

# Default system prompts
DEFAULT_PROMPTS = {
    "master": "You are a master orchestration agent. Analyze requests, create efficient execution plans, and coordinate specialized agents to achieve user goals.",
    "ocr": "You are an OCR analysis agent. Extract and structure information from documents accurately.",
    "info": "You are an information gathering agent. Synthesize web search results into clear, accurate summaries.",
    "rag": "You are a RAG (Retrieval-Augmented Generation) agent. Combine vector search results and knowledge base information to provide accurate, contextual responses."
}


@router.post("/execute")
async def execute_agents(request: AgentRequest):
    """Execute the multi-agent system"""
    try:
        # Get agent models from Redis or use defaults
        agent_models_data = await redis_service.get("agent_models")
        agent_models = agent_models_data or {
            "master": "qwen3-vl:4b",
            "ocr": "qwen3-vl:4b",
            "info": "qwen3-vl:4b",
            "rag": "qwen3-vl:4b",
            "embedding": "qwen3-embedding:8b"
        }

        # Get system prompts from Redis or use defaults
        system_prompts_data = await redis_service.get("system_prompts")
        if system_prompts_data:
            system_prompts = {
                key: prompt["current"]
                for key, prompt in system_prompts_data.items()
            }
        else:
            system_prompts = DEFAULT_PROMPTS

        # Create master agent
        master = MasterAgent(agent_models, system_prompts)

        # Execute
        context = {}
        if request.collections:
            context["collections"] = request.collections
        if request.context:
            context["text"] = request.context

        result = await master.execute(request.query, context if context else None)

        # Save to history
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "input": request.query,
            "result": result["final_result"],
            "plan": result["plan"],
            "status": result["status"],
            "duration": result["duration"],
            "timestamp": datetime.now().isoformat(),
            "model": agent_models["master"]
        }

        # 30 days
        await redis_service.set(f"history:{session_id}", session, 2592000)

        # Publish event
        await redis_service.publish("agent_events", {
            "type": "execution_complete",
            "session_id": session_id,
            "duration": result["duration"]
        })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
