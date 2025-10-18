import logging

from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import config
from model import BuildTaskRequest
from tasks import create_project_task, update_project_task

router = APIRouter()

@router.post("/task")
async def task(build_task: BuildTaskRequest) -> JSONResponse:
    try:
        # Secret validation
        if config.secret_password != build_task.secret:
            return JSONResponse({"status": "invalid"}, 401)

        # Convert to dict for Celery serialization
        payload = build_task.model_dump()
        logging.info(payload)
        result: AsyncResult
        if build_task.round == 1:
            result = create_project_task.delay(payload)
        elif build_task.round == 2:
            result = update_project_task.delay(payload)
        else:
            return JSONResponse({"status": "invalid round"}, 400)

        return JSONResponse({
            "status": "queued",
            "id": result.id,
            "nonce": build_task.nonce,
        }, 200)
    except Exception as e:
        logging.error(e)
        return JSONResponse({
            "status": "error",
            "error": "internal server error",
        }, 500)
