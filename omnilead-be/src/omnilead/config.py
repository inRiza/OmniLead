from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="OMNILEAD_", extra="ignore"
    )

    secrets_dir: Path = Path(".secrets")
    db_path: Path = Path("data/omnilead.db")
    cors_origins: list[str] = ["http://localhost:3000"]

    # Instagram Graph API (resmi)
    instagram_user_id: str = ""
    instagram_access_token: str = ""
    instagram_graph_version: str = "v26.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
