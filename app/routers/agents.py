from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from app.agents.master_agent import MasterAgent
from app.models.agent import AgentRequest
from app.services.redis_service import redis_service
from app.services.file_service import file_service
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Default system prompts
DEFAULT_PROMPTS = {
    "master": "You are a master orchestration agent. Analyze requests, create efficient execution plans, and coordinate specialized agents to achieve user goals.",
    "ocr": "You are an OCR analysis agent. Extract and structure information from documents accurately.",
    "info": "You are an information gathering agent. Synthesize web search results into clear, accurate summaries.",
    "rag": "You are a RAG (Retrieval-Augmented Generation) agent. Combine vector search results and knowledge base information to provide accurate, contextual responses."
}


@router.post("/execute")
async def execute_agents(
    query: str = Form(...),
    context: Optional[str] = Form(None),
    collections_str: Optional[str] = Form("[]"), # Default to empty JSON array string
    urls_str: Optional[str] = Form("[]"),       # Default to empty JSON array string
    files: List[UploadFile] = File([]),
):
    """Execute the multi-agent system"""
    try:
        collections = json.loads(collections_str)
        urls = json.loads(urls_str)

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

        # Process files and URLs
        file_contents = []
        try:
            if urls:
                logger.info(f"Processing URLs: {urls}")
                url_files = await file_service.get_files_from_urls(urls)
                file_contents.extend([file_service.read_file_content(f) for f in url_files])
                logger.info(f"Processed {len(url_files)} URLs.")
            if files:
                logger.info(f"Processing {len(files)} uploaded files.")
                uploaded_files = await file_service.get_files_from_uploads(files)
                file_contents.extend([file_service.read_file_content(f) for f in uploaded_files])
                logger.info(f"Processed {len(uploaded_files)} uploaded files.")
        except Exception as file_e:
            logger.error(f"Error during file/URL processing: {file_e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"File/URL processing error: {str(file_e)}")

        # Combine context
        final_context = context or ""
        if file_contents:
            final_context += "\n\n" + "\n\n".join(file_contents)

        # Execute
        exec_context = {}
        if collections:
            exec_context["collections"] = collections
        if final_context:
            exec_context["text"] = final_context

        result = await master.execute(query, exec_context)

        # Save to history
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "input": query,
            "context": final_context,
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
        logger.error(f"Error in execute_agents endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
