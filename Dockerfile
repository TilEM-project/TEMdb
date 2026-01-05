FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY packages/temdb-models/ ./packages/temdb-models/
COPY packages/temdb/ ./packages/temdb/

RUN uv pip install --system ./packages/temdb-models ./packages/temdb

COPY run.py ./

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000"]
