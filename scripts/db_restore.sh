#!/usr/bin/env bash
# Restores a dump produced by db_dump.sh into the onpremise `db` service
# from docker-compose.yml. Run this ON the onpremise host, from the project
# directory, with the onpremise .env already in place and the stack up
# (`docker compose up -d db`).
#
# Usage:
#   ./scripts/db_restore.sh backups/agrohub_20260904_120000.sql
set -euo pipefail
cd "$(dirname "$0")/.."

DUMP_FILE="${1:?Usage: $0 <dump_file.sql>}"
[ -f "$DUMP_FILE" ] || { echo "No existe: $DUMP_FILE" >&2; exit 1; }

if [ -z "${DB_NAME:-}" ] && [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DB_NAME:?DB_NAME not set (check .env)}"
: "${DB_USER:?DB_USER not set (check .env)}"
: "${DB_PASSWORD:?DB_PASSWORD not set (check .env)}"

echo "Restoring ${DUMP_FILE} into onpremise db service (${DB_NAME})..."
docker compose exec -T db mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$DUMP_FILE"

echo "Restore complete. Run 'python manage.py migrate' as a no-op sanity check."
