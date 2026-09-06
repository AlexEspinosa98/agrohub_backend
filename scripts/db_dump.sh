#!/usr/bin/env bash
# Dumps the full AgroHub MySQL database (schema + data, all apps' tables)
# from whatever DB is configured in .env, for the onpremise migration.
#
# Uses the mysql:8.0 Docker image to run mysqldump, so no local mysql
# client install is required. Produces a single self-contained .sql file
# under backups/ that db_restore.sh can load into the onpremise db as-is
# (including django_migrations, so `manage.py migrate` is a no-op afterward).
#
# Usage:
#   ./scripts/db_dump.sh
#
# Override the source DB without touching .env:
#   DB_HOST=other-host DB_NAME=other_db ./scripts/db_dump.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${DB_HOST:-}" ] && [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DB_HOST:?DB_HOST not set (check .env)}"
: "${DB_PORT:=3306}"
: "${DB_NAME:?DB_NAME not set (check .env)}"
: "${DB_USER:?DB_USER not set (check .env)}"
: "${DB_PASSWORD:?DB_PASSWORD not set (check .env)}"

mkdir -p backups
OUT="backups/agrohub_$(date +%Y%m%d_%H%M%S).sql"

echo "Dumping ${DB_NAME}@${DB_HOST}:${DB_PORT} -> ${OUT}"
docker run --rm mysql:8.0 \
  mysqldump \
  -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
  --single-transaction --quick --routines --triggers --set-gtid-purged=OFF --no-tablespaces \
  "$DB_NAME" > "$OUT"

echo "Done: ${OUT} ($(du -h "$OUT" | cut -f1))"
