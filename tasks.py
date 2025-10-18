import asyncio
import logging
from time import sleep

import requests
from github import GithubException
from kombu.exceptions import HttpError

from celery_app import celery_app
from services import generate_code, send_callback_response, create_repository_repository, \
    enable_pages_for_repo, get_repository_content, create_files, commit_multiple_files, get_repository_details

logger = logging.getLogger(__name__)

MIT_LICENSE_TEXT = """MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


@celery_app.task(name="tasks.create_task")
def create_project_task(build_task: dict):
    """Process an incoming BuildTaskRequest (passed as a plain dict for Celery serialization).

    Returns a small summary payload that could be expanded later.
    """
    logger.info("Creating project task")
    logger.info(f"Build task: {build_task}")
    brief = build_task["brief"]
    attachments = build_task.get("attachments", [])
    checks = build_task.get("checks", [])

    html_generated, readme_generated = asyncio.run(generate_code(brief, attachments, checks))

    evaluation_url = build_task.get("evaluation_url")

    email = build_task.get("email")
    task = build_task.get("task")
    round_index = build_task.get("round")
    nonce = build_task.get("nonce")

    if html_generated is None or readme_generated is None:
        logger.info(f"Either html ({html_generated}) or readme ({readme_generated}) is None for task {task}")
        data = {"email": email, "task": task, "round": round_index, "nonce": nonce}
        logger.info(f"send callback response {evaluation_url}, {data}")
        send_callback_response(evaluation_url, {"email": email, "task": task, "round": round_index, "nonce": nonce})
    else:
        logger.info(f"Got code for task {task}")
        repository_name = task

        repository = create_repository_repository(repository_name)
        if repository is None:
            logger.error(f"Failed to create repository for task {task}")
            data = {"email": email, "task": task, "round": round_index, "nonce": nonce}
            logger.info(f"send callback response {evaluation_url}, {data}")
            send_callback_response(evaluation_url, {"email": email, "task": task, "round": round_index, "nonce": nonce})

        try:
            commit_sha = commit_multiple_files(repository_name,
                                               {"index.html": html_generated, "README.md": readme_generated,
                                                "LICENSE": MIT_LICENSE_TEXT},
                                               commit_message=f"first commit for the task {task}")
            pages_url = enable_pages_for_repo(repository)

            send_callback_response(
                evaluation_url,
                {
                    "email": email,
                    "task": task,
                    "round": round_index,
                    "nonce": nonce,
                    "repo_url": repository.html_url,
                    "commit_sha": commit_sha,
                    "pages_url": pages_url,
                },
            )
        except (GithubException, HttpError) as e:
            logger.error(f"GitHub exception for task {task}: {e}")
            data = {"email": email, "task": task, "round": round_index, "nonce": nonce}
            logger.info(f"send callback response {evaluation_url}, {data}")
            send_callback_response(evaluation_url, {"email": email, "task": task, "round": round_index, "nonce": nonce})

    logger.info("Finished creating project task")


@celery_app.task(name="tasks.upgrade_task")
def update_project_task(build_task: dict):
    """Process an incoming BuildTaskRequest (passed as a plain dict for Celery serialization).

    Returns a small summary payload that could be expanded later.
    """
    logger.info("Creating project task")
    logger.info(f"Build task: {build_task} ({type(build_task)})")
    brief = build_task["brief"]
    attachments = build_task.get("attachments", [])
    checks = build_task.get("checks", [])

    task = build_task.get("task")
    round_index = build_task.get("round")
    evaluation_url = build_task.get("evaluation_url")

    email = build_task.get("email")
    nonce = build_task.get("nonce")

    html_content, readme_content = get_repository_content(repository_name=task, files=["index.html", "README.md"])

    attachments.append({"name": "index.html", "url": f"data:text/html;base64,{html_content['content']}"})
    attachments.append({"name": "README.md", "url": f"data:text/markdown;base64,{readme_content['content']}"})

    update_html, update_readme = asyncio.run(generate_code(brief, attachments, checks))

    if update_html is None or update_readme is None:
        logger.info(f"Either html ({update_html}) or readme ({update_readme}) is None for task {task}")
        data = {"email": email, "task": task, "round": round_index, "nonce": nonce}
        logger.info(f"send callback response {evaluation_url}, {data}")
        send_callback_response(evaluation_url, {"email": email, "task": task, "round": round_index, "nonce": nonce})
    else:
        try:
            commit_sha = commit_multiple_files(repo_name=task, files={"index.html": update_html,
                                                         "README.md": update_readme,
                                                         "LICENSE": MIT_LICENSE_TEXT},
                                  commit_message="Updated project task"
                                  )
            repository_url, pages_url = get_repository_details(repo_name=task)
            logger.info(f"Sending callback to {evaluation_url} with repo_url: {repository_url}, pages_url: {pages_url}, commit_sha: {commit_sha}")
            send_callback_response(
                evaluation_url,
                {
                    "email": email,
                    "task": task,
                    "round": round_index,
                    "nonce": nonce,
                    "repo_url": repository_url,
                    "commit_sha": commit_sha,
                    "pages_url": pages_url,
                },
            )
        except (GithubException, HttpError) as e:
            logger.error(f"GitHub exception for task {task}: {e}")
            data = {"email": email, "task": task, "round": round_index, "nonce": nonce}
            logger.info(f"send callback response {evaluation_url}, {data}")
            send_callback_response(evaluation_url, {"email": email, "task": task, "round": round_index, "nonce": nonce})
