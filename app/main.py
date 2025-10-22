from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI
from .routes import router
from .celery_app import celery_app
from .core.logger import setup_logging

setup_logging()

def start_worker():
    celery_app.worker_main(["worker", "--loglevel=INFO", "-P", "solo"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup logic
    thread = Thread(target=start_worker, daemon=True)
    thread.start()
    yield
    # Shutdown logic (if needed)

app = FastAPI(lifespan=lifespan)
app.include_router(router)
