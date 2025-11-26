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
from app.tasks import execute_master_agent_task  # Import the Celery task

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
    client_id: str = "detmar",
    query: str = Form(...),
    context: Optional[str] = Form(None),
    # Default to empty JSON array string
    collections_str: Optional[str] = Form("[]"),
    # Default to empty JSON array string
    urls_str: Optional[str] = Form("[]"),
    files: List[UploadFile] = File([]),
):
    """Execute the multi-agent system asynchronously via Celery"""
    try:
        collections = json.loads(collections_str)
        urls = json.loads(urls_str)

        # client_id = str(uuid.uuid4()) # Generate a unique client ID for WebSocket communication

        # Prepare files data for Celery task
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append({"filename": file.filename, "content": content})

        # Enqueue the task
        task = execute_master_agent_task.delay(
            query=query,
            context_str=context,  # Pass context as string
            collections_json=collections_str,  # Pass collections as JSON string
            urls_json=urls_str,  # Pass urls as JSON string
            files_data=files_data,
            client_id=client_id
        )

        return {"message": "Task accepted", "task_id": task.id, "client_id": client_id}

    except Exception as e:
        logger.error(f"Error in execute_agents endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
