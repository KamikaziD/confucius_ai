# GEMINI.md

## Project Overview

This is a multi-agent AI system built with Python and FastAPI. The system is designed to handle complex queries by orchestrating multiple specialized AI agents. It uses Ollama for large language model inference, Qdrant for vector search, and Redis for caching and message passing.

The project includes a complete frontend built with HTML, CSS, and vanilla JavaScript, providing a user interface to interact with the agent system.

### Key Technologies

*   **Backend:** FastAPI, Python
*   **AI/ML:** Ollama, Qdrant
*   **Database/Cache:** Redis
*   **Frontend:** HTML, CSS, JavaScript
*   **Containerization:** Docker, Docker Compose

### Architecture

The system follows a microservices-like architecture orchestrated by a "Master Agent." The key components are:

*   **Master Agent:** Analyzes user requests and creates an execution plan, coordinating other agents.
*   **OCR Agent:** Extracts text from documents.
*   **Info Agent:** Gathers information from external sources (e.g., web search).
*   **RAG Agent:** Performs Retrieval-Augmented Generation using the Qdrant vector database.
*   **FastAPI Backend:** Exposes an API to interact with the agent system and manage settings.
*   **Redis:** Used for caching results and as a message broker for inter-agent communication.
*   **Qdrant:** Stores and searches vector embeddings of documents for the RAG agent.
*   **Frontend:** A single-page application that provides a user interface for the system.

## Building and Running

### Prerequisites

*   Python 3.11
*   Docker and Docker Compose
*   `pip` for installing Python packages

### Installation

1.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start services with Docker Compose:**
    ```bash
    docker-compose up -d
    ```

3.  **Pull required Ollama models:**
    ```bash
    ollama pull llama3.2
    ollama pull nomic-embed-text
    ```

### Running the Application

1.  **Create and configure your environment file:**
    ```bash
    cp .env.example .env
    # Edit .env with your settings if necessary
    ```

2.  **Run the FastAPI server:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

3.  **Access the application:**
    Open your browser to `http://localhost:8000`.

## Development Conventions

*   **Styling:** Python code seems to follow the PEP 8 style guide.
*   **Typing:** The Python code uses type hints extensively.
*   **Frameworks:** The backend is built with FastAPI.
*   **Testing:** There are no explicit tests in the provided code, but the `README.md` mentions that testing should be added.
*   **Dependencies:** Python dependencies are managed with a `requirements.txt` file.
*   **Containerization:** The project is fully containerized with Docker and Docker Compose for easy setup and deployment.
