# Sample Celery FastAPI Project

## Overview
This project is a FastAPI web service integrated with Celery for distributed task processing. It is designed to automate code deployment and static site generation using LLMs, GitHub, and OpenAI APIs. The service exposes endpoints for queuing project creation and update tasks, which are processed asynchronously in the background.

## Features
- **FastAPI**: RESTful API for task submission and status.
- **Celery**: Background task processing with in-memory broker (for demo/local use).
- **GitHub Integration**: Create/update repositories, enable GitHub Pages, commit files.
- **OpenAI Integration**: Generate code and documentation using LLMs.
- **Custom Logging**: Centralized logging for all components.
- **Configurable Secrets**: Simple authentication for API requests.

## Setup
### Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/) or pip

### Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd sample-celery
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or
   poetry install
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
python app.py
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
*Generated on October 18, 2025.*

