from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PC_DIR = Path(__file__).resolve().parent.parent  # Backend/pc
REPO_DIR = PC_DIR.parent.parent  # 仓库根


class Settings(BaseSettings):
    app_env: str = "dev"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.0
    llm_client_name: str = "HeartEase-Guardian/0.1"
    llm_session_header: str = ""
    llm_session_id: str = ""

    data_dir: Path = REPO_DIR / "data"
    mock_dir: Path = REPO_DIR / "data" / "mock"
    data_mode: str = "auto"  # auto | real | mock
    identity_mode: str = "mock"  # mock | off
    default_user: str = ""
    resume_llm_polish: str = "off"  # off | on
    store_backend: str = "json"  # json | mysql
    database_url: str = ""
    db_pool_size: int = 5
    log_level: str = "INFO"
    log_file: str = "var/logs/app.log"  # 相对 Backend/pc，留空则只打 stdout
    var_dir: Path = PC_DIR / "var"
    max_suggestions: int = 8
    max_upload_mb: int = 8

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", PC_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def settings() -> Settings:
    s = Settings()
    s.var_dir.mkdir(parents=True, exist_ok=True)
    return s
