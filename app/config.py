from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "examate-rag"
    environment: str = "local"  # local | ci | production
    # Streaming /chat provider. Google Gemini exposes an OpenAI-compatible API.
    llm_provider: str = "openai_compat"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_fallback_model: str = ""
    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    llm_timeout_seconds: float = 15.0
    llm_max_retries: int = 0

    # Gemini /ask compatibility settings.
    gemini_api_key: str = ""
    primary_model: str = "gemini-3.8-flash"
    fallback_model: str = "gemini-3.5-flash-lite"
    model_timeout_seconds: float = 15.0

    # Usage log and paid-tier estimates in USD per million text tokens.
    cost_log_path: str = "logs/cost_log.jsonl"
    primary_input_cost_per_million: float = 0.30
    primary_output_cost_per_million: float = 2.50
    fallback_input_cost_per_million: float = 0.10
    fallback_output_cost_per_million: float = 0.40

    @model_validator(mode="after")
    def reuse_gemini_settings_for_chat(self) -> "Settings":
        """Keep existing Gemini .env files compatible with the /chat provider."""
        if not self.llm_api_key:
            self.llm_api_key = self.gemini_api_key
        if not self.llm_model:
            self.llm_model = self.primary_model
        if not self.llm_fallback_model:
            self.llm_fallback_model = self.fallback_model
        if not self.llm_fallback_base_url:
            self.llm_fallback_base_url = self.llm_base_url
        if not self.llm_fallback_api_key:
            self.llm_fallback_api_key = self.llm_api_key
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
