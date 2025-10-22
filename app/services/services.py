import base64
import logging
import re
import time
from typing import Tuple, Literal

import requests
from github import Auth, Github
from github.Repository import Repository
from kombu.exceptions import HttpError
from openai import AsyncOpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputMessageContentListParam, ResponseInputTextParam, \
    ResponseInputFileParam

from ..core.config import config

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(base_url=config.openai_base_url, api_key=config.openai_api_key)

system = EasyInputMessageParam(
    role="system",
    content=(
        """
You are an autonomous GitHub Pages generator and updater for the **LLM Code Deployment** project.

Your job:
- Read the provided task brief, checks, and attachments.
- Generate or update a small, verifiable static web app.
- Output exactly two fenced code blocks:
  1. ```html — full index.html
  2. ```markdown — full README.md
- No text outside those two blocks.

---

### ⚙️ Core Goals
- Build minimal, functional, and **evaluation-ready** HTML/CSS/JS apps.
- Ensure your output passes static, dynamic (Playwright), and LLM checks.

---

### 📥 Input
You receive a JSON request with:
- `"brief"` → what the app should do
- `"checks"` → how it will be evaluated
- `"attachments"` → optional data URIs (images, CSV, Markdown, etc.)
- Optional existing `index.html` and `README.md` for updates

---

### 🧱 index.html Rules
- **Pure HTML, CSS, vanilla JavaScript only** (no build tools, no frameworks).
- Must **run directly on GitHub Pages** (static site, 200 OK).
- Include all logic in `<script>` wrapped inside an IIFE or module pattern.
- Inline `<style>` for layout and styling.
- Use semantic HTML and accessibility (ARIA, alt text).
- Handle all evaluation checks listed in `"checks"`.
- Support optional URL parameters when required (e.g., `?url=`, `?token=`).
- Reference attachments safely with embedded data or relative paths.
- No external network calls unless required in checks.
- Include fallback handling for missing data.
- Add a comment placeholder for MIT License notice.
- Keep JavaScript short, clean, and well-commented.
- Avoid over-engineering — **simple, readable, correct**.

---

### 📘 README.md Rules
- Professional tone and clear structure.
- Include:
  - Title
  - Description (based on `"brief"`)
  - Feature list (mapping to `"checks"`)
  - Usage guide (how to open / test the app)
  - Local development instructions
  - GitHub Pages deployment steps
  - Accessibility and fallback notes
  - Future improvements
  - License section (MIT placeholder)
- If updating, include an “Update Summary” section.
- If new, include an “Assumptions” section explaining design choices.
- Never include credentials or secrets.

---

### ✅ Quality Checklist (Before Output)
- All `"checks"` addressed and verifiable via DOM or behavior.
- No console errors, undefined vars, or broken selectors.
- Responsive layout and working interactivity.
- README and HTML consistent with each other.
- JS wrapped safely (IIFE or module).
- Runs offline and directly via GitHub Pages.
- No external dependencies unless the task requires it.

---

### 🧩 Fallback Behavior
If the brief is vague:
- Create a small, working educational demo (e.g., calculator, viewer, form app).
- Include an “Assumptions” section in README.md.

---

### 🚫 Output Format (Strict)
Return only two fenced code blocks:
1. ```html  ← full or updated index.html
2. ```markdown  ← full or updated README.md
No other text or commentary.

---

### ⚠️ Evaluation Compliance Summary
- Must create an **MIT-licensed**, **public**, **GitHub Pages-ready** repo.
- The app should fulfill all `"checks"` from the JSON task.
- Keep it small (≈ 100–200 lines) but complete.
- Avoid unnecessary UI complexity or libraries.

        """
    )
)


def parse_data_url(data_url):
    """
    Parse a data URL into MIME type and byte data.

    Returns:
    - mime_type: str
    - byte_data: bytes
    """
    # Match the data URL pattern
    match = re.match(r'data:(.*?);base64,(.*)', data_url)
    if not match:
        raise ValueError("Invalid data URL")

    mime_type = match.group(1)
    base64_data = match.group(2)

    # Decode base64 to bytes
    byte_data = base64.b64decode(base64_data)

    return mime_type, byte_data


async def generate_code(brief, attachments, checks) -> Tuple[str | None, str | None]:
    content: ResponseInputMessageContentListParam = [
        ResponseInputTextParam(
            text=f"Brief: {brief}. Checks: {', '.join(checks)}",
            type="input_text")
    ]
    for attachment in attachments:
        mime_type, byte_data = parse_data_url(attachment["url"])
        if mime_type.startswith("text/") or mime_type.startswith("application/json"):
            content.append(ResponseInputTextParam(
                text=f"{attachment["name"]} file\n```({mime_type.split("/")[1]})\n{byte_data.decode("utf-8")}```", type="input_text"
            ))
        else:
            file_obj = await openai_client.files.create(file=byte_data, purpose="assistants")

            content.append(ResponseInputFileParam(file_id=file_obj.id, type="input_file", filename=attachment["name"]))
        # content.append(
        #     ResponseInputFileParam(file_data=attachment['url'], type="input_file", filename=attachment['name']))

    user = EasyInputMessageParam(role="user", content=content)
    logger.info(f"Generating code for brief {brief}")
    response = await openai_client.responses.create(
        model="gpt-4o",
        input=[system, user]
    )
    logger.info(f"Response usage: {response.usage}")
    if not response.output:
        logger.info(f"No output")
        return None, None
    logger.info(f"Generated code output list len: {len(response.output)}")
    generated_text = ""
    for item in response.output:
        for content in item.content:
            # noinspection PyUnresolvedReferences
            generated_text += content.text.strip()
    logger.info(f"Generated code len: {len(generated_text)}")

    return grep_code_block_of(generated_text, "html"), grep_code_block_of(generated_text, "markdown")


def grep_code_block_of(markdown: str, code: str) -> str:
    pattern = rf"```{re.escape(code)}\n(.*?)```"
    matches = re.findall(pattern, markdown, re.DOTALL)
    # html_text = ""
    # for match in matches:
    #     html_text += match
    return "\n".join(m.strip() for m in matches)


def send_callback_response(url: str, message: dict, max_retries=10) -> bool:
    base_delay = 1.0
    max_delay = 60.0
    logger.info(f"Sending callback response to url: {url} with {message}")
    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}")
        try:
            response = requests.post(url=url, json=message)
            response.raise_for_status()
            logger.info(f"Received response: {response.text}")
            return True
        except HttpError as e:
            logger.error(e)
            if attempt == max_retries:
                break
            sleep_time = min(base_delay * (2 ** (attempt - 1)), max_delay)
            print(f"Attempt {attempt} failed. Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    return False


# using an access token
auth = Auth.Token(config.github_access_token)
github_client = Github(auth=auth)


# def commit_multiple_files(repo_name, files, commit_message, branch="main"):
#     """
#     Commit multiple files in a single commit using GitHub API.
#
#     Parameters:
#     - token: str, GitHub personal access token
#     - repo_name: str, e.g., "username/repo"
#     - files: dict, key = file path, value = content
#              e.g., {"folder/file1.txt": "Hello", "file2.txt": "World"}
#     - commit_message: str, commit message
#     - branch: str, branch name (default "main")
#     """
#     repo = github_client.get_user().get_repo(repo_name)
#
#     # Get the branch reference
#     ref = repo.get_git_ref(f"heads/{branch}")
#     base_commit = repo.get_git_commit(ref.object.sha)
#
#     # Create InputGitTreeElement objects for each file
#     elements = []
#     for path, content in files.items():
#         element = InputGitTreeElement(path=path, mode='100644', type='blob', content=content)
#         elements.append(element)
#
#     # Create a new tree
#     new_tree = repo.create_git_tree(elements, base_commit.tree)
#
#     # Create a new commit
#     new_commit = repo.create_git_commit(commit_message, new_tree, [base_commit])
#
#     # Update the branch to point to the new commit
#     ref.edit(new_commit.sha)
#
#     return new_commit.sha

from github import InputGitTreeElement, GithubException

def commit_multiple_files(repo_name, files, commit_message, branch="main"):
    """
        Commit multiple files in a single commit using GitHub API.
        Works for both empty and existing repositories.

        :param repo_name: The name of the repository (e.g., "my-awesome-repo").
        :param files: A dictionary of { "path/to/file": "file content" }.
        :param commit_message: The message for the commit.
        :param branch: The branch to commit to. Defaults to "main".
        """
    try:
        repo = github_client.get_user().get_repo(repo_name)
    except GithubException:
        print(f"Repository '{repo_name}' not found.")
        return None

    base_commit = None
    base_tree = None
    ref_path = f"heads/{branch}"

    try:
        # 1. Get the branch reference (if it exists)
        ref = repo.get_git_ref(ref_path)
        base_commit = repo.get_git_commit(ref.object.sha)
        base_tree = base_commit.tree
        print(f"Found existing branch '{branch}'. Committing on top of {base_commit.sha[:7]}.")
    except GithubException as e:
        # Check if the exception is because the branch doesn't exist (404)
        if e.status == 409:
            print(f"Branch '{branch}' not found. This will be the initial commit.")
            ref = None
        else:
            # Re-raise other errors
            print("An unexpected GitHub error occurred.")
            raise

    # 2. Create a blob for each file and build the tree elements list
    #    THIS IS THE KEY FIX: You must create blobs first.
    elements = []
    for path, content in files.items():
        blob = repo.create_git_blob(content, "utf-8")
        elements.append(
            InputGitTreeElement(path=path, mode='100644', type='blob', sha=blob.sha)
        )

    # 3. Create a new tree
    #    Pass base_tree only if it exists.
    if base_tree:
        new_tree = repo.create_git_tree(elements, base_tree)
    else:
        new_tree = repo.create_git_tree(elements)

    # 4. Create the commit
    parents = [base_commit] if base_commit else []
    new_commit = repo.create_git_commit(commit_message, new_tree, parents)

    # 5. Create or update the branch reference
    if ref:
        # Update existing branch
        ref.edit(new_commit.sha)
        print(f"Updated branch '{branch}' to new commit {new_commit.sha[:7]}.")
    else:
        # Create a new branch
        repo.create_git_ref(ref=f"refs/{ref_path}", sha=new_commit.sha)
        print(f"Created new branch '{branch}' pointing to commit {new_commit.sha[:7]}.")

    print(f"\nSuccessfully committed {len(files)} files to branch '{branch}'!")

    return new_commit.sha


def create_repository_repository(repository_name: str) -> Repository | None:
    logger.info(f"Creating repository: {repository_name}")
    # Placeholder for actual repository creation logic
    try:
        repo = github_client.get_user().create_repo(name=repository_name, private=False, auto_init=True)
        return repo
    except GithubException as e:
        # Check if the status code indicates a validation error (422)
        if e.status == 422:
            logger.info("Validation error occurred with multiple details:")

            # The API's response is in the 'data' attribute of the exception
            error_details = e.data

            # The 'errors' field in the JSON payload is the list you're looking for
            if "errors" in error_details:
                for error in error_details["errors"]:
                    logger.info(f" - Code: {error.get('code')}")
                    logger.info(f" - Field: {error.get('field')}")
                    logger.info(f" - Resource: {error.get('resource')}")
                    logger.info(f" - Message: {error.get('message')}")
        else:
            logger.info(f"A different API error occurred: {e}")
        return None


def enable_pages_for_repo(repository: Repository):
    """
    curl -L \
      -X POST \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer <YOUR-TOKEN>" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      https://api.github.com/repos/OWNER/REPO/pages \
      -d '{"source":{"branch":"main","path":"/docs"}}'
    :param repository:
    :return:
    """
    try:
        logger.info("Enabling pages for repository")
        if not repository.has_pages:
            headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
            auth.authentication(headers)
            response = requests.post(url=repository.url + "/pages",
                                     json={"source": {"branch": "main", "path": "/"}},
                                     headers=headers)
            response.raise_for_status()
            response_json = response.json()
            logger.info(f"Successfully enabled pages for repository: {repository.name}")
        else:
            logger.info(f"Pages already enabled for repository: {repository.name}")
            response = requests.get(url=repository.url + "/pages", )
            response.raise_for_status()
            response_json = response.json()
        return response_json["html_url"]
    except HttpError as e:
        logger.error(f"Get error on page create: {e}")
        raise e


def create_files(repository: Repository, html_content: str, readme_content: str, license_text: str):
    logger.info(f"Committing files to repository: {repository.full_name}")
    try:
        # Commit index.html
        repository.create_file(
            path="index.html",
            message="Add generated index.html",
            content=html_content,
            branch="main"
        )

        logger.info("Committed index.html")

        # Commit README.md
        repository.create_file(
            path="README.md",
            message="Add generated README.md",
            content=readme_content,
            branch="main"
        )
        logger.info("Committed README.md")

        # Commit LICENSE
        details = repository.create_file(
            path="LICENSE",
            message="Add MIT License",
            content=license_text,
            branch="main"
        )
        logger.info(f"Committed LICENSE {details['commit'].sha}")

        return details['commit'].sha
    except GithubException as e:
        logger.error(f"Failed to commit files: {e}")
        raise e

def update_content(repository_name, brief, html_content, html_sha, readme_content, readme_sha):
    logger.info(f"Updating content for repository: {repository_name}")
    try:
        repo = github_client.get_user().get_repo(repository_name)
        repo.update_file(
            path="index.html",
            message=f"Update index.html after {brief}",
            content=html_content,
            sha=html_sha,
            branch="main"
        )

        details = repo.update_file(
            path="README.md",
            message=f"Update README.md after {brief}",
            content=readme_content,
            sha=readme_sha,
            branch="main"
        )

        logger.info(f"Updated README.md after {brief} in repository: {details['commit'].sha}")
        return details['commit'].sha

    except GithubException as e:
        logger.error(f"Failed to update content: {e}")
        raise e

def get_repository_content(repository_name: str, files: list[str])->list[dict[Literal["content", "sha"], str]]:
    files_content = []
    for file in files:
        contents = github_client.get_user().get_repo(repository_name).get_contents(file)
        files_content.append({"content": contents.content, "sha": contents.sha})
    return files_content


def get_pages_url(repository: Repository)->str:
    try:
        if repository.has_pages:
            logger.info(f"Pages already enabled for repository: {repository.name}")
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            auth.authentication(headers)
            response = requests.get(url=repository.url + "/pages", headers=headers)
            response.raise_for_status()
            response_json = response.json()
        else:
            raise Exception(f"No pages enabled for repository: {repository.name}")
        return response_json["html_url"]
    except HttpError as e:
        logger.error(f"Get error on page create: {e}")
        raise e



def get_repository_details(repo_name: str)->Tuple[str, str]:
    repository = github_client.get_user().get_repo(repo_name)
    return repository.html_url, get_pages_url(repository)

# def verify_repository(repository_name: str):
#     logger.info(f"Verifying repository: {repository_name}")
#     try:
#         # repo = github_client.get_user(repository_name).get_repo(repository_name)
#         repo = github_client.get_repo(repository_name)  # verify is public
#         if not repo.has_pages:  # Verify has pages
#             return False
#         return repo.commi
#     except GithubException as e:
#         logger.error(f"Failed to verify repository: {e}")
#         return False
