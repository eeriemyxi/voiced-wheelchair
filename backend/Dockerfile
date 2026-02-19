FROM python:3.13-alpine AS base

ENV PYTHONUNBUFFERED=1
RUN apk add uv
COPY . /backend
WORKDIR /backend

RUN uv sync

FROM base AS production
CMD uv run fastapi run main.py --host 0.0.0.0

FROM base AS development
CMD uv run fastapi dev main.py --host 0.0.0.0
