from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="OMNILEAD_", extra="ignore"
    )

    # sqlite (dev/tes) atau firestore (produksi)
    store: str = "sqlite"
    firestore_project: str = ""
    secrets_dir: Path = Path(".secrets")
    db_path: Path = Path("data/omnilead.db")
    cors_origins: list[str] = ["http://localhost:3000"]

    # Autentikasi REST untuk FE. Kosong = mati (hanya dev).
    api_key: str = ""

    # Service agen (terpisah, dipanggil oleh BE)
    agent_url: str = "http://localhost:8100"
    agent_api_key: str = ""
    agent_timeout_s: float = 60.0

    # Cloud Scheduler: token bersama (Authorization: Bearer) atau OIDC bila audience diisi.
    scheduler_token: str = ""
    scheduler_oidc_audience: str = ""

    # Meta (WhatsApp Cloud API + Instagram webhook)
    meta_app_secret: str = ""
    meta_verify_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_graph_version: str = "v21.0"

    # Gmail API (OAuth refresh token dari mode Testing)
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_user: str = "me"
    gmail_pubsub_topic: str = ""
    gmail_push_token: str = ""

    # Instagram Graph API (resmi)
    instagram_user_id: str = ""
    instagram_access_token: str = ""
    instagram_graph_version: str = "v21.0"

    # LinkedIn Share on LinkedIn (resmi)
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/auth/linkedin/callback"
    linkedin_api_version: str = "202609"

    @property
    def linkedin_token_path(self) -> Path:
        return self.secrets_dir / "linkedin_token.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
