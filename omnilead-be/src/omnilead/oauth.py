"""Server-side channel onboarding. Never return platform credentials to the UI."""

import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx

from omnilead.accounts import AccountStore, digest
from omnilead.config import Settings

PROVIDERS = ("instagram", "gmail", "whatsapp", "linkedin")
CHANNELS = {"instagram": "instagram", "gmail": "email", "whatsapp": "whatsapp", "linkedin": "linkedin"}
SCOPES = {
    "instagram": ["instagram_business_basic", "instagram_business_manage_comments", "instagram_business_manage_messages"],
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
    "linkedin": ["openid", "profile", "w_member_social"],
    "whatsapp": ["whatsapp_business_management", "whatsapp_business_messaging"],
}


class OAuthError(ValueError):
    pass


class OAuthService:
    def __init__(self, settings: Settings, accounts: AccountStore, client: httpx.Client | None = None):
        self.s, self.accounts = settings, accounts
        self.http = client or httpx.Client(timeout=25, follow_redirects=False)

    def ready(self, provider: str) -> bool:
        s = self.s
        return bool({
            "gmail": s.gmail_client_id and s.gmail_client_secret,
            "instagram": s.instagram_client_id and s.instagram_client_secret,
            "linkedin": s.linkedin_client_id and s.linkedin_client_secret,
            "whatsapp": s.meta_app_id and s.meta_app_secret and s.whatsapp_signup_config_id,
        }.get(provider))

    def redirect_uri(self, provider: str) -> str:
        return f"{self.s.frontend_url.rstrip('/')}/api/backend/auth/oauth/{provider}/callback"

    def call(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self.http.request(method, url, **kwargs)
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise OAuthError("Platform tidak dapat dihubungi. Coba kembali beberapa saat lagi.") from None
        if not isinstance(data, dict) or response.is_error or data.get("error"):
            # Provider errors often contain tokens, URLs, app secrets, or user data.
            raise OAuthError("Platform menolak akses. Periksa izin akun atau hubungkan ulang.")
        return data

    def start(self, provider: str, workspace: str, session: str) -> dict:
        if not self.ready(provider):
            raise OAuthError("Pengelola OmniLead belum mengaktifkan koneksi ini. Hubungi pengelola.")
        verifier = secrets.token_urlsafe(48)
        state = self.accounts.state(provider, workspace, session, verifier=verifier)
        if provider == "whatsapp":
            return {"mode": "embedded", "state": state, "app_id": self.s.meta_app_id,
                    "config_id": self.s.whatsapp_signup_config_id, "version": self.s.whatsapp_signup_version}
        params = {"response_type": "code", "redirect_uri": self.redirect_uri(provider), "state": state}
        if provider == "gmail":
            import base64
            params.update(client_id=self.s.gmail_client_id, scope=" ".join(SCOPES[provider]),
                          access_type="offline", prompt="consent select_account", include_granted_scopes="true",
                          code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("="),
                          code_challenge_method="S256")
            url = "https://accounts.google.com/o/oauth2/v2/auth"
        elif provider == "instagram":
            params.update(client_id=self.s.instagram_client_id, scope=",".join(SCOPES[provider]),
                          force_authentication="1", enable_fb_login="0")
            url = "https://www.instagram.com/oauth/authorize"
        else:
            params.update(client_id=self.s.linkedin_client_id, scope=" ".join(SCOPES[provider]))
            url = "https://www.linkedin.com/oauth/v2/authorization"
        return {"mode": "redirect", "url": url + "?" + urlencode(params)}

    def complete(self, provider: str, code: str, state: str, session: str, workspace: str) -> None:
        flow = self.accounts.consume_state(state, provider, session)
        if flow["workspace"] != workspace or not self.ready(provider):
            raise OAuthError("Bisnis atau konfigurasi koneksi berubah. Mulai kembali.")
        common = {"code": code, "grant_type": "authorization_code", "redirect_uri": self.redirect_uri(provider)}
        if provider == "gmail":
            data = self.call("POST", "https://oauth2.googleapis.com/token", data={
                **common, "client_id": self.s.gmail_client_id, "client_secret": self.s.gmail_client_secret,
                "code_verifier": flow["verifier"],
            })
            token = self._required(data, "access_token")
            scopes = data.get("scope", "").split()
            if not set(SCOPES[provider]).issubset(scopes):
                raise OAuthError("Izinkan membaca dan mengirim email agar Gmail dapat digunakan.")
            profile = self.call("GET", "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                                headers={"Authorization": f"Bearer {token}"})
            account = self._required(profile, "emailAddress").lower()
            old = self.accounts.connection(workspace, provider)
            refresh = data.get("refresh_token") or (old.get("refresh_token") if old and old["account_id"] == account else None)
            if not refresh:
                raise OAuthError("Google tidak memberikan akses berkelanjutan. Cabut izin lama lalu hubungkan ulang.")
            connection = {"access_token": token, "refresh_token": refresh, "account_id": account,
                          "label": account, "scopes": scopes, "expires_at": time.time() + int(data.get("expires_in", 3600))}
        elif provider == "instagram":
            data = self.call("POST", "https://api.instagram.com/oauth/access_token", data={
                **common, "client_id": self.s.instagram_client_id, "client_secret": self.s.instagram_client_secret,
            })
            if "data" in data:
                if not isinstance(data["data"], list) or len(data["data"]) != 1:
                    raise OAuthError("Instagram mengembalikan akun yang tidak jelas. Hubungkan ulang.")
                data = data["data"][0]
            short = self._required(data, "access_token")
            permissions = data.get("permissions")
            if isinstance(permissions, str):
                permissions = permissions.replace(",", " ").split()
            if not isinstance(permissions, list) or not set(SCOPES[provider]).issubset(permissions):
                raise OAuthError("Izinkan akses profil, komentar, dan pesan untuk menghubungkan Instagram.")
            long = self.call("GET", "https://graph.instagram.com/access_token", params={
                "grant_type": "ig_exchange_token", "client_secret": self.s.instagram_client_secret, "access_token": short,
            })
            token = self._required(long, "access_token")
            profile = self.call("GET", "https://graph.instagram.com/me", params={
                "fields": "user_id,username", "access_token": token,
            })
            account = self._required(profile, "user_id")
            connection = {"access_token": token, "account_id": account, "label": "@" + self._required(profile, "username"),
                          "scopes": permissions or SCOPES[provider], "expires_at": time.time() + int(long.get("expires_in", 5184000)),
                          "issued_at": time.time()}
        elif provider == "linkedin":
            data = self.call("POST", "https://www.linkedin.com/oauth/v2/accessToken", data={
                **common, "client_id": self.s.linkedin_client_id, "client_secret": self.s.linkedin_client_secret,
            })
            token = self._required(data, "access_token")
            scopes = data.get("scope", " ".join(SCOPES[provider])).replace(",", " ").split()
            if not set(SCOPES[provider]).issubset(scopes):
                raise OAuthError("Izin profil dan Share on LinkedIn belum lengkap.")
            profile = self.call("GET", "https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
            account = self._required(profile, "sub")
            connection = {"access_token": token, "account_id": account, "person_urn": "urn:li:person:" + account,
                          "label": profile.get("name") or "Akun LinkedIn", "scopes": scopes,
                          "expires_at": time.time() + int(data.get("expires_in", 5184000))}
        else:
            raise OAuthError("Koneksi tidak didukung")
        self.activate(workspace, provider, connection)

    @staticmethod
    def _required(data: dict, key: str) -> str:
        value = data.get(key)
        if not isinstance(value, (str, int)) or not str(value):
            raise OAuthError("Respons platform belum lengkap. Hubungkan kembali akun Anda.")
        return str(value)

    def activate(self, workspace: str, provider: str, connection: dict) -> None:
        self.accounts.claim_asset(provider, connection["account_id"], workspace)
        old = self.accounts.connection(workspace, provider)
        try:
            if provider == "instagram":
                subscribed = self.call("POST", f"https://graph.instagram.com/{self.s.instagram_graph_version}/me/subscribed_apps",
                          data={"subscribed_fields": "comments,messages", "access_token": connection["access_token"]})
                if subscribed.get("success") is not True:
                    raise OAuthError("Notifikasi Instagram belum aktif. Hubungkan kembali atau hubungi pengelola.")
            elif provider == "whatsapp":
                subscribed = self.call("POST", f"https://graph.facebook.com/{self.s.whatsapp_graph_version}/{connection['waba_id']}/subscribed_apps",
                          headers={"Authorization": f"Bearer {connection['access_token']}"})
                if subscribed.get("success") is not True:
                    raise OAuthError("Notifikasi WhatsApp belum aktif. Hubungkan kembali atau hubungi pengelola.")
            connection.update(status="connected", connected_at=time.time(), error="")
            self.accounts.save_connection(workspace, provider, connection)
        except Exception:
            if not old or old["account_id"] != connection["account_id"]:
                self.accounts.release_asset(provider, connection["account_id"], workspace)
            raise
        if old and old["account_id"] != connection["account_id"]:
            self.accounts.release_asset(provider, old["account_id"], workspace)

    def whatsapp_exchange(self, workspace: str, session: str, state: str, code: str) -> dict:
        flow = self.accounts.consume_state(state, "whatsapp", session)
        if flow["workspace"] != workspace:
            raise OAuthError("Bisnis berubah. Mulai kembali.")
        base = f"https://graph.facebook.com/{self.s.whatsapp_graph_version}"
        data = self.call("GET", base + "/oauth/access_token", params={
            "client_id": self.s.meta_app_id, "client_secret": self.s.meta_app_secret, "code": code,
        })
        token = self._required(data, "access_token")
        debug = self.call("GET", base + "/debug_token", params={"input_token": token},
                          headers={"Authorization": f"Bearer {self.s.meta_app_id}|{self.s.meta_app_secret}"}).get("data", {})
        if (not debug.get("is_valid") or str(debug.get("app_id")) != self.s.meta_app_id
                or not set(SCOPES["whatsapp"]).issubset(debug.get("scopes", []))):
            raise OAuthError("Izin WhatsApp belum lengkap atau token tidak sesuai aplikasi.")
        wabas = {str(target) for scope in debug.get("granular_scopes", [])
                 if scope.get("scope") == "whatsapp_business_management" for target in scope.get("target_ids", [])}
        if not wabas:
            raise OAuthError("Meta belum memberikan akun WhatsApp Business. Ulangi dan pilih bisnis yang akan dihubungkan.")
        choices = []
        for waba in sorted(wabas):
            listing = self.call("GET", f"{base}/{waba}/phone_numbers", params={
                "fields": "id,display_phone_number,verified_name,status,code_verification_status", "limit": 100,
            }, headers={"Authorization": f"Bearer {token}"})
            for phone in listing.get("data", []):
                choices.append({"id": self._required(phone, "id"), "waba_id": waba,
                                "label": phone.get("display_phone_number") or phone.get("verified_name") or "Nomor WhatsApp",
                                "registered": phone.get("status") == "CONNECTED"})
        if not choices:
            raise OAuthError("Belum ada nomor WhatsApp yang bisa dipilih. Selesaikan verifikasi nomor di Meta.")
        selection = self.accounts.state("whatsapp-select", workspace, session)
        self.accounts.save_connection(workspace, "pending-whatsapp", {
            "selection": digest(selection), "access_token": token, "choices": choices,
            "expires_at": debug.get("expires_at") or (time.time() + int(data["expires_in"]) if data.get("expires_in") else None),
        })
        return {"selection": selection, "accounts": choices}

    def whatsapp_select(self, workspace: str, session: str, selection: str, account_id: str, pin: str) -> None:
        self.accounts.consume_state(selection, "whatsapp-select", session)
        pending = self.accounts.connection(workspace, "pending-whatsapp")
        if not pending or pending["selection"] != digest(selection):
            raise OAuthError("Pilihan akun telah berakhir. Hubungkan ulang WhatsApp.")
        chosen = next((p for p in pending["choices"] if p["id"] == account_id), None)
        if not chosen:
            raise OAuthError("Nomor tidak sesuai akun yang diizinkan Meta.")
        if self.accounts.asset_workspace("whatsapp", account_id) not in (None, workspace):
            raise OAuthError("Nomor ini sudah terhubung ke bisnis lain. Putuskan koneksi sebelumnya dahulu.")
        if not chosen["registered"]:
            if len(pin) != 6 or not pin.isascii() or not pin.isdigit():
                raise OAuthError("Masukkan PIN verifikasi dua langkah WhatsApp, 6 digit.")
            # Idempotent registration; PIN remains only in this request.
            self.call("POST", f"https://graph.facebook.com/{self.s.whatsapp_graph_version}/{account_id}/register",
                      headers={"Authorization": f"Bearer {pending['access_token']}"},
                      json={"messaging_product": "whatsapp", "pin": pin})
        self.activate(workspace, "whatsapp", {
            "access_token": pending["access_token"], "account_id": account_id,
            "waba_id": chosen["waba_id"], "label": chosen["label"], "scopes": SCOPES["whatsapp"],
            "expires_at": pending["expires_at"],
        })
        self.accounts.delete(f"connection-{workspace}-pending-whatsapp")

    def connection(self, workspace: str, provider: str, *, refresh: bool = True) -> dict | None:
        data = self.accounts.connection(workspace, provider)
        if not data or data.get("status") == "reconnect_required":
            return data
        now = time.time()
        expires = data.get("expires_at")
        due = expires is not None and expires < now + 300
        ig_due = provider == "instagram" and now - data.get("issued_at", now) > 30 * 86400
        if refresh and (due or ig_due):
            expected = dict(data)
            try:
                if provider == "gmail":
                    result = self.call("POST", "https://oauth2.googleapis.com/token", data={
                        "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
                        "client_id": self.s.gmail_client_id, "client_secret": self.s.gmail_client_secret,
                    })
                elif provider == "instagram" and expires and expires > now:
                    result = self.call("GET", "https://graph.instagram.com/refresh_access_token", params={
                        "grant_type": "ig_refresh_token", "access_token": data["access_token"],
                    })
                else:
                    raise OAuthError("Akses berakhir. Hubungkan ulang akun Anda.")
                data.update(access_token=self._required(result, "access_token"),
                            expires_at=now + int(result.get("expires_in", 3600)), issued_at=now)
                data = self.accounts.update_connection(workspace, provider, expected, data)
            except OAuthError:
                if due:
                    data.update(status="reconnect_required", error="Akses akun perlu diperbarui. Klik Hubungkan ulang.")
                    data = self.accounts.update_connection(workspace, provider, expected, data)
        return data

    def disconnect(self, workspace: str, provider: str) -> None:
        data = self.accounts.connection(workspace, provider)
        # Local removal is authoritative even when provider is temporarily offline.
        self.accounts.delete(f"connection-{workspace}-{provider}")
        if provider == "whatsapp":
            self.accounts.delete(f"connection-{workspace}-pending-whatsapp")
        if data:
            self.accounts.release_asset(provider, data["account_id"], workspace)

    def mark_reconnect(self, workspace: str, provider: str) -> None:
        data = self.accounts.connection(workspace, provider)
        if data:
            expected = dict(data)
            data.update(status="reconnect_required", error="Akses akun perlu diperbarui. Klik Hubungkan ulang.")
            self.accounts.update_connection(workspace, provider, expected, data)

    def statuses(self, workspace: str) -> list[dict]:
        result = []
        for provider in PROVIDERS:
            data = self.connection(workspace, provider)
            result.append({"provider": provider, "channel": CHANNELS[provider], "configured": self.ready(provider),
                           "status": data["status"] if data else "disconnected", "label": data["label"] if data else "",
                           "expires_at": data.get("expires_at") if data else None,
                           "scopes": data.get("scopes", []) if data else [], "error": data.get("error", "") if data else ""})
        return result

    def connector_settings(self, workspace: str) -> Settings:
        # Never inherit another business's legacy .env/file credentials.
        patch = {"gmail_refresh_token": "", "gmail_user": "me", "instagram_access_token": "", "instagram_user_id": "",
                 "whatsapp_access_token": "", "whatsapp_phone_number_id": "", "linkedin_access_token": "",
                 "linkedin_person_urn": "", "linkedin_use_legacy_token": False}
        for provider in PROVIDERS:
            data = self.connection(workspace, provider)
            if not data or data.get("status") != "connected":
                continue
            if provider == "gmail":
                patch.update(gmail_refresh_token=data["refresh_token"])
            elif provider == "instagram":
                patch.update(instagram_user_id=data["account_id"], instagram_access_token=data["access_token"],
                             instagram_api_host="https://graph.instagram.com")
            elif provider == "whatsapp":
                patch.update(whatsapp_phone_number_id=data["account_id"], whatsapp_access_token=data["access_token"])
            elif provider == "linkedin":
                patch.update(linkedin_access_token=data["access_token"], linkedin_person_urn=data["person_urn"])
        return self.s.model_copy(update=patch)
