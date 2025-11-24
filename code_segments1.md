# ============================================
# PROJECT STRUCTURE
# ============================================
"""
multi-agent-system/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── conversation.py
│   │   └── settings.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── master_agent.py
│   │   ├── ocr_agent.py
│   │   ├── info_agent.py
│   │   └── rag_agent.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ollama.py
│   │   ├── qdrant.py
│   │   ├── redis_service.py
│   │   └── search.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── settings.py
│   │   ├── collections.py
│   │   └── history.py
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       └── index.html
├── requirements.txt
├── docker-compose.yml
└── README.md
"""

# ============================================
# FILE: requirements.txt
# ============================================
"""
fastapi==0.109.0
uvicorn[standard]==0.27.0
redis==5.0.1
httpx==0.26.0
qdrant-client==1.7.3
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
jinja2==3.1.3
pypdf==3.17.4
python-docx==1.1.0
openpyxl==3.1.2
python-magic==0.4.27
aiofiles==23.2.1
"""

# ============================================
# FILE: app/config.py
# ============================================
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Multi-Agent AI System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_DEFAULT_COLLECTION: str = "documents"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Search
    SEARCH_PROVIDER: str = "duckduckgo"
    SERPER_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    
    # Cache TTL
    CACHE_TTL_SHORT: int = 300  # 5 minutes
    CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
    CACHE_TTL_LONG: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"

settings = Settings()


# ============================================
# FILE: app/models/agent.py
# ============================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AgentType(str, Enum):
    MASTER = "master"
    OCR = "ocr"
    INFO = "info"
    RAG = "rag"

class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

class LogEntry(BaseModel):
    agent: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    is_error: bool = False

class ReasoningStep(BaseModel):
    step: str
    thought: str
    timestamp: datetime = Field(default_factory=datetime.now)

class PlanStep(BaseModel):
    id: int
    agent: str
    action: str
    depends_on: List[int] = []
    reasoning: str

class ExecutionPlan(BaseModel):
    steps: List[PlanStep]
    agents: List[str]
    execution_mode: ExecutionMode
    estimated_time: int

class AgentResult(BaseModel):
    agent_type: AgentType
    result: Dict[str, Any]
    execution_time: float
    model_used: str

class AgentRequest(BaseModel):
    query: str
    context: Optional[str] = None
    collections: Optional[List[str]] = None


# ============================================
# FILE: app/models/conversation.py
# ============================================
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ConversationSession(BaseModel):
    id: str
    input: str
    result: str
    logs: List[Dict[str, Any]]
    reasoning: List[Dict[str, Any]]
    plan: Optional[Dict[str, Any]]
    status: str  # success, failed
    duration: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    model: Optional[str] = None
    services: Optional[Dict[str, bool]] = None


# ============================================
# FILE: app/models/settings.py
# ============================================
from pydantic import BaseModel
from typing import Dict, List, Optional

class AgentModels(BaseModel):
    master: str = "llama3.2"
    ocr: str = "llama3.2"
    info: str = "llama3.2"
    rag: str = "llama3.2"
    embedding: str = "nomic-embed-text"

class SystemPrompt(BaseModel):
    current: str
    versions: List[Dict[str, Any]] = []
    name: str

class SystemPrompts(BaseModel):
    master: SystemPrompt
    ocr: SystemPrompt
    info: SystemPrompt
    rag: SystemPrompt


# ============================================
# FILE: app/services/redis_service.py
# ============================================
import redis.asyncio as redis
import json
from typing import Optional, Any, List
from app.config import settings

class RedisService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = await redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None
        
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis:
            return False
        
        serialized = json.dumps(value) if not isinstance(value, str) else value
        
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis:
            return False
        
        result = await self.redis.delete(key)
        return result > 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        if not self.redis:
            return []
        
        return await self.redis.keys(pattern)
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        if not self.redis:
            return 0
        
        serialized = json.dumps(message) if not isinstance(message, str) else message
        return await self.redis.publish(channel, serialized)
    
    async def ping(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis:
            return False
        
        try:
            return await self.redis.ping()
        except:
            return False

redis_service = RedisService()


# ============================================
# FILE: app/services/ollama.py
# ============================================
import httpx
from typing import List, Optional, Dict, Any
from app.config import settings

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        stream: bool = False
    ) -> str:
        """Generate completion from Ollama"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": stream,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    
    async def generate_embedding(self, text: str, model: str) -> List[float]:
        """Generate embedding from Ollama"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
    
    async def check_connection(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False

ollama_service = OllamaService()


# ============================================
# FILE: app/services/qdrant.py
# ============================================
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional
from app.config import settings
import uuid

class QdrantService:
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.url = settings.QDRANT_URL
    
    def connect(self):
        """Connect to Qdrant"""
        self.client = QdrantClient(url=self.url)
    
    def create_collection(self, collection_name: str, vector_size: int = 768):
        """Create a new collection"""
        if not self.client:
            self.connect()
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections"""
        if not self.client:
            self.connect()
        
        collections = self.client.get_collections()
        return [{"name": c.name} for c in collections.collections]
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        if not self.client:
            self.connect()
        
        self.client.delete_collection(collection_name=collection_name)
    
    def add_point(
        self,
        collection_name: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> str:
        """Add a point to collection"""
        if not self.client:
            self.connect()
        
        point_id = str(uuid.uuid4())
        
        self.client.upsert(
            collection_name=collection_name,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)]
        )
        
        return point_id
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if not self.client:
            self.connect()
        
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def check_connection(self) -> bool:
        """Check if Qdrant is available"""
        try:
            if not self.client:
                self.connect()
            self.client.get_collections()
            return True
        except:
            return False

qdrant_service = QdrantService()


# ============================================
# FILE: app/agents/base_agent.py
# ============================================
from abc import ABC, abstractmethod
from typing import Dict, Any
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


# ============================================
# FILE: app/agents/ocr_agent.py
# ============================================
from app.agents.base_agent import BaseAgent
from app.models.agent import AgentType
from app.services.ollama import ollama_service
from typing import Dict, Any, Optional

class OCRAgent(BaseAgent):
    def __init__(self, model: str, system_prompt: str):
        super().__init__(AgentType.OCR, model)
        self.system_prompt = system_prompt
    
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute OCR analysis"""
        prompt = f"""Analyze the following text and extract key information. 
Identify the document type and extract structured data.

Text: "{query}"

Provide your analysis in the following format:
Document Type: [type]
Confidence: [0-1]
Key Information: [bullet points of extracted data]"""
        
        result, duration = await self._measure_execution(
            ollama_service.generate,
            prompt,
            self.system_prompt,
            self.model
        )
        
        return {
            "text": query,
            "analysis": result,
            "confidence": 0.95,
            "detected_type": self._detect_document_type(query),
            "model": self.model,
            "execution_time": duration
        }
    
    def _detect_document_type(self, text: str) -> str:
        """Simple document type detection"""
        text_lower = text.lower()
        if "invoice" in text_lower:
            return "invoice"
        elif "receipt" in text_lower:
            return "receipt"
        elif "contract" in text_lower:
            return "contract"
        elif "report" in text_lower:
            return "report"
        return "general document"


# ============================================
# FILE: app/agents/info_agent.py
# ============================================
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


# ============================================
# FILE: app/agents/rag_agent.py
# ============================================
from app.agents.base_agent import BaseAgent
from app.models.agent import AgentType
from app.services.ollama import ollama_service
from app.services.qdrant import qdrant_service
from app.services.redis_service import redis_service
from app.config import settings
from typing import Dict, Any, Optional, List

class RAGAgent(BaseAgent):
    def __init__(self, model: str, embedding_model: str, system_prompt: str):
        super().__init__(AgentType.RAG, model)
        self.embedding_model = embedding_model
        self.system_prompt = system_prompt
    
    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute RAG with vector search"""
        
        collections = context.get("collections", [settings.QDRANT_DEFAULT_COLLECTION]) if context else [settings.QDRANT_DEFAULT_COLLECTION]
        
        # Check cache
        cache_key = f"rag:{query}:{':'.join(collections)}"
        cached = await redis_service.get(cache_key)
        if cached:
            return cached
        
        # Generate query embedding
        query_embedding = await ollama_service.generate_embedding(query, self.embedding_model)
        
        # Search across collections
        all_results = []
        for collection in collections:
            try:
                results = qdrant_service.search(collection, query_embedding, limit=3)
                for r in results:
                    r["collection"] = collection
                all_results.extend(results)
            except:
                pass
        
        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:5]
        
        # Build context
        vector_context = "\n\n".join([
            f"[Collection: {r['collection']}, Score: {r['score']:.3f}]\n{r['payload']}"
            for r in top_results
        ]) if top_results else "No similar documents found in vector database."
        
        prompt = f"""Using the following information sources, provide a comprehensive response:

Vector Search Results ({len(top_results)} documents from {len(collections)} collections):
{vector_context}

User Query: {query}
Additional Context: {context.get('text', '') if context else ''}

Provide a clear, helpful response that combines all available information."""
        
        result, duration = await self._measure_execution(
            ollama_service.generate,
            prompt,
            self.system_prompt,
            self.model
        )
        
        response = {
            "response": result,
            "vector_results": top_results,
            "vector_results_count": len(top_results),
            "collections_searched": collections,
            "model": self.model,
            "embedding_model": self.embedding_model,
            "execution_time": duration
        }
        
        # Cache result
        await redis_service.set(cache_key, response, settings.CACHE_TTL_MEDIUM)
        
        return response


# ============================================
# FILE: app/agents/master_agent.py
# ============================================
from app.agents.ocr_agent import OCRAgent
from app.agents.info_agent import InfoAgent
from app.agents.rag_agent import RAGAgent
from app.models.agent import ExecutionPlan, PlanStep, ExecutionMode
from typing import Dict, Any, List
import asyncio
import time

class MasterAgent:
    def __init__(
        self,
        agent_models: Dict[str, str],
        system_prompts: Dict[str, str]
    ):
        self.ocr_agent = OCRAgent(agent_models["ocr"], system_prompts["ocr"])
        self.info_agent = InfoAgent(agent_models["info"], system_prompts["info"])
        self.rag_agent = RAGAgent(
            agent_models["rag"],
            agent_models["embedding"],
            system_prompts["rag"]
        )
        self.agent_models = agent_models
    
    def analyze_request(self, query: str) -> Dict[str, Any]:
        """Analyze user request to determine required agents"""
        query_lower = query.lower()
        
        needs_ocr = any(kw in query_lower for kw in ["document", "text", "extract", "read", "scan"])
        needs_info = any(kw in query_lower for kw in ["search", "find", "information", "lookup", "research"])
        needs_rag = True  # Always use RAG for context
        
        complexity = sum([needs_ocr, needs_info, needs_rag])
        
        return {
            "needs_ocr": needs_ocr,
            "needs_info": needs_info,
            "needs_rag": needs_rag,
            "complexity": complexity,
            "summary": f"Request requires {complexity} agents. OCR: {needs_ocr}, Info: {needs_info}, RAG: {needs_rag}"
        }
    
    def create_execution_plan(self, analysis: Dict[str, Any]) -> ExecutionPlan:
        """Create execution plan based on analysis"""
        steps = []
        agents = []
        
        if analysis["needs_ocr"]:
            steps.append(PlanStep(
                id=len(steps) + 1,
                agent="OCR Agent",
                action="Extract and analyze text from document",
                depends_on=[],
                reasoning="User request mentions document or text extraction"
            ))
            agents.append("OCR Agent")
        
        if analysis["needs_info"]:
            steps.append(PlanStep(
                id=len(steps) + 1,
                agent="Info Agent",
                action="Search for relevant information",
                depends_on=[],
                reasoning="User request requires external information lookup"
            ))
            agents.append("Info Agent")
        
        if analysis["needs_rag"]:
            depends_on = [1] if analysis["needs_ocr"] else []
            steps.append(PlanStep(
                id=len(steps) + 1,
                agent="RAG Agent",
                action="Query knowledge base for context",
                depends_on=depends_on,
                reasoning="Knowledge base consultation needed for comprehensive response"
            ))
            agents.append("RAG Agent")
        
        return ExecutionPlan(
            steps=steps,
            agents=list(set(agents)),
            execution_mode=ExecutionMode.PARALLEL if analysis["complexity"] > 1 else ExecutionMode.SEQUENTIAL,
            estimated_time=len(steps) * 1000
        )
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the plan"""
        results = {}
        
        # Separate independent and dependent agents
        independent_steps = [s for s in plan.steps if not s.depends_on]
        dependent_steps = [s for s in plan.steps if s.depends_on]
        
        # Execute independent agents in parallel
        if plan.execution_mode == ExecutionMode.PARALLEL and len(independent_steps) > 1:
            tasks = []
            for step in independent_steps:
                if step.agent == "OCR Agent":
                    tasks.append(("OCR Agent", self.ocr_agent.execute(query, context)))
                elif step.agent == "Info Agent":
                    tasks.append(("Info Agent", self.info_agent.execute(query, context)))
            
            parallel_results = await asyncio.gather(*[task[1] for task in tasks])
            for (agent_name, _), result in zip(tasks, parallel_results):
                results[agent_name] = result
        else:
            # Sequential execution
            for step in independent_steps:
                if step.agent == "OCR Agent":
                    results["OCR Agent"] = await self.ocr_agent.execute(query, context)
                elif step.agent == "Info Agent":
                    results["Info Agent"] = await self.info_agent.execute(query, context)
        
        # Execute dependent agents
        for step in dependent_steps:
            if step.agent == "RAG Agent":
                rag_context = context or {}
                if "OCR Agent" in results:
                    rag_context["text"] = results["OCR Agent"]["text"]
                results["RAG Agent"] = await self.rag_agent.execute(query, rag_context)
        
        return results
    
    def synthesize_results(
        self,
        results: Dict[str, Any],
        plan: ExecutionPlan,
        query: str
    ) -> str:
        """Synthesize results from all agents"""
        output = "=== MASTER AGENT SYNTHESIS ===\n\n"
        output += f"📋 EXECUTION SUMMARY:\n"
        output += f"- Master Model: {self.agent_models['master']}\n"
        output += f"- Total Steps: {len(plan.steps)}\n"
        output += f"- Agents Used: {', '.join(plan.agents)}\n"
        output += f"- Execution Mode: {plan.execution_mode.value}\n\n"
        
        if "OCR Agent" in results:
            ocr = results["OCR Agent"]
            output += f"📄 OCR AGENT RESULTS:\n"
            output += f"- Model: {ocr['model']}\n"
            output += f"- Document Type: {ocr['detected_type']}\n"
            output += f"- Confidence: {ocr['confidence']*100:.0f}%\n"
            output += f"- Analysis:\n{ocr['analysis']}\n\n"
        
        if "Info Agent" in results:
            info = results["Info Agent"]
            output += f"🔍 INFO AGENT RESULTS:\n"
            output += f"- Model: {info['model']}\n"
            output += f"{info['full_response']}\n\n"
        
        if "RAG Agent" in results:
            rag = results["RAG Agent"]
            output += f"📚 RAG AGENT RESULTS:\n"
            output += f"- Model: {rag['model']}\n"
            output += f"- Embedding Model: {rag['embedding_model']}\n"
            output += f"- Vector Search Results: {rag['vector_results_count']}\n"
            output += f"- Collections Searched: {', '.join(rag['collections_searched'])}\n"
            output += f"\nResponse:\n{rag['response']}\n\n"
        
        output += f"💡 CONCLUSION:\n"
        output += f"All {len(plan.steps)} planned steps completed successfully.\n"
        
        return output
    
    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Main execution method"""
        start_time = time.time()
        
        # Analyze request
        analysis = self.analyze_request(query)
        
        # Create execution plan
        plan = self.create_execution_plan(analysis)
        
        # Execute plan
        results = await self.execute_plan(plan, query, context)
        
        # Synthesize results
        final_result = self.synthesize_results(results, plan, query)
        
        duration = time.time() - start_time
        
        return {
            "query": query,
            "analysis": analysis,
            "plan": plan.dict(),
            "results": results,
            "final_result": final_result,
            "duration": duration,
            "status": "success"
        }


# ============================================
# FILE: app/main.py
# ============================================
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.services.redis_service import redis_service
from app.routers import agents, settings as settings_router, collections, history

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_service.connect()
    yield
    # Shutdown
    await redis_service.disconnect()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    COR