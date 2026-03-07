#!/bin/sh
set -e

# 绛夊緟 Postgres 灏辩华鍚庢墽琛屾暟鎹簱杩佺Щ
echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations done."

exec "$@"
