# Image of the simulator service. Build it from the repository root, which contains libs/schemas:
#   docker build -f services/simulator/Dockerfile .

# --- Stage 1: install the dependencies and the packages into a virtual environment -------------
FROM python:3.12.16-slim AS build

# uv, at the same version as on developer machines and in CI.
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

# Compile .py files to bytecode (faster start), copy files instead of linking them,
# and use the Python of this image instead of downloading one.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Only the files describing the dependencies first: as long as they do not change,
# Docker reuses this layer and the next build skips the download.
COPY pyproject.toml uv.lock ./
COPY libs/schemas/pyproject.toml libs/schemas/
COPY services/simulator/pyproject.toml services/simulator/
RUN uv sync --locked --no-dev --package sentio-simulator --no-install-workspace

# Then the source code of the two packages the simulator needs.
COPY libs/schemas libs/schemas
COPY services/simulator services/simulator
RUN uv sync --locked --no-dev --package sentio-simulator --no-editable

# --- Stage 2: the image that runs, without uv, the source tree or build caches -----------------
FROM python:3.12.16-slim

# An unprivileged user: the service does not need root.
RUN useradd --system --uid 10001 --no-create-home simulator

COPY --from=build /app/.venv /app/.venv

# Use the virtual environment's Python; print logs immediately instead of buffering them.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER simulator

# Exec form: Python is the main process (PID 1) and receives SIGTERM directly from Docker.
CMD ["python", "-m", "sentio_simulator"]
