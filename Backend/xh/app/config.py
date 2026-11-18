from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

XH_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_env: str = "dev"
    agent_mode: Literal["template"] = "template"
    data_file: Path = XH_DIR / "app" / "data" / "mock" / "academic.json"
    var_dir: Path = XH_DIR / "var"
    adapter_timeout_seconds: float = 3.0
    wendian_mode: str = "mock"
    fenghuo_mode: str = "mock"
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 1
    agent_recursion_limit: int = 10
    max_suggestions: int = 3

    model_config = SettingsConfigDict(
        env_file=(XH_DIR / ".env",), env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def settings() -> Settings:
    current = Settings()
    current.var_dir.mkdir(parents=True, exist_ok=True)
    return current
