FROM python:3.12-slim AS builder
ARG UV_VERSION=0.11.1
ENV UV_CACHE_DIR=/tmp/uv-cache UV_LINK_MODE=copy
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config ./config
COPY goldens ./goldens
RUN uv sync --locked --no-dev

FROM python:3.12-slim
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
RUN groupadd --system agent && useradd --system --gid agent --home /app agent
WORKDIR /app
COPY --from=builder --chown=agent:agent /app /app
USER agent
ENTRYPOINT ["marketplace-listing-agent"]
CMD ["doctor", "--scope", "core"]
