FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts

RUN pip install --no-cache-dir -e ".[api,temporal,redis]"

EXPOSE 8000

CMD ["sh", "-c", "python scripts/migrate.py && python scripts/serve_api.py"]
