# Next.js frontend microservice — multi-stage build.
# Stage 1: install and build the Next.js app (standalone output).
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# BACKEND_URL and API_AUTH_TOKEN are read at request time by the proxy route
# handler, so they are runtime environment variables rather than build args.
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 2: runtime built from the same node:22-alpine base so the standalone
# server binary matches its Node version. nginx terminates HTTP and proxies the
# app and the /api/backend/* boundary to the backend microservice.
FROM node:22-alpine

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Next standalone server listens on the internal port; nginx is the public edge.
ENV PORT=3001
EXPOSE 3000

RUN apk add --no-cache nginx && \
    addgroup -S app && adduser -S -G app app && \
    mkdir -p /var/lib/nginx/logs && \
    touch /var/lib/nginx/logs/error.log

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

COPY nginx-main.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Keep the runtime process unprivileged.
RUN touch /run/nginx.pid && mkdir -p /var/cache/nginx /var/log/nginx /app/tmp && \
    chmod -R g+w /app && \
    chown -R app:app /app /run/nginx.pid /var/cache/nginx /var/log/nginx /etc/nginx && \
    chown -R app:app /var/lib/nginx

COPY --chown=app:app docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER app
ENTRYPOINT ["docker-entrypoint.sh"]