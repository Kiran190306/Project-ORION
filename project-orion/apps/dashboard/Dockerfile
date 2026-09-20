# ════════════════════════════════════════════════════════════
# Project ORION — Production Trading Dashboard Container
# Multi-stage image: Node build -> Nginx static server
# ════════════════════════════════════════════════════════════

# ── Stage 1: Build Frontend Artifacts ────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Build arguments for frontend configuration (default empty for single-domain relative proxy)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Install dependencies
COPY package.json ./
RUN npm install --no-audit --no-fund

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ── Stage 2: Production Nginx Server ─────────────────────────
FROM nginx:1.27-alpine-slim AS runtime

LABEL maintainer="platform-team@orion.example.com"
LABEL service="orion-dashboard"
LABEL version="0.1.0"
LABEL description="Project ORION Institutional Paper Trading Dashboard"

# Copy custom Nginx configuration with SPA fallback and security headers
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
