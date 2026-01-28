import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Generator
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'agrohub'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def get_connection():
    """Obtiene una conexión a la base de datos PostgreSQL"""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

@contextmanager
def get_db_cursor() -> Generator[RealDictCursor, None, None]:
    """Context manager para obtener un cursor de base de datos"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en operación de base de datos: {e}")
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
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"Conexión exitosa a PostgreSQL: {version['version']}")
            return True
    except Exception as e:
        logger.error(f"Error al probar la conexión: {e}")
        return False
