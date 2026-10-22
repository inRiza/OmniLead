from omnilead.config import Settings

ENV_ACCOUNTS = {
    "instagram": ("instagram_user_id", "instagram_access_token"),
    "facebook": ("facebook_page_id", "facebook_page_access_token"),
    "gmail": ("gmail_user", "gmail_refresh_token"),
    "whatsapp": ("whatsapp_phone_number_id", "whatsapp_access_token"),
}
CHANNEL = {"instagram": "instagram", "facebook": "facebook", "gmail": "email", "whatsapp": "whatsapp"}


def env_accounts(settings: Settings) -> dict[str, dict]:
    out = {}
    for provider, (account_field, secret_field) in ENV_ACCOUNTS.items():
        account = str(getattr(settings, account_field) or "")
        configured = bool(account and getattr(settings, secret_field))
        out[provider] = {"provider": provider, "channel": CHANNEL[provider], "account_id": account if configured else "",
                         "configured": configured}
    return out


def env_bindings(settings: Settings) -> dict[str, str]:
    return {a["channel"]: a["account_id"] for a in env_accounts(settings).values()}


def env_statuses(settings: Settings) -> list[dict]:
    return [{"provider": a["provider"], "channel": a["channel"], "configured": True, "manual": False,
             "status": "connected" if a["configured"] else "disconnected",
             "label": f"Akun pengujian dari .env ({a['account_id']})" if a["configured"] else "",
             "expires_at": None, "scopes": [], "error": "" if a["configured"] else "Belum diisi di .env backend",
             "test_mode": True}
            for a in env_accounts(settings).values()]


def test_mode_active(settings: Settings, store) -> bool:
    return bool(settings.test_mode_enabled and store.get_settings().test_mode)
