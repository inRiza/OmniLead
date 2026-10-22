#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOKEN_FILE="$REPO_ROOT/omnilead-be/.secrets/openclaw-token"
if lsof -iTCP:18889 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "gateway: listening on 18889"
else
  echo "gateway: TIDAK JALAN — ./tools/openclaw/start.sh"
  exit 1
fi
if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "token: belum ada (start.sh akan membuatnya)"
  exit 1
fi
TOKEN=$(tr -d '\n' <"$TOKEN_FILE")
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:18891/profiles)
echo "browser control :18891 HTTP $code"
[[ "$code" == "200" ]] || exit 1
