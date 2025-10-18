from threading import Thread

from fastapi import FastAPI
from routes import router
from celery_app import celery_app
from logger import setup_logging

setup_logging()

app = FastAPI()
app.include_router(router)
def start_worker():
    celery_app.worker_main(["worker", "--loglevel=INFO", "-P", "solo"])

@app.on_event("startup")
def startup_event():
    Thread(target=start_worker, daemon=True).start()

