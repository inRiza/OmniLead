"""Accounts, opaque sessions, one-use OAuth state, and encrypted channel credentials.

SQLite for local use; Firestore for shared persistence on Cloud Run. CRM data
is stored separately per workspace. Raw session/state secrets are never stored.
"""

import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
import uuid

from cryptography.fernet import Fernet

from omnilead.config import Settings

COOKIE = "omnilead_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"{salt}:{key.hex()}"


def password_matches(password: str, stored: str) -> bool:
    return hmac.compare_digest(hash_password(password, stored.split(":", 1)[0]), stored)


class AccountStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.RLock()
        self.remote = None
        if settings.store == "firestore":
            from google.cloud import firestore
            self.firestore_client = firestore.Client(project=settings.firestore_project or None)
            self.remote = self.firestore_client.collection("accounts")
        else:
            settings.accounts_db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(settings.accounts_db_path, check_same_thread=False)
            self.db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            self.db.commit()
        key = settings.token_encryption_key
        if not key:
            if settings.store == "firestore" or settings.frontend_url.startswith("https://"):
                raise RuntimeError("OMNILEAD_TOKEN_ENCRYPTION_KEY wajib diisi untuk deployment")
            key_path = settings.secrets_dir / "oauth.key"
            key_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with key_path.open("xb") as f:
                    f.write(Fernet.generate_key())
            except FileExistsError:
                pass
            key = key_path.read_text().strip()
        self.cipher = Fernet(key.encode())

    def get(self, key: str) -> dict | None:
        if self.remote is not None:
            snap = self.remote.document(key).get()
            return snap.to_dict() if snap.exists else None
        with self.lock:
            row = self.db.execute("SELECT data FROM records WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, data: dict, *, create: bool = False) -> None:
        if self.remote is not None:
            ref = self.remote.document(key)
            if create:
                from google.api_core.exceptions import AlreadyExists
                try:
                    ref.create(data)
                except AlreadyExists:
                    raise ValueError("Data sudah terdaftar") from None
            else:
                ref.set(data)
            return
        with self.lock:
            try:
                self.db.execute(
                    "INSERT INTO records VALUES (?,?)" if create else "INSERT OR REPLACE INTO records VALUES (?,?)",
                    (key, json.dumps(data)),
                )
                self.db.commit()
            except sqlite3.IntegrityError:
                raise ValueError("Data sudah terdaftar") from None

    def delete(self, key: str) -> None:
        if self.remote is not None:
            self.remote.document(key).delete()
        else:
            with self.lock:
                self.db.execute("DELETE FROM records WHERE id=?", (key,))
                self.db.commit()

    def take(self, key: str) -> dict | None:
        """Atomically consume a state/nonce, including across Cloud Run instances."""
        if self.remote is not None:
            from google.cloud import firestore
            ref = self.remote.document(key)
            @firestore.transactional
            def consume(tx):
                snap = ref.get(transaction=tx)
                if snap.exists:
                    tx.delete(ref)
                    return snap.to_dict()
                return None
            return consume(self.firestore_client.transaction())
        with self.lock:
            data = self.get(key)
            self.delete(key)
            return data

    @staticmethod
    def spaces(user: dict) -> list[dict]:
        return user.get("workspaces") or [{"id": user["workspace_id"], "name": user["business"]}]

    def register(self, email: str, password: str, name: str, business: str = "Pribadi") -> dict:
        user = {"id": uuid.uuid4().hex, "workspace_id": uuid.uuid4().hex,
                "email": email, "name": name, "business": business,
                "password": hash_password(password)}
        user["workspaces"] = [{"id": user["workspace_id"], "name": business}]
        self.put("user-" + digest(email), user, create=True)
        return user

    def session(self, user: dict) -> str:
        token = secrets.token_urlsafe(32)
        self.put("session-" + digest(token), {
            "user_key": "user-" + digest(user["email"]),
            "workspace_id": user["workspace_id"],
            "expires": time.time() + self.settings.session_days * 86400,
        })
        return token

    def user_for_session(self, token: str) -> dict | None:
        data = self.get("session-" + digest(token)) if token else None
        if not data or data["expires"] <= time.time():
            return None
        user = self.get(data["user_key"])
        if not user:
            return None
        spaces = self.spaces(user)
        active = next((w for w in spaces if w["id"] == data.get("workspace_id", user["workspace_id"])), None)
        if not active:
            return None
        return {**user, "workspace_id": active["id"], "business": active["name"], "workspaces": spaces}

    def mutate_user(self, email: str, change) -> dict:
        key = "user-" + digest(email)
        if self.remote is not None:
            from google.cloud import firestore
            ref = self.remote.document(key)
            @firestore.transactional
            def update(tx):
                user = ref.get(transaction=tx).to_dict()
                result = change(user)
                tx.set(ref, user)
                return result
            return update(self.firestore_client.transaction())
        with self.lock:
            user = self.get(key)
            result = change(user)
            self.put(key, user)
            return result

    def add_workspace(self, email: str, name: str) -> dict:
        workspace = {"id": uuid.uuid4().hex, "name": name}
        def add(user):
            spaces = self.spaces(user)
            if len(spaces) >= 50:
                raise ValueError("Maksimal 50 ruang kerja per akun")
            user["workspaces"] = [*spaces, workspace]
            return workspace
        return self.mutate_user(email, add)

    def select_workspace(self, session: str, workspace: str) -> None:
        key = "session-" + digest(session)
        with self.lock:
            data = self.get(key)
            user = self.user_for_session(session)
            if not data or not user or not any(w["id"] == workspace for w in self.spaces(user)):
                raise ValueError("Anda tidak memiliki akses ke bisnis ini")
            data["workspace_id"] = workspace
            self.put(key, data)

    def update_profile(self, email: str, workspace: str, name: str, business: str) -> None:
        def update(user):
            user["name"] = name
            user["workspaces"] = [{**w, "name": business} if w["id"] == workspace else w for w in self.spaces(user)]
            if workspace == user["workspace_id"]:
                user["business"] = business
        self.mutate_user(email, update)

    def save_connection(self, workspace: str, provider: str, data: dict) -> None:
        # The binding as well as the credentials is authenticated by Fernet.
        envelope = {"workspace": workspace, "provider": provider, "data": data}
        self.put(f"connection-{workspace}-{provider}", {
            "sealed": self.cipher.encrypt(json.dumps(envelope).encode()).decode(),
        })

    def connection(self, workspace: str, provider: str) -> dict | None:
        row = self.get(f"connection-{workspace}-{provider}")
        if not row:
            return None
        envelope = json.loads(self.cipher.decrypt(row["sealed"].encode()))
        if envelope["workspace"] != workspace or envelope["provider"] != provider:
            raise ValueError("Kredensial tidak sesuai bisnis")
        return envelope["data"]

    def update_connection(self, workspace: str, provider: str, expected: dict, updated: dict) -> dict | None:
        """Compare-and-swap: refresh cannot revive a disconnected/replaced grant."""
        key = f"connection-{workspace}-{provider}"
        def replacement(row):
            if not row:
                return None, None
            envelope = json.loads(self.cipher.decrypt(row["sealed"].encode()))
            if envelope["workspace"] != workspace or envelope["provider"] != provider:
                raise ValueError("Kredensial tidak sesuai bisnis")
            if envelope["data"] != expected:
                return None, envelope["data"]
            envelope["data"] = updated
            return {"sealed": self.cipher.encrypt(json.dumps(envelope).encode()).decode()}, updated
        if self.remote is not None:
            from google.cloud import firestore
            ref = self.remote.document(key)
            @firestore.transactional
            def update(tx):
                snap = ref.get(transaction=tx)
                row, result = replacement(snap.to_dict() if snap.exists else None)
                if row:
                    tx.set(ref, row)
                return result
            return update(self.firestore_client.transaction())
        with self.lock:
            row, result = replacement(self.get(key))
            if row:
                self.put(key, row)
            return result

    def claim_asset(self, provider: str, account_id: str, workspace: str) -> None:
        key = "asset-" + digest(f"{provider}:{account_id}")
        try:
            self.put(key, {"workspace": workspace}, create=True)
        except ValueError:
            if self.get(key) != {"workspace": workspace}:
                raise ValueError("Akun ini sudah terhubung ke bisnis lain. Putuskan koneksi sebelumnya dahulu.") from None

    def asset_workspace(self, provider: str, account_id: str) -> str | None:
        row = self.get("asset-" + digest(f"{provider}:{account_id}"))
        return row["workspace"] if row else None

    def release_asset(self, provider: str, account_id: str, workspace: str) -> None:
        if self.asset_workspace(provider, account_id) == workspace:
            self.delete("asset-" + digest(f"{provider}:{account_id}"))

    def workspace_ids(self) -> list[str]:
        if self.remote is not None:
            records = ((d.id, d.to_dict()) for d in self.remote.stream())
        else:
            with self.lock:
                rows = self.db.execute("SELECT id,data FROM records WHERE id LIKE 'user-%'").fetchall()
            records = ((key, json.loads(data)) for key, data in rows)
        return list({workspace["id"] for key, data in records if key.startswith("user-") for workspace in self.spaces(data)})

    def state(self, provider: str, workspace: str, session: str, **extra) -> str:
        value = secrets.token_urlsafe(32)
        self.put("state-" + digest(value), {
            "provider": provider, "workspace": workspace, "session": digest(session),
            "expires": time.time() + 600, **extra,
        })
        return value

    def consume_state(self, value: str, provider: str, session: str) -> dict:
        data = self.take("state-" + digest(value))
        if (not data or data["expires"] < time.time() or data["provider"] != provider
                or not hmac.compare_digest(data["session"], digest(session))):
            raise ValueError("Sesi penghubungan berakhir atau tidak valid. Coba hubungkan kembali.")
        return data
