# syntax=docker/dockerfile:1.7
# Kanban.fun: one image, two roles (web = Daphne, worker = Steady Queue).

FROM node:24-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./frontend
RUN npm run typecheck && npm run build

FROM python:3.14-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    KANBAN_DATA_DIR=/data \
    KANBAN_MEDIA_DIR=/media
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install --no-install-recommends -y sqlite3 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
COPY --from=assets /app/static/dist ./static/dist
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput \
    && useradd --uid 1000 --create-home app \
    && mkdir -p /data /media \
    && chown -R app:app /data /media
USER app
VOLUME ["/data", "/media"]
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/up', timeout=4)" || exit 1
ENTRYPOINT ["bin/docker-entrypoint"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "config.asgi:application"]
