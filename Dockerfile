#syntax=docker/dockerfile:1.19

FROM python:3.13 AS builder

WORKDIR /app

ENV UV_PYTHON_PREFERENCE=only-system
ENV UV_PYTHON_DOWNLOADS=never

COPY --link --from=ghcr.io/astral-sh/uv:latest /uv /usr/bin/uv

ENV VIRTUAL_ENV=/opt/venv
RUN uv venv ${VIRTUAL_ENV} --seed

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --active --frozen --no-install-project --no-dev

COPY --link src /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    uv build

FROM python:3.13-slim AS base

WORKDIR /app

COPY --link --from=ghcr.io/astral-sh/uv:latest /uv /usr/bin/uv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=tmpfs,target=/var/log <<-EOT
    apt-get update
    apt-get install -y --no-install-recommends tini
    apt-get clean
EOT

# Create directories for volume mounts
RUN mkdir -p /app/papers /app/data /app/database /app/logs && \
    chmod 777 /app/data /app/database /app/logs

ENTRYPOINT [ "tini", "--", "moya-research"]
CMD [ "--help" ]

FROM base AS dev

COPY --from=builder /opt/venv /opt/venv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,from=builder,source=/app/src,target=/app/src \
    uv sync --active --frozen --no-dev

ENV PYTHONPATH=/app/src
VOLUME [ "/app/src" ]

FROM base AS app

COPY --from=builder /opt/venv /opt/venv

RUN --mount=type=bind,from=builder,source=/app/dist,target=/app/dist uv pip install --no-deps /app/dist/*.whl