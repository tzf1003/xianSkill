#!/bin/sh
set -e

export PYTHONPATH=/app

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations done."

exec "$@"
