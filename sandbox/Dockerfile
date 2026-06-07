FROM python:3.14.5-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
RUN useradd -m -u 1000 sandbox
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache
USER sandbox

ENV PATH="/app/.venv/bin:$PATH"
