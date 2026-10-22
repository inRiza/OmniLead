#!/usr/bin/env bash
set -euo pipefail
TOOL_ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$TOOL_ROOT/../.." && pwd)"
# OpenClaw resmi: Node 24.16+ atau 26.1+ (bukan v25).
for node_bin in /opt/homebrew/opt/node@24/bin/node /usr/local/opt/node@24/bin/node; do
  if [[ -x "$node_bin" ]]; then
    export PATH="$(dirname "$node_bin"):$PATH"
    break
  fi
done
BACKEND_ROOT="$REPO_ROOT/omnilead-be"
STATE_ROOT="$BACKEND_ROOT/data/openclaw"
LOG_ROOT="$BACKEND_ROOT/data/local-runtime"
SECRET_ROOT="$BACKEND_ROOT/.secrets"
ENTRY="$TOOL_ROOT/node_modules/openclaw/openclaw.mjs"

if [[ ! -f "$ENTRY" ]]; then
  echo "Jalankan dulu: $TOOL_ROOT/install.sh" >&2
  exit 1
fi
if lsof -iTCP:18889 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 18889 sudah dipakai. OpenClaw mungkin sudah jalan." >&2
  exit 1
fi

mkdir -p "$STATE_ROOT" "$LOG_ROOT" "$SECRET_ROOT"
TOKEN_PATH="$SECRET_ROOT/openclaw-token"
if [[ ! -f "$TOKEN_PATH" ]]; then
  openssl rand -hex 32 >"$TOKEN_PATH"
fi
TOKEN="$(tr -d '\n' <"$TOKEN_PATH")"

BROWSER=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
  if [[ -x "$candidate" ]]; then
    BROWSER="$candidate"
    break
  fi
done
if [[ -z "$BROWSER" ]]; then
  echo "Pasang Google Chrome atau Microsoft Edge di macOS." >&2
  exit 1
fi

CONFIG_PATH="$STATE_ROOT/openclaw.json"
if [[ ! -f "$CONFIG_PATH" ]]; then
  cat >"$CONFIG_PATH" <<EOF
{
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "port": 18889,
    "auth": { "mode": "token", "token": "$TOKEN" },
    "controlUi": { "enabled": false }
  },
  "agents": { "defaults": { "workspace": "$STATE_ROOT/workspace" } },
  "tools": { "allow": ["browser"] },
  "plugins": { "allow": ["browser"], "entries": { "browser": { "enabled": true } } },
  "browser": {
    "enabled": true,
    "headless": false,
    "evaluateEnabled": false,
    "executablePath": "$BROWSER",
    "ssrfPolicy": {
      "dangerouslyAllowPrivateNetwork": false,
      "allowedHostnames": [
        "www.instagram.com", "instagram.com",
        "www.facebook.com", "facebook.com", "www.messenger.com",
        "web.whatsapp.com", "mail.google.com", "accounts.google.com"
      ]
    }
  }
}
EOF
fi

export OPENCLAW_STATE_DIR="$STATE_ROOT"
export OPENCLAW_CONFIG_PATH="$CONFIG_PATH"
export OPENCLAW_EAGER_BROWSER_CONTROL_SERVER=1
STAMP="$(date +%Y%m%d-%H%M%S)"
STDOUT="$LOG_ROOT/openclaw-$STAMP.stdout.log"
STDERR="$LOG_ROOT/openclaw-$STAMP.stderr.log"

nohup node "$ENTRY" gateway run --port 18889 --bind loopback >"$STDOUT" 2>"$STDERR" &
PID=$!
ready=0
for _ in $(seq 1 90); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "OpenClaw gagal start. Lihat $STDERR" >&2
    exit 1
  fi
  if lsof -iTCP:18889 -sTCP:LISTEN >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "OpenClaw masih boot (PID $PID). Cek log $STDERR — startup bisa 1–3 menit." >&2
fi
cat >"$LOG_ROOT/openclaw-runtime.json" <<EOF
{"pid":$PID,"started_at":"$STAMP","state_dir":"$STATE_ROOT","config_path":"$CONFIG_PATH","version":"2026.10.5","gateway_port":18889,"browser_port":18891}
EOF
echo "OpenClaw gateway PID $PID — loopback :18889, browser control :18891"
echo "Log: $STDOUT"
