FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Copy root project pyproject.toml and source for ai-driven-e2e dependency
COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Copy the product/api project
COPY product/api ./product/api

# Sync dependencies for product/api
WORKDIR /workspace/product/api
RUN uv sync --frozen --no-dev

ENV PATH="/workspace/product/api/.venv/bin:$PATH"

CMD ["uvicorn", "product_api.main:run", "--factory", "--host", "0.0.0.0"]
