FROM oven/bun:1 AS base
WORKDIR /app

FROM base AS development

COPY package.json bun.lock* ./
RUN bun install
COPY . .
EXPOSE 3000

CMD ["bun", "run", "dev", "--host", "0.0.0.0", "--port", "3000"]
