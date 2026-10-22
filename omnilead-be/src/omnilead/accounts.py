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
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from omnilead.config import Settings

COOKIE = "omnilead_session"
ROLES = ("owner", "admin", "staff")
MANAGERS = ("owner", "admin")
PLAN_LIMITS = {"free": 1, "pro": 3, "business": 10}
MAX_WORKSPACES = 50
MAX_MEMBERS = 50
PROFILE_FIELDS = ("category", "description", "service_area", "hours")
RESET_SECONDS = 1800
VERIFY_SECONDS = 86400


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    def mutate(self, key: str, change):
        if self.remote is not None:
            from google.cloud import firestore
            ref = self.remote.document(key)
            @firestore.transactional
            def update(tx):
                snap = ref.get(transaction=tx)
                data, result = change(snap.to_dict() if snap.exists else None)
                if data is not None:
                    tx.set(ref, data)
                return result
            return update(self.firestore_client.transaction())
        with self.lock:
            data, result = change(self.get(key))
            if data is not None:
                self.put(key, data)
            return result

    @staticmethod
    def spaces(user: dict) -> list[dict]:
        spaces = user["workspaces"] if "workspaces" in user else [{"id": user["workspace_id"], "name": user["business"]}]
        return [{**w, "role": w.get("role", "owner")} for w in spaces]

    def plan(self, user: dict) -> str:
        if user.get("plan") in PLAN_LIMITS:
            return user["plan"]
        return self.settings.default_plan if self.settings.default_plan in PLAN_LIMITS else "free"

    def workspace_limit(self, user: dict) -> int:
        return min(PLAN_LIMITS[self.plan(user)], MAX_WORKSPACES)

    @classmethod
    def owned(cls, user: dict) -> int:
        return sum(1 for w in cls.spaces(user) if w["role"] == "owner")

    def set_plan(self, email: str, plan: str) -> None:
        if plan not in PLAN_LIMITS:
            raise ValueError("Paket tidak dikenal")
        self.mutate_user(email, lambda user: user.update(plan=plan))

    @staticmethod
    def _record(workspace: str, name: str, owner: str, profile: dict | None = None) -> dict:
        return {"id": workspace, "name": name, "owner_email": owner, "archived": False,
                "profile": dict(profile or {}),
                "members": [{"email": owner, "role": "owner", "invited_at": now_iso(), "accepted": True}]}

    def register(self, email: str, password: str, name: str, business: str = "Pribadi") -> dict:
        workspace = {"id": uuid.uuid4().hex, "name": business, "role": "owner"}
        user = {"id": uuid.uuid4().hex, "workspace_id": workspace["id"],
                "email": email, "name": name, "business": business,
                "password": hash_password(password), "plan": self.plan({}),
                "email_verified": False, "session_version": 1, "workspaces": [workspace]}
        self.put("user-" + digest(email), user, create=True)
        self.put("workspace-" + workspace["id"], self._record(workspace["id"], business, email))
        invite = self.take("invite-" + digest(email))
        for workspace_id in (invite or {}).get("workspaces", []):
            entry = self._accept(workspace_id, email)
            if entry:
                self._add_entry(email, entry)
        return self.get("user-" + digest(email))

    def _accept(self, workspace: str, email: str) -> dict | None:
        def change(record):
            member = next((m for m in (record or {}).get("members", []) if m["email"] == email), None)
            if not record or record.get("archived") or not member:
                return None, None
            member["accepted"] = True
            return record, {"id": workspace, "name": record["name"], "role": member["role"]}
        return self.mutate("workspace-" + workspace, change)

    def workspace(self, workspace: str, email: str | None = None) -> dict | None:
        key = "workspace-" + workspace
        record = self.get(key)
        if record or not email:
            return record
        user = self.get("user-" + digest(email))
        entry = next((w for w in self.spaces(user) if w["id"] == workspace), None) if user else None
        if not entry or entry["role"] != "owner":
            return None
        try:
            self.put(key, self._record(workspace, entry["name"], email), create=True)
        except ValueError:
            pass
        return self.get(key)

    def role_for(self, email: str, workspace: str) -> str | None:
        record = self.workspace(workspace, email)
        if not record or record.get("archived"):
            return None
        return next((m["role"] for m in record["members"] if m["email"] == email and m["accepted"]), None)

    def workspace_profile(self, workspace: str) -> dict:
        record = self.get("workspace-" + workspace)
        return dict(record.get("profile") or {}) if record and not record.get("archived") else {}

    def _set_entry(self, email: str, workspace: str, **fields) -> None:
        if not self.get("user-" + digest(email)):
            return
        def change(user):
            user["workspaces"] = [{**w, **fields} if w["id"] == workspace else w for w in self.spaces(user)]
            if "name" in fields and user["workspace_id"] == workspace:
                user["business"] = fields["name"]
        self.mutate_user(email, change)

    def _add_entry(self, email: str, entry: dict) -> None:
        def change(user):
            spaces = self.spaces(user)
            if not any(w["id"] == entry["id"] for w in spaces):
                user["workspaces"] = [*spaces, entry]
        self.mutate_user(email, change)

    def _drop_entry(self, email: str, workspace: str) -> None:
        if not self.get("user-" + digest(email)):
            return
        def change(user):
            remaining = [w for w in self.spaces(user) if w["id"] != workspace]
            if not remaining:
                remaining = [{"id": uuid.uuid4().hex, "name": "Pribadi", "role": "owner"}]
            user["workspaces"] = remaining
            if not any(w["id"] == user["workspace_id"] for w in remaining):
                user["workspace_id"], user["business"] = remaining[0]["id"], remaining[0]["name"]
        self.mutate_user(email, change)

    def _forget_invite(self, email: str, workspace: str) -> None:
        def change(invite):
            if not invite:
                return None, None
            invite["workspaces"] = [w for w in invite["workspaces"] if w != workspace]
            return invite, invite["workspaces"]
        if self.mutate("invite-" + digest(email), change) == []:
            self.delete("invite-" + digest(email))

    def session(self, user: dict) -> str:
        token = secrets.token_urlsafe(32)
        self.put("session-" + digest(token), {
            "user_key": "user-" + digest(user["email"]),
            "user_id": user["id"],
            "version": user.get("session_version", 0),
            "workspace_id": user["workspace_id"],
            "expires": time.time() + self.settings.session_days * 86400,
        })
        return token

    def user_for_session(self, token: str) -> dict | None:
        key = "session-" + digest(token) if token else ""
        data = self.get(key) if token else None
        now = time.time()
        if not data:
            return None
        if data["expires"] <= now:
            self.delete(key)
            return None
        user = self.get(data["user_key"])
        if (not user or data.get("user_id", user["id"]) != user["id"]
                or data.get("version", 0) != user.get("session_version", 0)):
            self.delete(key)
            return None
        spaces = self.spaces(user)
        wanted = data.get("workspace_id", user["workspace_id"])
        active = (next((w for w in spaces if w["id"] == wanted), None)
                  or next((w for w in spaces if w["id"] == user["workspace_id"]), None)
                  or (spaces[0] if spaces else None))
        if not active:
            return None
        lifetime = self.settings.session_days * 86400
        changed = active["id"] != wanted
        if data["expires"] - now < lifetime / 2:
            data["expires"] = now + lifetime
            changed = True
        if changed:
            data["workspace_id"] = active["id"]
            self.put(key, data)
        return {**user, "workspace_id": active["id"], "business": active["name"], "workspaces": spaces,
                "session_expires": data["expires"]}

    def mutate_user(self, email: str, change) -> dict:
        def apply(user):
            return user, change(user)
        return self.mutate("user-" + digest(email), apply)

    def add_workspace(self, email: str, name: str, profile: dict | None = None) -> dict:
        workspace = {"id": uuid.uuid4().hex, "name": name, "role": "owner"}
        def add(user):
            spaces = self.spaces(user)
            if len(spaces) >= MAX_WORKSPACES:
                raise ValueError("Maksimal 50 ruang kerja per akun")
            limit = self.workspace_limit(user)
            if self.owned(user) >= limit:
                raise ValueError(f"Paket {self.plan(user).capitalize()} hanya dapat memiliki {limit} bisnis. "
                                 "Tingkatkan paket untuk menambah bisnis.")
            user["workspaces"] = [*spaces, workspace]
        self.mutate_user(email, add)
        record = self._record(workspace["id"], name, email, profile)
        self.put("workspace-" + workspace["id"], record)
        return {**workspace, "profile": record["profile"]}

    def update_workspace(self, workspace: str, name: str | None = None, profile: dict | None = None) -> dict:
        def change(record):
            if not record or record.get("archived"):
                raise LookupError("Bisnis tidak ditemukan")
            if name is not None:
                record["name"] = name
            if profile is not None:
                record["profile"] = {**(record.get("profile") or {}), **profile}
            return record, record
        record = self.mutate("workspace-" + workspace, change)
        if name is not None:
            for member in record["members"]:
                if member["accepted"]:
                    self._set_entry(member["email"], workspace, name=name)
        return record

    def archive_workspace(self, workspace: str) -> None:
        def change(record):
            if not record or record.get("archived"):
                return None, []
            record["archived"], record["archived_at"] = True, now_iso()
            return record, record["members"]
        for member in self.mutate("workspace-" + workspace, change):
            if member["accepted"]:
                self._drop_entry(member["email"], workspace)
            else:
                self._forget_invite(member["email"], workspace)

    def members(self, workspace: str) -> list[dict]:
        record = self.get("workspace-" + workspace) or {"members": []}
        result = []
        for member in record["members"]:
            user = self.get("user-" + digest(member["email"]))
            result.append({**member, "name": user["name"] if user else None})
        return result

    def invite(self, workspace: str, email: str, role: str) -> dict:
        if role not in ROLES[1:]:
            raise ValueError("Peran tidak dikenal")
        registered = self.get("user-" + digest(email)) is not None
        def change(record):
            if not record or record.get("archived"):
                raise LookupError("Bisnis tidak ditemukan")
            if any(m["email"] == email for m in record["members"]):
                raise ValueError("Email ini sudah menjadi anggota bisnis")
            if len(record["members"]) >= MAX_MEMBERS:
                raise ValueError("Maksimal 50 anggota per bisnis")
            member = {"email": email, "role": role, "invited_at": now_iso(), "accepted": registered}
            record["members"].append(member)
            return record, (member, record["name"])
        member, name = self.mutate("workspace-" + workspace, change)
        if registered:
            self._add_entry(email, {"id": workspace, "name": name, "role": role})
        else:
            def pending(invite):
                spaces = (invite or {}).get("workspaces", [])
                return {"email": email, "workspaces": [*spaces, workspace] if workspace not in spaces else spaces}, None
            self.mutate("invite-" + digest(email), pending)
        return member

    def set_role(self, workspace: str, email: str, role: str) -> dict:
        if role not in ROLES[1:]:
            raise ValueError("Peran tidak dikenal")
        def change(record):
            member = next((m for m in (record or {}).get("members", []) if m["email"] == email), None)
            if not member:
                raise LookupError("Anggota tidak ditemukan")
            if member["role"] == "owner":
                raise ValueError("Peran pemilik bisnis tidak bisa diubah")
            member["role"] = role
            return record, member
        member = self.mutate("workspace-" + workspace, change)
        if member["accepted"]:
            self._set_entry(email, workspace, role=role)
        return member

    def remove_member(self, workspace: str, email: str) -> None:
        def change(record):
            member = next((m for m in (record or {}).get("members", []) if m["email"] == email), None)
            if not member:
                raise LookupError("Anggota tidak ditemukan")
            if member["role"] == "owner":
                raise ValueError("Pemilik bisnis tidak bisa dihapus dari anggota")
            record["members"] = [m for m in record["members"] if m["email"] != email]
            return record, member
        member = self.mutate("workspace-" + workspace, change)
        if member["accepted"]:
            self._drop_entry(email, workspace)
        else:
            self._forget_invite(email, workspace)

    def _transfer(self, workspace: str, old: str, new: str) -> None:
        def change(record):
            record["owner_email"] = new
            record["members"] = [{**m, "role": "owner"} if m["email"] == new else m
                                 for m in record["members"] if m["email"] != old]
            return record, None
        self.mutate("workspace-" + workspace, change)
        self._set_entry(new, workspace, role="owner")

    def delete_account(self, email: str) -> list[str]:
        user = self.get("user-" + digest(email))
        if not user:
            return []
        archived = []
        for space in self.spaces(user):
            record = self.workspace(space["id"], email)
            if not record or record.get("archived"):
                continue
            member = next((m for m in record["members"] if m["email"] == email), None)
            if not member:
                continue
            if member["role"] != "owner":
                self.remove_member(space["id"], email)
                continue
            others = [m for m in record["members"] if m["email"] != email and m["accepted"]
                      and self.get("user-" + digest(m["email"]))]
            if not others:
                self.archive_workspace(space["id"])
                archived.append(space["id"])
            else:
                heir = next((m for m in others if m["role"] == "admin"), others[0])
                self._transfer(space["id"], email, heir["email"])
        self.delete("user-" + digest(email))
        self.delete("invite-" + digest(email))
        return archived

    def check_password(self, email: str, password: str) -> bool:
        user = self.get("user-" + digest(email))
        stored = user["password"] if user else hash_password("dummy-password-for-timing", "0" * 32)
        return password_matches(password, stored) and user is not None

    def _set_password(self, email: str, password: str) -> int:
        hashed = hash_password(password)
        def change(user):
            user["password"] = hashed
            user["session_version"] = user.get("session_version", 0) + 1
            return user["session_version"]
        return self.mutate_user(email, change)

    def _keep_session(self, token: str | None, version: int) -> None:
        key = "session-" + digest(token) if token else ""
        data = self.get(key) if token else None
        if data:
            data["version"] = version
            self.put(key, data)

    def revoke_sessions(self, email: str, keep: str | None = None) -> None:
        def change(user):
            user["session_version"] = user.get("session_version", 0) + 1
            return user["session_version"]
        self._keep_session(keep, self.mutate_user(email, change))

    def change_password(self, email: str, current: str, new: str, keep: str | None = None) -> None:
        if not self.check_password(email, current):
            raise ValueError("Kata sandi saat ini salah")
        self._keep_session(keep, self._set_password(email, new))

    def _token(self, prefix: str, user: dict, seconds: int) -> str:
        token = secrets.token_urlsafe(32)
        self.put(f"{prefix}-" + digest(token), {
            "email": user["email"], "user_id": user["id"], "version": user.get("session_version", 0),
            "expires": time.time() + seconds,
        })
        return token

    def _redeem(self, prefix: str, token: str, *, versioned: bool) -> dict | None:
        data = self.take(f"{prefix}-" + digest(token)) if token else None
        if not data or data["expires"] <= time.time():
            return None
        user = self.get("user-" + digest(data["email"]))
        if not user or user["id"] != data["user_id"]:
            return None
        if versioned and data["version"] != user.get("session_version", 0):
            return None
        return user

    def reset_token(self, email: str) -> str | None:
        user = self.get("user-" + digest(email))
        return self._token("reset", user, RESET_SECONDS) if user else None

    def reset_password(self, token: str, password: str) -> None:
        user = self._redeem("reset", token, versioned=True)
        if not user:
            raise ValueError("Tautan atur ulang kata sandi tidak valid atau sudah kedaluwarsa")
        self._set_password(user["email"], password)

    def verify_token(self, email: str) -> str | None:
        user = self.get("user-" + digest(email))
        return self._token("verify", user, VERIFY_SECONDS) if user else None

    def verify_email(self, token: str) -> None:
        user = self._redeem("verify", token, versioned=False)
        if not user:
            raise ValueError("Tautan verifikasi email tidak valid atau sudah kedaluwarsa")
        self.mutate_user(user["email"], lambda u: u.update(email_verified=True))

    def rate_limited(self, limits: dict[str, int], window: int = 60) -> bool:
        now = time.time()
        with self.lock:
            hits = {}
            for key, limit in limits.items():
                row = self.get("ratelimit-" + digest(key)) or {}
                recent = [t for t in row.get("hits", []) if t > now - window]
                if len(recent) >= limit:
                    return True
                hits[key] = recent
            for key, recent in hits.items():
                self.put("ratelimit-" + digest(key), {"hits": [*recent, now][-limits[key]:], "expires": now + window})
        return False

    def select_workspace(self, session: str, workspace: str) -> None:
        key = "session-" + digest(session)
        with self.lock:
            user = self.user_for_session(session)
            data = self.get(key)
            if not data or not user or not any(w["id"] == workspace for w in self.spaces(user)):
                raise ValueError("Anda tidak memiliki akses ke bisnis ini")
            data["workspace_id"] = workspace
            self.put(key, data)

    def update_profile(self, email: str, workspace: str, name: str, business: str) -> None:
        self.mutate_user(email, lambda user: user.update(name=name))
        user = self.get("user-" + digest(email))
        current = next((w["name"] for w in self.spaces(user) if w["id"] == workspace), None)
        if current == business:
            return
        if self.workspace(workspace, email):
            self.update_workspace(workspace, name=business)
        else:
            self._set_entry(email, workspace, name=business)

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
