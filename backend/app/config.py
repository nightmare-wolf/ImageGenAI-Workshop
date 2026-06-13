from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Datastore
    database_url: str = "postgresql+psycopg://ctf:ctf@db:5432/ctf"
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_recycle_seconds: int = 1800

    # Admin JWT (teams use opaque DB-backed session tokens, not JWT)
    jwt_secret: str = "dev-insecure-change-me-min-32-bytes-long!!"
    jwt_ttl_minutes: int = 240
    admin_password: str = "changeme-admin"

    # Team registration / sessions
    event_access_code: str = ""        # blank => open registration
    session_ttl_minutes: int = 480     # team token lifetime (one workshop day)

    # LLM / image backend (central API calls this; student containers never do)
    llm_mode: str = "mock"             # mock | openai
    llm_api_base: str = ""             # e.g. https://<runpod-vllm-endpoint>/v1
    llm_api_key: str = ""
    llm_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    llm_timeout_seconds: int = 60

    # CORS
    cors_origins: str = "http://localhost:8080"

    # Challenge engine
    challenges_dir: str = "challenges"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
