from app.celery_app import celery_app
from app.agents.master_agent import MasterAgent
from app.services.redis_service import redis_service
from app.services.file_service import file_service
from app.config import settings
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import asyncio # Import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def execute_master_agent_task(
    self,
    query: str,
    context_str: Optional[str],
    collections_json: str,
    urls_json: str,
    files_data: List[Dict[str, Any]], # [{"filename": "name.pdf", "content": b"..."}]
    client_id: str
):
    try:
        # Deserialize inputs
        collections = json.loads(collections_json)
        urls = json.loads(urls_json)
        context = json.loads(context_str) if context_str else {}

        # Get agent models from Redis or use defaults
        agent_models_data = redis_service.get_sync("agent_models") # Use sync version for Celery task
        agent_models = agent_models_data or {
            "master": "qwen3-vl:4b",
            "ocr": "qwen3-vl:4b",
            "info": "qwen3-vl:4b",
            "rag": "qwen3-vl:4b",
            "embedding": "qwen3-embedding:8b"
        }

        # Get system prompts from Redis or use defaults
        system_prompts_data = redis_service.get_sync("system_prompts")
        if system_prompts_data:
            system_prompts = {
                key: prompt["current"]
                for key, prompt in system_prompts_data.items()
            }
        else:
            system_prompts = {
                "master": "You are a master orchestration agent. Analyze requests, create efficient execution plans, and coordinate specialized agents to achieve user goals.",
                "ocr": "You are an OCR analysis agent. Extract and structure information from documents accurately.",
                "info": "You are an information gathering agent. Synthesize web search results into clear, accurate summaries.",
                "rag": "You are a RAG (Retrieval-Augmented Generation) agent. Combine vector search results and knowledge base information to provide accurate, contextual responses."
            }

        # Create master agent
        master = MasterAgent(agent_models, system_prompts)

        # Process files and URLs
        file_contents = []
        if urls:
            logger.info(f"Task {self.request.id}: Processing URLs: {urls}")
            url_files = asyncio.run(file_service.get_files_from_urls(urls))
            file_contents.extend([file_service.read_file_content(f) for f in url_files])
            logger.info(f"Task {self.request.id}: Processed {len(url_files)} URLs.")
        
        # Reconstruct file objects for file_service
        processed_files_for_service = []
        for fd in files_data:
            # file_service.read_file_content expects a dict with "content" key
            processed_files_for_service.append({"filename": fd["filename"], "content": fd["content"]})

        if processed_files_for_service:
            logger.info(f"Task {self.request.id}: Processing {len(processed_files_for_service)} uploaded files.")
            # file_service.read_file_content is sync, can be called directly
            file_contents.extend([file_service.read_file_content(f) for f in processed_files_for_service])
            logger.info(f"Task {self.request.id}: Processed {len(processed_files_for_service)} uploaded files.")

        # Combine context
        final_context = context.get("text", "")
        if file_contents:
            final_context += "\n\n" + "\n\n".join(file_contents)
        
        # Add URLs to context if they exist and are not handled as files
        if urls and not file_contents: # Only add if not already processed as files
            final_context += "\n\nURLs: " + ", ".join(urls)

        # Execute
        exec_context = {}
        if collections:
            exec_context["collections"] = collections
        if final_context:
            exec_context["text"] = final_context

        result = asyncio.run(master.execute(query, exec_context))

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
        redis_service.set_sync(f"history:{session_id}", session, 2592000)

        # Publish event to client via Redis Pub/Sub
        redis_service.publish_sync(f"agent_results:{client_id}", json.dumps({
            "task_id": self.request.id,
            "status": "SUCCESS",
            "result": result
        }))

        return result

    except Exception as e:
        logger.error(f"Task {self.request.id}: Error during master agent execution: {e}", exc_info=True)
        redis_service.publish_sync(f"agent_results:{client_id}", json.dumps({
            "task_id": self.request.id,
            "status": "FAILURE",
            "error": str(e)
        }))
        raise # Re-raise to let Celery mark the task as failed
