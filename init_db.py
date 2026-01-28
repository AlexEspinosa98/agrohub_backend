#!/usr/bin/env python3
"""
Script para inicializar la base de datos de familias AgroHub
"""

import os
import sys
import logging
from database.connection import test_connection, get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_schema():
    """Crear el esquema de la base de datos ejecutando schema.sql"""
    try:
        # Leer el archivo schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
        
        if not os.path.exists(schema_path):
            logger.error(f"Archivo schema.sql no encontrado en: {schema_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Ejecutar el schema
        with get_db_cursor() as cursor:
            cursor.execute(schema_sql)
            logger.info("Schema de base de datos creado exitosamente")
            
        return True
        
    except Exception as e:
        logger.error(f"Error creando schema de base de datos: {e}")
        return False

def verify_tables():
    """Verificar que las tablas fueron creadas correctamente"""
    try:
        with get_db_cursor() as cursor:
            # Verificar tabla families
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'families'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            
            if not columns:
                logger.error("Tabla 'families' no encontrada")
                return False
            
            logger.info("Tabla 'families' verificada exitosamente:")
            for col in columns:
                logger.info(f"  - {col['column_name']}: {col['data_type']}")
            
            # Verificar índices
            cursor.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'families'
            """)
            
            indexes = cursor.fetchall()
            logger.info(f"Índices encontrados: {len(indexes)}")
            for idx in indexes:
                logger.info(f"  - {idx['indexname']}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error verificando tablas: {e}")
        return False

def insert_test_data():
    """Insertar datos de prueba (opcional)"""
    try:
        with get_db_cursor() as cursor:
            # Verificar si ya hay datos
            cursor.execute("SELECT COUNT(*) as count FROM families")
            result = cursor.fetchone()
            
            if result['count'] > 0:
                logger.info(f"La tabla ya contiene {result['count']} registros")
                return True
            
            # Insertar familia de prueba
            test_family = {
                'nombre_jefe': 'Juan Carlos',
                'apellido_jefe': 'Pérez García',
                'cedula': '12345678',
                'telefono': '3001234567',
                'direccion': 'Calle 123 #45-67',
                'vereda': 'La Esperanza',
                'municipio': 'Santa Marta',
                'numero_integrantes': '4',
                'tipo_vivienda': 'Casa propia',
                'actividad_economica': 'Agricultura - Banano',
                'observaciones': 'Familia de prueba para validar el sistema',
                'timestamp': 'NOW()',
                'sincronizado': True
            }
            
            cursor.execute("""
                INSERT INTO families (
                    nombre_jefe, apellido_jefe, cedula, telefono, direccion,
                    vereda, municipio, numero_integrantes, tipo_vivienda,
                    actividad_economica, observaciones, timestamp, sincronizado
                ) VALUES (
                    %(nombre_jefe)s, %(apellido_jefe)s, %(cedula)s, %(telefono)s, %(direccion)s,
                    %(vereda)s, %(municipio)s, %(numero_integrantes)s, %(tipo_vivienda)s,
                    %(actividad_economica)s, %(observaciones)s, NOW(), %(sincronizado)s
                )
            """, test_family)
            
            logger.info("Datos de prueba insertados exitosamente")
            return True
            
    except Exception as e:
        logger.error(f"Error insertando datos de prueba: {e}")
        return False

def main():
    """Función principal para inicializar la base de datos"""
    logger.info("=== Inicializando Base de Datos AgroHub Familias ===")
    
    # 1. Probar conexión
    logger.info("1. Probando conexión a la base de datos...")
    if not test_connection():
        logger.error("❌ No se pudo conectar a la base de datos")
        logger.error("Verifica la configuración en database/connection.py")
        sys.exit(1)
    logger.info("✅ Conexión exitosa")
    
    # 2. Crear schema
    logger.info("2. Creando schema de base de datos...")
    if not create_database_schema():
        logger.error("❌ Error creando schema")
        sys.exit(1)
    logger.info("✅ Schema creado exitosamente")
    
    # 3. Verificar tablas
    logger.info("3. Verificando tablas...")
    if not verify_tables():
        logger.error("❌ Error verificando tablas")
        sys.exit(1)
    logger.info("✅ Tablas verificadas exitosamente")
    
    # 4. Insertar datos de prueba (opcional)
    logger.info("4. Insertando datos de prueba...")
    if insert_test_data():
        logger.info("✅ Datos de prueba insertados")
    else:
        logger.warning("⚠️  No se pudieron insertar datos de prueba (opcional)")
    
    logger.info("=== Inicialización completada exitosamente ===")
    logger.info("El servicio de familias está listo para usar")

if __name__ == "__main__":
    main()
