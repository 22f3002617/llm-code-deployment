---
title: My Docker Space
emoji: 🐳
colorFrom: blue
colorTo: green
sdk: docker
app_file: Dockerfile
pinned: false
---
# LLM Code Deployment Service

## Overview
This project is designed to automate code deployment and static site generation using LLMs, GitHub, and OpenAI APIs. The service exposes endpoints for queuing project creation and update tasks, which are processed asynchronously in the background.

## Features
- **FastAPI**: REST full API for task submission and status.
- **Celery**: Background task processing with in-memory broker (for demo/local use).
- **GitHub Integration**: Create/update repositories, enable GitHub Pages, commit files.
- **OpenAI Integration**: Generate code and documentation using LLMs.
- **Custom Logging**: Centralized logging for all components.
- **Configurable Secrets**: Simple authentication for API requests.

## Setup
### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) or pip

### Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd llm-code-deployment
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or
   uv sync
   ```

### Environment Variables
Configure your secrets and API keys in `config.py` or via environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GITHUB_TOKEN`: Your GitHub personal access token
- `SECRET_PASSWORD`: Password for authenticating API requests

## Usage
### Running the Service
Start the FastAPI app (Celery worker starts automatically in a background thread):
```bash
uvicorn app.main:app
```

### Docker
Build docker image
```bash
docker build -t "code-dev-agent"  . 
```
Run docker container
```bash
docker run -it --rm -p 7860:7860 --name code-dev-agent code-dev-agent
```

### API Endpoints
#### POST /task
Queue a new project creation or update task.
- **Request Body**: JSON matching `BuildTaskRequest` model
  - `secret`: Authentication password
  - `round`: 1 (create) or 2 (update)
  - `nonce`: Unique identifier
  - Other fields as required
- **Response**:
  - `status`: "queued" or error
  - `id`: Celery task ID
  - `nonce`: Echoed from request

## Development
- Tasks are defined in `tasks.py` and use services from `services.py`.
- Logging is configured in `logger.py`.
- Configuration is managed in `config.py`.
- For production, configure Celery with a robust broker (e.g., Redis, RabbitMQ).

## License
MIT License

---

