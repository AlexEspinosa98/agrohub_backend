import logging
import os
from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector.cursor import MySQLCursorDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la base de datos principal (MySQL)
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "agrohub"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
}


def get_connection():
    """Obtiene una conexión a la base de datos MySQL"""
    try:
        return mysql.connector.connect(**DATABASE_CONFIG)
    except mysql.connector.Error as e:  # pragma: no cover - conexión externa
        logger.error("Error conectando a la base de datos: %s", e)
        raise


@contextmanager
def get_db_cursor() -> Generator[MySQLCursorDict, None, None]:
    """Context manager para obtener un cursor dict y manejar commit/rollback"""
    conn = None
    cursor: MySQLCursorDict | None = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        yield cursor
        conn.commit()
    except Exception as e:  # pragma: no cover - manejo genérico
        if conn:
            conn.rollback()
        logger.error("Error en operación de base de datos: %s", e)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def test_connection():
    """Prueba la conexión a la base de datos"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version = cursor.fetchone()
            logger.info("Conexión exitosa a MySQL: %s", version.get("version"))
            return True
    except Exception as e:  # pragma: no cover - conexión externa
        logger.error("Error al probar la conexión: %s", e)
        return False
