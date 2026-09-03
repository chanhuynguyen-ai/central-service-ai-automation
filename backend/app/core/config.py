from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CentralOps AI API"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./centralops.db"

    jwt_secret: str = "change-this-local-development-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    llm_provider: str = "mock"
    llm_model: str = "llama3.2:3b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    integration_api_key: str = "centralops-local-integration-key"

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
