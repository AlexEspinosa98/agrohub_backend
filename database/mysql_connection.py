import logging
import os
from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector.cursor import MySQLCursorDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "agrohub"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "connection_timeout": 8,
}


def get_connection():
    """Obtiene una conexión a la base de datos MySQL."""
    try:
        return mysql.connector.connect(**DATABASE_CONFIG)
    except mysql.connector.Error as exc:  # pragma: no cover - conexión externa
        logger.error("Error conectando a la base de datos MySQL: %s", exc)
        raise


@contextmanager
def get_db_cursor() -> Generator[MySQLCursorDict, None, None]:
    """Context manager para obtener un cursor dict y manejar commit/rollback."""
    conn = None
    cursor: MySQLCursorDict | None = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        yield cursor
        conn.commit()
    except Exception as exc:  # pragma: no cover - manejo genérico
        if conn:
            conn.rollback()
        logger.error("Error en operación de base de datos: %s", exc)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def test_connection() -> bool:
    """Prueba la conexión a MySQL y registra la versión."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version = cursor.fetchone()
            logger.info("Conexión exitosa a MySQL: %s", version.get("version"))
            return True
    except Exception as exc:  # pragma: no cover - conexión externa
        logger.error("Error al probar la conexión a MySQL: %s", exc)
        return False
