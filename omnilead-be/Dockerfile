# Cloud Run: omnilead-api. Belum diuji build di mesin pengembang (Docker daemon tidak aktif).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra firestore
ENV PATH="/app/.venv/bin:$PATH" PORT=8080 OMNILEAD_STORE=firestore
EXPOSE 8080
CMD ["sh", "-c", "uvicorn omnilead.main:app --host 0.0.0.0 --port ${PORT}"]
