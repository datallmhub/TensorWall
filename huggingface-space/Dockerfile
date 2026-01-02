# TensorWall - Hugging Face Space Docker
# Single container with Backend (FastAPI) + Frontend (Next.js) + SQLite + Caddy

FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=
RUN npm run build

# -------------------------------------------
# Final image: Python + Node + Caddy
# -------------------------------------------
FROM python:3.11-slim

# Install Node.js and Caddy
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt aiosqlite

COPY backend/ ./backend/

# Copy frontend build
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json ./frontend/
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/next.config.js ./frontend/

# Copy HF Space specific files
COPY huggingface-space/Caddyfile /etc/caddy/Caddyfile
COPY huggingface-space/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# HF Space port
ENV PORT=7860

# SQLite database (no external deps)
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/tensorwall.db
ENV ENVIRONMENT=demo
ENV REDIS_URL=

# Demo credentials
ENV DEMO_MODE=true
ENV ADMIN_EMAIL=demo@tensorwall.ai
ENV ADMIN_PASSWORD=demo123

# CORS
ENV CORS_ORIGINS=["*"]

# JWT secret for demo
ENV JWT_SECRET_KEY=hf-demo-secret-key-not-for-production

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -sf http://localhost:7860/api/health/live || exit 1

CMD ["/app/start.sh"]
