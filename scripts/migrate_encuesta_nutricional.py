#!/usr/bin/env python3
"""
Migración: encuestas_nutricionales (tabla plana original)
         → personas_nutricionales + encuesta_nutricional_miembros

Ejecutar UNA SOLA VEZ desde la raíz del proyecto:
    python scripts/migrate_encuesta_nutricional.py

El script es idempotente: detecta el estado actual de la BD y solo migra
lo que aún no haya sido migrado.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mysql_connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone()["cnt"] > 0


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table,),
    )
    return cur.fetchone()["cnt"] > 0


def step1_create_personas_table(cur):
    log.info("Paso 1: creando tabla personas_nutricionales (si no existe)...")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS personas_nutricionales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cedula VARCHAR(50) NOT NULL UNIQUE,
            nombre VARCHAR(255),
            edad_anios INT,
            sexo VARCHAR(20),
            area_residencia VARCHAR(20),
            nivel_educativo VARCHAR(50),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    log.info("  OK")


def step2_create_miembros_table(cur):
    log.info("Paso 2: creando tabla encuesta_nutricional_miembros (si no existe)...")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS encuesta_nutricional_miembros (
            id INT AUTO_INCREMENT PRIMARY KEY,
            encuesta_id INT NOT NULL,
            persona_id INT NOT NULL,
            percepcion_estado_nutricional VARCHAR(20),
            cambio_peso_no_intencional BOOLEAN,
            nino_en_control_crecimiento VARCHAR(10),
            peso_kg DECIMAL(6,2),
            talla_cm DECIMAL(6,2),
            circunferencia_cintura_cm DECIMAL(6,2),
            perimetro_brazo_cm DECIMAL(6,2),
            grupo_perimetro_brazo VARCHAR(30),
            imc_calculado DECIMAL(6,2),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL,
            CONSTRAINT fk_miembro_encuesta
                FOREIGN KEY (encuesta_id)
                REFERENCES encuestas_nutricionales(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_miembro_persona
                FOREIGN KEY (persona_id)
                REFERENCES personas_nutricionales(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    log.info("  OK")


def step3_migrate_existing_rows(cur):
    """
    Por cada fila en encuestas_nutricionales que tenga cedula_participante
    (columna del esquema original) y aún no tenga miembro migrado, crea:
      1. Un registro en personas_nutricionales (upsert por cédula)
      2. Un registro en encuesta_nutricional_miembros
    """
    if not _column_exists(cur, "encuestas_nutricionales", "cedula_participante"):
        log.info("Paso 3: columna 'cedula_participante' no encontrada — nada que migrar.")
        return

    log.info("Paso 3: migrando filas de encuestas_nutricionales a personas + miembros...")

    cur.execute(
        """
        SELECT e.id, e.cedula_participante, e.nombre_participante,
               e.edad_anios, e.sexo, e.area_residencia, e.nivel_educativo,
               e.percepcion_estado_nutricional, e.cambio_peso_no_intencional,
               e.nino_en_control_crecimiento, e.peso_kg, e.talla_cm,
               e.circunferencia_cintura_cm, e.perimetro_brazo_cm,
               e.grupo_perimetro_brazo, e.imc_calculado,
               e.is_active, e.created_at, e.deleted_at
        FROM encuestas_nutricionales e
        LEFT JOIN encuesta_nutricional_miembros m ON m.encuesta_id = e.id
        WHERE m.id IS NULL
          AND e.cedula_participante IS NOT NULL
        """
    )
    rows = cur.fetchall()
    log.info("  Filas a migrar: %d", len(rows))

    migrated = 0
    for row in rows:
        # Upsert persona
        cur.execute(
            """
            INSERT INTO personas_nutricionales
                (cedula, nombre, edad_anios, sexo, area_residencia, nivel_educativo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = LAST_INSERT_ID(id),
                nombre        = COALESCE(VALUES(nombre), nombre),
                edad_anios    = COALESCE(VALUES(edad_anios), edad_anios),
                sexo          = COALESCE(VALUES(sexo), sexo),
                area_residencia  = COALESCE(VALUES(area_residencia), area_residencia),
                nivel_educativo  = COALESCE(VALUES(nivel_educativo), nivel_educativo)
            """,
            (
                row["cedula_participante"],
                row.get("nombre_participante"),
                row.get("edad_anios"),
                row.get("sexo"),
                row.get("area_residencia"),
                row.get("nivel_educativo"),
            ),
        )
        persona_id = cur.lastrowid

        # Insertar miembro
        cur.execute(
            """
            INSERT INTO encuesta_nutricional_miembros (
                encuesta_id, persona_id,
                percepcion_estado_nutricional, cambio_peso_no_intencional,
                nino_en_control_crecimiento, peso_kg, talla_cm,
                circunferencia_cintura_cm, perimetro_brazo_cm,
                grupo_perimetro_brazo, imc_calculado,
                is_active, deleted_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                row["id"], persona_id,
                row.get("percepcion_estado_nutricional"),
                row.get("cambio_peso_no_intencional"),
                row.get("nino_en_control_crecimiento"),
                row.get("peso_kg"), row.get("talla_cm"),
                row.get("circunferencia_cintura_cm"),
                row.get("perimetro_brazo_cm"),
                row.get("grupo_perimetro_brazo"),
                row.get("imc_calculado"),
                row["is_active"],
                row.get("deleted_at"),
            ),
        )
        migrated += 1

    log.info("  Migrados: %d filas", migrated)


def step4_drop_old_columns(cur):
    """
    Elimina de encuestas_nutricionales las columnas que ya pasaron
    a personas_nutricionales y encuesta_nutricional_miembros.
    Solo elimina si la columna existe.
    """
    columns_to_drop = [
        "nombre_participante", "cedula_participante",
        "edad_anios", "sexo", "area_residencia", "nivel_educativo",
        "percepcion_estado_nutricional", "cambio_peso_no_intencional",
        "nino_en_control_crecimiento", "peso_kg", "talla_cm",
        "circunferencia_cintura_cm", "perimetro_brazo_cm",
        "grupo_perimetro_brazo", "imc_calculado",
    ]
    to_drop = [c for c in columns_to_drop
               if _column_exists(cur, "encuestas_nutricionales", c)]

    if not to_drop:
        log.info("Paso 4: columnas ya eliminadas previamente — nada que hacer.")
        return

    log.info("Paso 4: eliminando columnas individuales de encuestas_nutricionales...")
    drop_clause = ", ".join(f"DROP COLUMN `{c}`" for c in to_drop)
    cur.execute(f"ALTER TABLE encuestas_nutricionales {drop_clause}")
    log.info("  Columnas eliminadas: %s", ", ".join(to_drop))


def main():
    log.info("=== Migración encuesta_nutricional ===")
    with get_db_cursor() as cur:
        step1_create_personas_table(cur)
        step2_create_miembros_table(cur)
        step3_migrate_existing_rows(cur)
        step4_drop_old_columns(cur)
    log.info("=== Migración completada exitosamente ===")


if __name__ == "__main__":
    main()
