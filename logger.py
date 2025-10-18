import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log")
        ],
        force=True
    )

from celery.signals import after_setup_logger

# @after_setup_logger.connect
# def setup_celery_logging(logger, *args, **kwargs):
#     logger.handlers.clear()
#     handler = logging.StreamHandler(sys.stdout)
#     formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     logger.setLevel(logging.INFO)
#     logging.getLogger(__name__).info("gotttttt celery logger setup")
