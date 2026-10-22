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

    # API key mode demo lama (hanya berlaku jika auth_enabled=false).
    api_key: str = ""

    # Login pengguna dan OAuth. Token kanal disimpan per bisnis, bukan di browser.
    auth_enabled: bool = True
    accounts_db_path: Path = Path("data/accounts.db")
    frontend_url: str = "http://localhost:3000"
    token_encryption_key: str = ""  # Fernet; lokal dibuat di .secrets/oauth.key
    session_days: int = 7
    registration_enabled: bool = True
    test_mode_enabled: bool = False
    default_plan: str = "free"
    reset_link_log: bool = False
    # Akun demo untuk juri: dibuat dan diisi data demo saat server menyala (lihat demo.py).
    demo_email: str = ""
    demo_password: str = ""
    demo_name: str = "Bu Rina"
    demo_business: str = "Usaha Bu Rina (demo)"
    demo_samples: bool = True
    meta_app_id: str = ""
    whatsapp_signup_config_id: str = ""
    whatsapp_signup_version: str = "v25.0"
    instagram_client_id: str = ""
    instagram_client_secret: str = ""
    instagram_api_host: str = "https://graph.instagram.com"  # Instagram Login

    # Service agen (terpisah, dipanggil oleh BE)
    agent_url: str = "http://localhost:8100"
    agent_api_key: str = ""
    agent_timeout_s: float = 60.0
    # key = X-API-Key saja; oidc = tambah token identitas Google (agen tidak publik di Cloud Run)
    agent_auth: str = "key"

    # Opt-in OpenClaw runtime on the same host/container as this backend.
    browser_enabled: bool = False
    browser_headless: bool = False
    openclaw_browser_url: str = "http://127.0.0.1:18891"
    openclaw_token_file: Path = Path(".secrets/openclaw-token")
    openclaw_state_dir: Path = Path("data/openclaw")

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
    instagram_graph_version: str = "v26.0"

    # Facebook Page (Graph API + Messenger Platform). Login memakai aplikasi Meta yang sama
    # (meta_app_id/meta_app_secret); token di bawah ini hanya untuk mode lokal tanpa login.
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    facebook_graph_version: str = "v21.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
