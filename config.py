from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    cur_dir: Path = Path(__file__).parent
    app_name: str = 'llm-code-deployment'
    debug: bool = Field(False, alias="DEBUG_MODE", description="Enable debug mode")
    secret_password: str = Field(..., alias="SECRET_PASSWORD", description="Secret password for validating requests")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY", description="OpenAI API key")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL", description="OpenAI API endpoint")

    github_access_token: str = Field(..., alias="GITHUB_ACCESS_TOKEN", description="GitHub access token")

    model_config = SettingsConfigDict(env_file=cur_dir / (".env.dev" if debug else ".env"), extra='ignore')  # Tell Pydantic to load .env

config = AppConfig()


if __name__ == '__main__':
    print(config.model_dump_json(indent=2))