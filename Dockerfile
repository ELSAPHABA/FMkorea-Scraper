FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md docker-entrypoint.sh ./
COPY src ./src

RUN chmod +x /app/docker-entrypoint.sh \
    && pip install --no-cache-dir ".[s3,postgres]"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
