# Build from the repository root: docker build -f tools/openclaw/Dockerfile .
FROM node:24.16.0-bookworm-slim AS openclaw
WORKDIR /opt/openclaw
COPY tools/openclaw/package.json tools/openclaw/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium ca-certificates fonts-liberation tini \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv
COPY --from=openclaw /usr/local/bin/node /usr/local/bin/node
COPY --from=openclaw /opt/openclaw /opt/openclaw
WORKDIR /app
COPY omnilead-be/pyproject.toml omnilead-be/uv.lock omnilead-be/README.md ./
COPY omnilead-be/src ./src
RUN uv sync --frozen --no-dev --extra firestore \
    && groupadd --gid 10001 omnilead && useradd --uid 10001 --gid 10001 --create-home omnilead \
    && mkdir -p /var/lib/omnilead && chown -R omnilead:omnilead /var/lib/omnilead
COPY tools/openclaw/container.py /opt/openclaw/container.py
ENV PATH="/app/.venv/bin:$PATH" PORT=8080 \
    OMNILEAD_BROWSER_ENABLED=true OMNILEAD_BROWSER_HEADLESS=true \
    OMNILEAD_OPENCLAW_STATE_DIR=/var/lib/omnilead/openclaw \
    OMNILEAD_OPENCLAW_TOKEN_FILE=/var/lib/omnilead/secrets/openclaw-token \
    OMNILEAD_SECRETS_DIR=/var/lib/omnilead/secrets \
    OMNILEAD_DB_PATH=/var/lib/omnilead/omnilead.db \
    OMNILEAD_ACCOUNTS_DB_PATH=/var/lib/omnilead/accounts.db
USER omnilead
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "python", "/opt/openclaw/container.py"]
