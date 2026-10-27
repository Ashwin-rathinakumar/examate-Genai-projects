from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "examate-rag"
    environment: str = "local"  # local | ci | production
    gemini_api_key: str = ""
    primary_model: str = "gemini-2.5-flash"
    fallback_model: str = "gemini-2.5-flash-lite"
    model_timeout_seconds: float = 15.0
    cost_log_path: str = "logs/cost_log.jsonl"
    primary_input_cost_per_million: float = 0.30
    primary_output_cost_per_million: float = 2.50
    fallback_input_cost_per_million: float = 0.10
    fallback_output_cost_per_million: float = 0.40


@lru_cache
def get_settings() -> Settings:
    return Settings()
