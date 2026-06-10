"""Application settings, loaded from the environment (see .env.example)."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    secret_key: str = "change-me"
    server_secret: str = "change-me-hmac"
    jwt_ttl_minutes: int = 240

    database_url: str = "postgresql+psycopg://ctf:ctf@postgres:5432/ctf"
    redis_url: str = "redis://redis:6379/0"

    imagegen_mode: str = "mock"            # mock | runpod
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""
    imagegen_timeout_seconds: int = 30
    imagegen_steps: int = 4

    rate_limit_generate_per_min: int = 30
    rate_limit_submit_per_min: int = 10
    max_concurrent_generates: int = 16
    upload_max_bytes: int = 4_000_000

    loki_url: str = "http://loki:3100"
    log_level: str = "INFO"

    challenges_dir: str = "challenges"


@lru_cache
def get_settings() -> Settings:
    return Settings()
