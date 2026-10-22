"""Supervise the official OpenClaw gateway and one OmniLead API worker."""

import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener


def main():
    os.umask(0o077)
    state = Path(os.environ["OMNILEAD_OPENCLAW_STATE_DIR"])
    token_file = Path(os.environ["OMNILEAD_OPENCLAW_TOKEN_FILE"])
    state.mkdir(parents=True, exist_ok=True)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    if not token_file.exists():
        # Exclusive creation avoids overwriting a supplied/persisted runtime secret.
        with token_file.open("x") as stream:
            stream.write(secrets.token_hex(32))
    token = token_file.read_text().strip()
    if len(token) < 32:
        raise RuntimeError("OpenClaw token file must contain at least 32 characters")
    config_path = state / "openclaw.json"
    config = {
        "gateway": {"mode": "local", "bind": "loopback", "port": 18889,
            "auth": {"mode": "token", "token": token}, "controlUi": {"enabled": False}},
        "agents": {"defaults": {"workspace": str(state / "workspace")}},
        "tools": {"allow": ["browser"]},
        "plugins": {"allow": ["browser"], "entries": {"browser": {"enabled": True}}},
        "browser": {"enabled": True, "headless": True, "evaluateEnabled": False,
            "executablePath": "/usr/bin/chromium", "noSandbox": True,
            "ssrfPolicy": {"dangerouslyAllowPrivateNetwork": False,
                "allowedHostnames": ["www.instagram.com", "instagram.com", "www.facebook.com",
                    "facebook.com", "www.messenger.com", "web.whatsapp.com", "mail.google.com", "accounts.google.com"]}},
    }
    config_path.write_text(json.dumps(config))
    environment = {**os.environ, "OPENCLAW_STATE_DIR": str(state),
        "OPENCLAW_CONFIG_PATH": str(config_path), "OPENCLAW_EAGER_BROWSER_CONTROL_SERVER": "1"}
    stopping = False
    children = []

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    exit_code = 1
    try:
        gateway = subprocess.Popen(["node", "/opt/openclaw/node_modules/openclaw/openclaw.mjs",
            "gateway", "run", "--bind", "loopback", "--port", "18889"],
            env=environment, start_new_session=True)
        children.append(gateway)
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 210
        while not stopping:
            if gateway.poll() is not None:
                raise RuntimeError("OpenClaw gateway exited during startup")
            try:
                request = Request("http://127.0.0.1:18891/profiles", headers={"Authorization": "Bearer " + token})
                with opener.open(request, timeout=2) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("OpenClaw browser control startup timed out")
            time.sleep(1)
        if stopping:
            return 0
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "omnilead.main:app",
            "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8080"), "--workers", "1"],
            env=environment, start_new_session=True)
        children.append(api)
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A runtime process exited; stopping the container")
            time.sleep(1)
        exit_code = 0
    finally:
        # Shut down API first so it can close its own OpenClaw browser profiles.
        for child in reversed(children):
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=3)
                except ProcessLookupError:
                    pass
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
