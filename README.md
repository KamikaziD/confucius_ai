# Multi-Agent AI System - FastAPI Implementation

Complete FastAPI implementation with Redis, Qdrant, Ollama integration and HTML frontend.

## Features

✅ Multi-agent orchestration (Master, OCR, Info, RAG)
✅ Ollama integration with per-agent model selection
✅ Qdrant vector database with document upload
✅ Redis caching and pub/sub events
✅ Web search capabilities
✅ System prompt editor with version control
✅ Conversation history with persistence
✅ Collection manager with file upload
✅ Real-time agent activity tracking
✅ Parallel and sequential execution modes
✅ Complete HTML/CSS/JS frontend

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Services

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or manually:
# Redis
docker run -p 6379:6379 redis:7-alpine

# Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Ollama
ollama serve
```

### 3. Pull Required Models

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run Application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Access Application

Open browser to: http://localhost:8000

## Project Structure

```
app/
├── main.py              # FastAPI application
├── config.py            # Configuration
├── models/              # Pydantic models
├── agents/              # Agent implementations
├── services/            # External services
├── routers/             # API routes
├── static/              # CSS/JS files
└── templates/           # HTML templates
```

## API Endpoints

### Agents
- `POST /api/agents/execute` - Execute multi-agent system

### Settings
- `GET /api/settings/models` - Get available models
- `GET/POST /api/settings/agent-models` - Agent model config
- `GET/POST /api/settings/system-prompts` - System prompts
- `GET /api/settings/connections` - Check connections
- `GET/POST /api/settings/selected-collections` - Collections

### Collections
- `GET /api/collections/` - List collections
- `POST /api/collections/create` - Create collection
- `DELETE /api/collections/{name}` - Delete collection
- `POST /api/collections/upload` - Upload documents

### History
- `GET /api/history/` - Get conversation history
- `GET /api/history/{session_id}` - Get specific session
- `DELETE /api/history/{session_id}` - Delete session
- `DELETE /api/history/` - Clear all history

## Configuration

Edit `.env` file or set environment variables:

```bash
OLLAMA_URL=http://localhost:11434
QDRANT_URL=http://localhost:6333
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Usage Examples

### Execute Query

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/agents/execute",
        json={
            "query": "Analyze this invoice document",
            "collections": ["documents"]
        }
    )
    print(response.json())
```

### Upload Documents

```python
files = [("files", open("document.pdf", "rb"))]
data = {"collection": "documents"}

response = requests.post(
    "http://localhost:8000/api/collections/upload",
    files=files,
    data=data
)
```

## Performance

- Parallel agent execution for independent tasks
- Redis caching for repeated queries
- Async/await throughout for non-blocking I/O
- Connection pooling for all external services

## Security

- CORS enabled (configure for production)
- No authentication (add as needed)
- Validate all inputs
- Sanitize file uploads

## Troubleshooting

**Ollama not connecting:**
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_URL in .env

**Qdrant errors:**
- Verify Qdrant is running on port 6333
- Check collection exists before searching

**Redis connection failed:**
- Ensure Redis is running on port 6379
- Check REDIS_HOST and REDIS_PORT

## License

MIT
