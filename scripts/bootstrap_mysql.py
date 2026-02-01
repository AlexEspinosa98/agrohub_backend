#!/usr/bin/env python3
"""
Bootstrap de esquema en MySQL.

Este script instancia los repositorios que ya crean tablas en su constructor.
Úsalo cuando despliegues en una base nueva o quieras asegurarte de que todas las
tablas existen en el host configurado en las variables de entorno DB_*.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

# Asegura que el directorio raíz del proyecto esté en sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Carga variables de entorno antes de importar conexión (para que DATABASE_CONFIG use los valores correctos)
load_dotenv(ROOT / ".env")

from database.connection import test_connection
from modules.user_activity.infrastructure.repositories.postgres_repository import (
    UserActivityRepository,
)
from data_characterization.infrastructure.repositories.postgres_repository import (
    PostgresEncuestaRepository,
)
from modules.hub_cgsm.infrastructure_hub_cgsm.repositories.postgres_repository import (
    PostgresEncuestaRepository as HubRepo,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap_mysql")


def main() -> None:
    # Carga variables de entorno desde .env en el root del proyecto
    load_dotenv(ROOT / ".env")
    logger.info(
        "Usando DB_HOST=%s DB_PORT=%s DB_NAME=%s DB_USER=%s",
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_NAME"),
        os.getenv("DB_USER"),
    )

    logger.info("Verificando conexión MySQL...")
    if not test_connection():
        raise SystemExit("No se pudo conectar a MySQL con las variables DB_*")

    logger.info("Creando/esquema User Activity...")
    UserActivityRepository()

    logger.info("Creando/esquema Data Characterization...")
    PostgresEncuestaRepository()

    logger.info("Creando/esquema Hub CGSM...")
    HubRepo()

    logger.info("✅ Esquema asegurado en MySQL.")


if __name__ == "__main__":
    main()
