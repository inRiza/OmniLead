#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
for node_bin in /opt/homebrew/opt/node@24/bin/node /usr/local/opt/node@24/bin/node; do
  if [[ -x "$node_bin" ]]; then
    export PATH="$(dirname "$node_bin"):$PATH"
    break
  fi
done
if ! command -v npm >/dev/null 2>&1; then
  echo "npm tidak ditemukan. Pasang Node 24 LTS: brew install node@24" >&2
  exit 1
fi
NODE_VER="$(node -p "process.versions.node")"
NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
if [[ "$NODE_MAJOR" == "25" ]]; then
  echo "Node $NODE_VER: OpenClaw preinstall menolak v25; memakai npm ci --ignore-scripts (disarankan Node 24 LTS via fnm/nvm)."
  npm ci --ignore-scripts
else
  npm ci
fi
echo "OpenClaw $(node -p "require('./node_modules/openclaw/package.json').version") siap di $ROOT"
