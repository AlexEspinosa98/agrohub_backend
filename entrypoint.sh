#!/bin/sh
set -e

python - <<'PYEOF'
import os
import socket
import time

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))
print(f"Esperando a MySQL en {host}:{port}...")
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("MySQL disponible.")
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit(f"No se pudo conectar a MySQL en {host}:{port}")
PYEOF

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
