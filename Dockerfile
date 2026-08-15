FROM python:3.13.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/app
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    pip install --upgrade pip && \
    pip install uv

WORKDIR /app

COPY ./pyproject.toml .

RUN uv pip install --system --no-cache .

COPY . .
