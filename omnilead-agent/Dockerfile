# Cloud Run: omnilead-agent. Dibangun dan dijalankan di Docker lokal (21 Okt 2026).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY eval ./eval
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn omnilead_agent.main:app --host 0.0.0.0 --port ${PORT}"]
