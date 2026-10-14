#!/bin/sh
# Start nginx (public edge) and the Next.js standalone server (internal).
# Wait for the backend microservice before serving requests. The default
# BACKEND_URL=http://backend:8000 is retried when the backend is not yet up.

set -eu

if [ -n "${BACKEND_URL:-}" ]; then
    HOST="${BACKEND_URL#http://}"
    HOST="${HOST#https://}"
    HOST="${HOST%%/*}"
    i=1
    until wget -q -O /dev/null "http://$HOST/health" || [ "$i" -gt 30 ]; do
        echo "waiting for backend ($HOST)… attempt $i/30"
        i=$((i + 1))
        sleep 2
    done
fi

nginx

# Pin the standalone server to loopback: nginx is the only process that talks
# to it inside this container.
export HOSTNAME=127.0.0.1

exec node server.js