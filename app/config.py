from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os
 # Ensure .env is loaded into process environment before settings are constructed
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=False)
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env.example"), override=False)


class Settings(BaseSettings):
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default=os.getenv("MODEL", "gemini-1.5-pro-latest"), validation_alias="MODEL")
    mock_mode: bool = Field(default=True, validation_alias="MOCK_MODE")
    timeout_s: float = Field(default=30.0, validation_alias="TIMEOUT_S")
    max_input_chars: int = Field(default=12000, validation_alias="MAX_INPUT_CHARS")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # pydantic-settings v2 style configuration
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
