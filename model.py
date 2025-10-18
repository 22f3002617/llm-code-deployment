from pydantic import BaseModel, Field
from typing import List, Literal


class Attachment(BaseModel):
    name: str = Field(..., description="Attachment file name")
    url: str = Field(..., description="Attachment data URI")

class BuildTaskRequest(BaseModel):
    email: str = Field(..., description="Student email ID")
    secret: str = Field(..., description="Student-provided secret")
    task: str = Field(..., description="A unique task ID")
    round: int = Field(Literal[1, 2], description="Round index for the task")
    nonce: str = Field(..., description="Nonce to pass back to evaluation URL")
    brief: str = Field(..., description="Brief description of the task")
    checks: List[str] = Field(..., description="Evaluation checks for the task")
    evaluation_url: str = Field(..., description="URL to send repo & commit details")
    attachments: List[Attachment] = Field(default_factory=list, description="List of attachments as data URIs")



class CallBackResponse(BaseModel):
    email: str = Field(..., description="Student email ID")
    task: str = Field(..., description="Task ID")
    round: int = Field(..., description="Round index for the task")
    nonce: str = Field(..., description="Nonce to pass back to evaluation URL")
    repo_url: str = Field(..., description="URL of the generated GitHub repository")
    commit_sha: str = Field(..., description="Commit SHA of the generated code")
    pages_url: str = Field(..., description="URL of the GitHub Pages site (if applicable)")