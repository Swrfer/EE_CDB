FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m pip install \
    --no-cache-dir \
    uv==0.12.13

COPY pyproject.toml uv.lock README.md ./

RUN uv sync \
    --locked \
    --extra dev \
    --no-install-project \
    --no-cache

COPY src ./src

RUN uv sync \
    --locked \
    --extra dev \
    --no-editable \
    --no-cache


FROM python:3.12-slim AS runtime

ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE="1"
ENV PYTHONUNBUFFERED="1"

WORKDIR /app

RUN groupadd \
        --gid 10001 \
        clinlab \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --home-dir /home/clinlab \
        --shell /usr/sbin/nologin \
        clinlab \
    && chown 10001:10001 /app

COPY --from=builder \
    --chown=10001:10001 \
    /app/.venv \
    /app/.venv

COPY --chown=10001:10001 \
    pyproject.toml \
    ./pyproject.toml

COPY --chown=10001:10001 \
    tests \
    ./tests

USER 10001:10001

CMD ["pytest"]
