from celery import Celery

celery_app = Celery('tasks', broker='memory://localhost//', backend="cache+memory://localhost",)
celery_app.conf.worker_hijack_root_logger = False
# Auto-discover tasks in app.tasks (explicit import can ensure registration)
try:
    from . import tasks
except Exception:
    # Avoid crashing import if tasks have issues; they will surface in logs/tests
    pass

