from data_characterization.domain.entities import EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario, SurveyLocationInfo
from data_characterization.domain.repositories import EncuestaRepository
from database.connection import get_db_cursor
from typing import List, Union, Optional
from datetime import date

class PostgresEncuestaRepository(EncuestaRepository):
    def __init__(self):
        self._create_tables()

    def _create_tables(self):
        with get_db_cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS encuestas_agrohub (
    id SERIAL PRIMARY KEY,
    
    -- Metadatos
    nombre_aplicador TEXT,
    fecha_aplicacion DATE,
    municipio TEXT,
    vereda TEXT,
    nombre_organizacion TEXT,
    tipo_organizacion TEXT, -- texto plano: Asociación campesina, Consejo, Otra...

    -- 1. Información Generalya subo
    anio_conformacion INT,
    numero_miembros INT,
    numero_nucleos_familiares INT,
    cobertura_territorial TEXT,
    representante_legal TEXT,
    contacto TEXT,

    -- 2. Perfil Productivo y Agroecológico
    tipos_agricultura TEXT, -- lista separada por comas
    cultivan_hortalizas TEXT,
    cuales_hortalizas TEXT,
    area_hortalizas INT,
    destino_hortalizas TEXT,
    actividades_complementarias TEXT, -- lista separada por comas
    tiene_patio TEXT,
    area_patio INT,
    condiciones_terreno TEXT, -- lista separada por comas

    -- 3. Madurez Organizativa
    formalizacion TEXT,
    asociatividad TEXT,
    experiencia_proyectos TEXT,
    descripcion_experiencia TEXT,
    tiene_estatutos_plan TEXT,
    acceso_mercado TEXT, -- lista separada por comas
    frecuencia_venta TEXT,
    manejo_administrativo TEXT,

    -- 4. Apropiación Tecnológica
    tecnologias_usadas TEXT, -- lista separada por comas
    otras_tecnologias TEXT,
    capacidad_aprendizaje TEXT,
    comentarios TEXT,
    conectividad TEXT,

    -- 5. Perspectivas
    expectativas TEXT,
    compromisos TEXT,
    limitaciones TEXT,
                        
    -- 6. geolocalización
    latitud TEXT,
    longitud TEXT,

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""")
            cur.execute("""CREATE TABLE IF NOT EXISTS encuestas_educativas (
    id SERIAL PRIMARY KEY,

    -- Metadatos
    nombre_aplicador TEXT,
    fecha_aplicacion DATE,
    municipio TEXT,
    vereda TEXT,
    nombre_institucion TEXT,
    codigo_dane TEXT,
    nombre_directivo TEXT,
    contacto TEXT,

    -- 1. Información General
    tipo_institucion TEXT,
    sedes TEXT,
    numero_estudiantes INT,
    numero_docentes INT,
    grados_atiende TEXT, -- lista: Preescolar,Básica primaria,etc.
    tiene_prae BOOLEAN,
    prae_descripcion TEXT,

    -- 2. Experiencia y Enfoque
    experiencia_proyectos BOOLEAN,
    descripcion_proyectos TEXT,
    tiene_huerta BOOLEAN,
    area_huerta INT,
    uso_huerta TEXT, -- lista: Formativo, Alimentario, etc.
    temas_agroambientales TEXT, -- lista

    -- 3. Infraestructura
    espacio_agrohub BOOLEAN,
    area_agrohub INT,
    condiciones_terreno TEXT, -- lista
    internet TEXT, -- Sí, No, Intermitente
    espacios_complementarios BOOLEAN,
    cantidad_espacios INT,
    laboratorio BOOLEAN,
    laboratorio_funciona BOOLEAN,

    -- 4. Vinculación Comunitaria
    actores_comunitarios TEXT, -- lista
    tiene_alianzas BOOLEAN,
    descripcion_alianzas TEXT,

    -- 5. Capacidades de Innovación
    tiene_semilleros BOOLEAN,
    nombre_grupo TEXT,
    interes_agricultura TEXT, -- Alto, Medio, Bajo
    medios_comunicacion TEXT, -- lista

    -- 6. Expectativas
    expectativas TEXT,
    compromisos TEXT,
    limitaciones TEXT,

    -- 7. Observaciones Finales
    comentarios TEXT,
    anexa_documentos BOOLEAN,
                        
    -- 8. geolocalización
    latitud TEXT,
    longitud TEXT,

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS encuestas_derecho_humano_alimentario (
                id SERIAL PRIMARY KEY,

                -- Metadatos y datos generales
                fecha_aplicacion DATE,
                nombre_jefe_hogar TEXT,
                edad INT,
                genero TEXT, -- 'Hombre', 'Mujer'
                departamento TEXT, -- si lo vas a dejar fijo 'Magdalena', sino quitar
                municipio TEXT,
                subregion TEXT,
                numero_miembros_hogar INT,
                nivel_educativo TEXT, -- opciones: Sin educación formal, Primaria incompleta, etc.
                nombre_encuestador TEXT,
                cargo_encuestador TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email TEXT,

                -- Agricultura Familiar
                dedicado_agricultura BOOLEAN,
                cultivos_principales TEXT, -- lista de cultivos seleccionados
                razon_produccion TEXT, -- lista de razones (consumo, venta, etc.)

                -- Disponibilidad de alimentos
                cobertura_necesidades BOOLEAN, -- producción suficiente todo el año
                meses_escasez TEXT, -- lista de meses
                cambios_produccion TEXT, -- 'Aumentado', 'Igual', 'Disminuido'
                razon_cambios TEXT, -- lista de causas
                acceso_insumos_agricolas BOOLEAN,
                asistencia_tecnica BOOLEAN,

                -- Accesibilidad a alimentos
                compra_suficiente_alimentos BOOLEAN,
                acceso_mercado BOOLEAN,
                distancia_mercado TEXT, -- ej: '33km', '20min'
                alimento_asequible BOOLEAN,
                reduccion_consumo BOOLEAN,
                ayuda_alimentaria BOOLEAN,

                -- Adecuación de alimentos
                dieta_balanceada BOOLEAN,
                consumo_grupos_alimenticios TEXT, -- objeto con frecuencias: frutas, proteínas, cereales
                agua_potable_preparacion BOOLEAN,
                enfermedades_transmitidas BOOLEAN,
                alimentos_culturalmente_aceptables BOOLEAN,
                higiene_manipulacion BOOLEAN,

                -- Percepción y conocimiento
                conoce_derecho_alimentacion BOOLEAN,
                cree_derecho_respetado BOOLEAN,
                medidas_mejorar_acceso TEXT, -- lista de medidas seleccionadas

                -- Geolocalización
                latitud TEXT,
                longitud TEXT
            );
            """)

            cur.execute("""ALTER TABLE encuestas_agrohub ADD COLUMN IF NOT EXISTS email TEXT;""")
            cur.execute("""ALTER TABLE encuestas_educativas ADD COLUMN IF NOT EXISTS email TEXT;""")
            cur.execute("""ALTER TABLE encuestas_derecho_humano_alimentario ADD COLUMN IF NOT EXISTS email TEXT;""")

    def save_bulk(self, surveys: List[Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]]) -> List[Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]]:
        with get_db_cursor() as cur:
            for survey in surveys:
                if isinstance(survey, EncuestaAgrohub):
                    sql = """
                        INSERT INTO encuestas_agrohub (
                            email, nombre_aplicador, fecha_aplicacion, municipio, vereda, nombre_organizacion, tipo_organizacion,
                            anio_conformacion, numero_miembros, numero_nucleos_familiares, cobertura_territorial, representante_legal, contacto,
                            tipos_agricultura, cultivan_hortalizas, cuales_hortalizas, area_hortalizas, destino_hortalizas, actividades_complementarias, tiene_patio, area_patio, condiciones_terreno,
                            formalizacion, asociatividad, experiencia_proyectos, descripcion_experiencia, tiene_estatutos_plan, acceso_mercado, frecuencia_venta, manejo_administrativo,
                            tecnologias_usadas, otras_tecnologias, capacidad_aprendizaje, comentarios, conectividad,
                            expectativas, compromisos, limitaciones, latitud, longitud
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, fecha_creacion;
                    """
                    params = (
                        survey.email, survey.nombre_aplicador, survey.fecha_aplicacion, survey.municipio, survey.vereda, survey.nombre_organizacion, survey.tipo_organizacion,
                        survey.anio_conformacion, survey.numero_miembros, survey.numero_nucleos_familiares, survey.cobertura_territorial, survey.representante_legal, survey.contacto,
                        survey.tipos_agricultura, survey.cultivan_hortalizas, survey.cuales_hortalizas, survey.area_hortalizas, survey.destino_hortalizas, survey.actividades_complementarias, survey.tiene_patio, survey.area_patio, survey.condiciones_terreno,
                        survey.formalizacion, survey.asociatividad, survey.experiencia_proyectos, survey.descripcion_experiencia, survey.tiene_estatutos_plan, survey.acceso_mercado, survey.frecuencia_venta, survey.manejo_administrativo,
                        survey.tecnologias_usadas, survey.otras_tecnologias, survey.capacidad_aprendizaje, survey.comentarios, survey.conectividad,
                        survey.expectativas, survey.compromisos, survey.limitaciones, survey.latitud, survey.longitud
                    )
                    cur.execute(sql, params)
                elif isinstance(survey, EncuestaEducativa):
                    sql = """
                        INSERT INTO encuestas_educativas (
                            email, nombre_aplicador, fecha_aplicacion, municipio, vereda, nombre_institucion, codigo_dane, nombre_directivo, contacto,
                            tipo_institucion, sedes, numero_estudiantes, numero_docentes, grados_atiende, tiene_prae, prae_descripcion,
                            experiencia_proyectos, descripcion_proyectos, tiene_huerta, area_huerta, uso_huerta, temas_agroambientales,
                            espacio_agrohub, area_agrohub, condiciones_terreno, internet, espacios_complementarios, cantidad_espacios, laboratorio, laboratorio_funciona,
                            actores_comunitarios, tiene_alianzas, descripcion_alianzas,
                            tiene_semilleros, nombre_grupo, interes_agricultura, medios_comunicacion,
                            expectativas, compromisos, limitaciones, 
                            comentarios, anexa_documentos,
                            latitud, longitud
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )
                        RETURNING id, fecha_creacion;
                    """
                    params = (
                        survey.email, survey.nombre_aplicador, survey.fecha_aplicacion, survey.municipio, survey.vereda, survey.nombre_institucion, survey.codigo_dane, survey.nombre_directivo, survey.contacto,
                        survey.tipo_institucion, survey.sedes, survey.numero_estudiantes, survey.numero_docentes, survey.grados_atiende, survey.tiene_prae, survey.prae_descripcion,
                        survey.experiencia_proyectos, survey.descripcion_proyectos, survey.tiene_huerta, survey.area_huerta, survey.uso_huerta, survey.temas_agroambientales,
                        survey.espacio_agrohub, survey.area_agrohub, survey.condiciones_terreno, survey.internet, survey.espacios_complementarios, survey.cantidad_espacios, survey.laboratorio, survey.laboratorio_funciona,
                        survey.actores_comunitarios, survey.tiene_alianzas, survey.descripcion_alianzas,
                        survey.tiene_semilleros, survey.nombre_grupo, survey.interes_agricultura, survey.medios_comunicacion,
                        survey.expectativas, survey.compromisos, survey.limitaciones,
                        survey.comentarios, survey.anexa_documentos,
                        survey.latitud, survey.longitud
                    )
                    cur.execute(sql, params)
                elif isinstance(survey, EncuestaDerechoHumanoAlimentario):
                    sql = """
                        INSERT INTO encuestas_derecho_humano_alimentario (
                            email, fecha_aplicacion, nombre_jefe_hogar, edad, genero, departamento, municipio, subregion,
                            numero_miembros_hogar, nivel_educativo, nombre_encuestador, cargo_encuestador,
                            dedicado_agricultura, cultivos_principales, razon_produccion,
                            cobertura_necesidades, meses_escasez, cambios_produccion, razon_cambios,
                            acceso_insumos_agricolas, asistencia_tecnica,
                            compra_suficiente_alimentos, acceso_mercado, distancia_mercado,
                            alimento_asequible, reduccion_consumo, ayuda_alimentaria,
                            dieta_balanceada, consumo_grupos_alimenticios, agua_potable_preparacion,
                            enfermedades_transmitidas, alimentos_culturalmente_aceptables, higiene_manipulacion,
                            conoce_derecho_alimentacion, cree_derecho_respetado, medidas_mejorar_acceso,
                            latitud, longitud
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s
                        )
                        RETURNING id, fecha_creacion;
                    """

                    params = (
                        survey.email, survey.fecha_aplicacion, survey.nombre_jefe_hogar, survey.edad, survey.genero, survey.departamento, survey.municipio, survey.subregion,
                        survey.numero_miembros_hogar, survey.nivel_educativo, survey.nombre_encuestador, survey.cargo_encuestador,
                        survey.dedicado_agricultura, survey.cultivos_principales, survey.razon_produccion,
                        survey.cobertura_necesidades, survey.meses_escasez, survey.cambios_produccion, survey.razon_cambios,
                        survey.acceso_insumos_agricolas, survey.asistencia_tecnica,
                        survey.compra_suficiente_alimentos, survey.acceso_mercado, survey.distancia_mercado,
                        survey.alimento_asequible, survey.reduccion_consumo, survey.ayuda_alimentaria,
                        survey.dieta_balanceada, survey.consumo_grupos_alimenticios, survey.agua_potable_preparacion,
                        survey.enfermedades_transmitidas, survey.alimentos_culturalmente_aceptables, survey.higiene_manipulacion,
                        survey.conoce_derecho_alimentacion, survey.cree_derecho_respetado, survey.medidas_mejorar_acceso,
                        survey.latitud, survey.longitud
                    )
                    cur.execute(sql, params)
            return surveys

    def get_all(
        self,
        page: int,
        page_size: int,
        email: Optional[str] = None,
        survey_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        id: Optional[int] = None
    ) -> List[Union[EncuestaAgrohub, EncuestaEducativa]]:

        with get_db_cursor() as cur:
            # --- columnas ---
            agrohub_table_cols = {
                "id", "email", "nombre_aplicador", "fecha_aplicacion", "municipio", "vereda",
                "nombre_organizacion", "tipo_organizacion", "anio_conformacion", "numero_miembros",
                "numero_nucleos_familiares", "cobertura_territorial", "representante_legal", "contacto",
                "tipos_agricultura", "cultivan_hortalizas", "cuales_hortalizas", "area_hortalizas",
                "destino_hortalizas", "actividades_complementarias", "tiene_patio", "area_patio",
                "condiciones_terreno", "formalizacion", "asociatividad", "experiencia_proyectos",
                "descripcion_experiencia", "tiene_estatutos_plan", "acceso_mercado", "frecuencia_venta",
                "manejo_administrativo", "tecnologias_usadas", "otras_tecnologias", "capacidad_aprendizaje",
                "comentarios", "conectividad", "expectativas", "compromisos", "limitaciones", "fecha_creacion",
                "latitud", "longitud",
            }

            educativa_table_cols = {
                "id", "email", "nombre_aplicador", "fecha_aplicacion", "municipio", "vereda",
                "nombre_institucion", "codigo_dane", "nombre_directivo", "contacto",
                "tipo_institucion", "sedes", "numero_estudiantes", "numero_docentes",
                "grados_atiende", "tiene_prae", "prae_descripcion", "experiencia_proyectos",
                "descripcion_proyectos", "tiene_huerta", "area_huerta", "uso_huerta",
                "temas_agroambientales", "espacio_agrohub", "area_agrohub", "condiciones_terreno",
                "internet", "espacios_complementarios", "cantidad_espacios", "laboratorio",
                "laboratorio_funciona", "actores_comunitarios", "tiene_alianzas", "descripcion_alianzas",
                "tiene_semilleros", "nombre_grupo", "interes_agricultura", "medios_comunicacion",
                "comentarios", "anexa_documentos", "fecha_creacion", "expectativas", "compromisos", "limitaciones",
                "latitud", "longitud"
            }

            alimentaria_table_cols = {
                "id", "email", "fecha_aplicacion", "nombre_jefe_hogar", "edad", "genero",
                "departamento", "municipio", "subregion", "numero_miembros_hogar",
                "nivel_educativo", "nombre_encuestador", "cargo_encuestador",
                "dedicado_agricultura", "cultivos_principales", "razon_produccion",
                "cobertura_necesidades", "meses_escasez", "cambios_produccion", "razon_cambios",
                "acceso_insumos_agricolas", "asistencia_tecnica",
                "compra_suficiente_alimentos", "acceso_mercado", "distancia_mercado",
                "alimento_asequible", "reduccion_consumo", "ayuda_alimentaria",
                "dieta_balanceada", "consumo_grupos_alimenticios", "agua_potable_preparacion",
                "enfermedades_transmitidas", "alimentos_culturalmente_aceptables", "higiene_manipulacion",
                "conoce_derecho_alimentacion", "cree_derecho_respetado", "medidas_mejorar_acceso",
                "fecha_creacion", "latitud", "longitud"
            }

            # CAMPOS BOOLEAN ESPECÍFICOS DE CADA TABLA - MÁS PRECISIÓN

            
            educativa_boolean_cols = {
                "tiene_prae", "experiencia_proyectos", "tiene_huerta", "espacio_agrohub",
                "espacios_complementarios", "laboratorio", "laboratorio_funciona",
                "tiene_alianzas", "tiene_semilleros", "anexa_documentos"
            }
            
            # CAMPOS BOOLEAN PROBLEMÁTICOS DE LA TABLA ALIMENTARIA
            alimentaria_boolean_cols = {
                "dedicado_agricultura", "cobertura_necesidades", "acceso_insumos_agricolas", "asistencia_tecnica",
                "compra_suficiente_alimentos", "acceso_mercado", "alimento_asequible", "reduccion_consumo",
                "ayuda_alimentaria", "dieta_balanceada", "agua_potable_preparacion", "enfermedades_transmitidas",
                "alimentos_culturalmente_aceptables", "higiene_manipulacion", "conoce_derecho_alimentacion",
                "cree_derecho_respetado"
            }

            # TODOS LOS BOOLEAN JUNTOS
            all_boolean_cols = educativa_boolean_cols.union(alimentaria_boolean_cols)

            # CAMPOS ENTEROS
            integer_cols = {
                "id", "anio_conformacion", "numero_miembros", "numero_nucleos_familiares", 
                "area_hortalizas", "area_patio", "numero_estudiantes", "numero_docentes", 
                "area_huerta", "area_agrohub", "cantidad_espacios", "edad", "numero_miembros_hogar"
            }

            timestamp_cols = {"fecha_creacion"}
            date_cols = {"fecha_aplicacion"}

            # FUNCIÓN PARA CREAR CASTING SEGURO DE BOOLEAN
            def safe_boolean_cast(alias: str, col: str) -> str:
                return f"""
                CASE 
                    WHEN {alias}.{col} IS NULL THEN NULL
                    WHEN {alias}.{col} = TRUE THEN 'true'
                    WHEN {alias}.{col} = FALSE THEN 'false'
                    ELSE NULL
                END::TEXT AS {col}
                """.strip()

            def safe_integer_cast(alias: str, col: str) -> str:
                return f"""
                CASE 
                    WHEN {alias}.{col} IS NULL THEN NULL
                    WHEN {alias}.{col}::TEXT ~ '^-?[0-9]+$' THEN {alias}.{col}::INTEGER
                    ELSE NULL
                END AS {col}
                """.strip()

            def build_select(alias: str, table_cols: set) -> str:
                parts = []
                for col in sorted(table_cols):
                    if col in all_boolean_cols:
                        parts.append(safe_boolean_cast(alias, col))
                    elif col in integer_cols:
                        parts.append(safe_integer_cast(alias, col))
                    elif col in timestamp_cols:
                        parts.append(f"{alias}.{col}::TIMESTAMP AS {col}")
                    elif col in date_cols:
                        parts.append(f"{alias}.{col}::DATE AS {col}")
                    else:
                        parts.append(f"{alias}.{col}::TEXT AS {col}")
                return ", ".join(parts)

            # --- si hay tipo específico ---
            if survey_type == "agrohub":
                select_sql = build_select("T1", agrohub_table_cols)
                base_sql = f"SELECT {select_sql}, 'agrohub' AS type FROM encuestas_agrohub T1"
                model_class = EncuestaAgrohub

            elif survey_type == "educativa":
                select_sql = build_select("T2", educativa_table_cols)
                base_sql = f"SELECT {select_sql}, 'educativa' AS type FROM encuestas_educativas T2"
                model_class = EncuestaEducativa

            elif survey_type == "derecho_humano_alimentario":
                select_sql = build_select("T3", alimentaria_table_cols)
                base_sql = f"SELECT {select_sql}, 'derecho_humano_alimentario' AS type FROM encuestas_derecho_humano_alimentario T3"
                model_class = EncuestaDerechoHumanoAlimentario

            else:
                # --- UNION ALL de las tres ---
                full_cols = sorted(list(agrohub_table_cols.union(educativa_table_cols).union(alimentaria_table_cols)))
                agrohub_select, educativa_select, alimentaria_select = [], [], []

                for col in full_cols:
                    # AGROHUB
                    if col in agrohub_table_cols:
                        if col in all_boolean_cols:
                            agrohub_select.append(f"T1.{col}::TEXT AS {col}")
                        elif col in integer_cols:
                            agrohub_select.append(safe_integer_cast("T1", col))
                        elif col in timestamp_cols:
                            agrohub_select.append(f"T1.{col}::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            agrohub_select.append(f"T1.{col}::DATE AS {col}")
                        else:
                            agrohub_select.append(f"T1.{col}::TEXT AS {col}")
                    else:
                        if col in all_boolean_cols:
                            agrohub_select.append(f"NULL::TEXT AS {col}")
                        elif col in integer_cols:
                            agrohub_select.append(f"NULL::INTEGER AS {col}")
                        elif col in timestamp_cols:
                            agrohub_select.append(f"NULL::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            agrohub_select.append(f"NULL::DATE AS {col}")
                        else:
                            agrohub_select.append(f"NULL::TEXT AS {col}")

                    # EDUCATIVA
                    if col in educativa_table_cols:
                        if col in all_boolean_cols:
                            educativa_select.append(safe_boolean_cast("T2", col))
                        elif col in integer_cols:
                            educativa_select.append(safe_integer_cast("T2", col))
                        elif col in timestamp_cols:
                            educativa_select.append(f"T2.{col}::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            educativa_select.append(f"T2.{col}::DATE AS {col}")
                        else:
                            educativa_select.append(f"T2.{col}::TEXT AS {col}")
                    else:
                        if col in all_boolean_cols:
                            educativa_select.append(f"NULL::TEXT AS {col}")
                        elif col in integer_cols:
                            educativa_select.append(f"NULL::INTEGER AS {col}")
                        elif col in timestamp_cols:
                            educativa_select.append(f"NULL::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            educativa_select.append(f"NULL::DATE AS {col}")
                        else:
                            educativa_select.append(f"NULL::TEXT AS {col}")

                    # ALIMENTARIA
                    if col in alimentaria_table_cols:
                        if col in all_boolean_cols:
                            alimentaria_select.append(safe_boolean_cast("T3", col))
                        elif col in integer_cols:
                            alimentaria_select.append(safe_integer_cast("T3", col))
                        elif col in timestamp_cols:
                            alimentaria_select.append(f"T3.{col}::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            alimentaria_select.append(f"T3.{col}::DATE AS {col}")
                        else:
                            alimentaria_select.append(f"T3.{col}::TEXT AS {col}")
                    else:
                        if col in all_boolean_cols:
                            alimentaria_select.append(f"NULL::TEXT AS {col}")
                        elif col in integer_cols:
                            alimentaria_select.append(f"NULL::INTEGER AS {col}")
                        elif col in timestamp_cols:
                            alimentaria_select.append(f"NULL::TIMESTAMP AS {col}")
                        elif col in date_cols:
                            alimentaria_select.append(f"NULL::DATE AS {col}")
                        else:
                            alimentaria_select.append(f"NULL::TEXT AS {col}")

                agrohub_sql = f"SELECT {', '.join(agrohub_select)}, 'agrohub' AS type FROM encuestas_agrohub T1"
                educativa_sql = f"SELECT {', '.join(educativa_select)}, 'educativa' AS type FROM encuestas_educativas T2"
                alimentaria_sql = f"SELECT {', '.join(alimentaria_select)}, 'derecho_humano_alimentario' AS type FROM encuestas_derecho_humano_alimentario T3"
                base_sql = f"{agrohub_sql} UNION ALL {educativa_sql} UNION ALL {alimentaria_sql}"
                model_class = None

            # --- filtros ---
            where_clauses, params = [], []

            if not survey_type and (email or start_date or end_date or id):
                if email:
                    where_clauses.append("email = %s")
                    params.append(email)
                if start_date:
                    where_clauses.append("fecha_creacion >= %s")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("fecha_creacion <= %s")
                    params.append(end_date)
                if id:
                    where_clauses.append("id = %s")
                    params.append(id)

                full_query = f"SELECT * FROM ({base_sql}) AS unified_data"
                if where_clauses:
                    full_query += " WHERE " + " AND ".join(where_clauses)
            else:
                if email:
                    where_clauses.append("email = %s")
                    params.append(email)
                if start_date:
                    where_clauses.append("fecha_creacion >= %s")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("fecha_creacion <= %s")
                    params.append(end_date)
                if id:
                    where_clauses.append("id = %s")
                    params.append(id)

                full_query = base_sql
                if where_clauses:
                    full_query += " WHERE " + " AND ".join(where_clauses)

            cur.execute(full_query, tuple(params))
            rows = cur.fetchall()
            return rows


    def update(self, id: int, survey: Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]) -> Optional[Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]]:
        with get_db_cursor() as cur:
            if isinstance(survey, EncuestaAgrohub):
                table_name = "encuestas_agrohub"
                model_class = EncuestaAgrohub
            elif isinstance(survey, EncuestaEducativa):
                table_name = "encuestas_educativas"
                model_class = EncuestaEducativa
            elif isinstance(survey, EncuestaDerechoHumanoAlimentario):
                table_name = "encuestas_derecho_humano_alimentario"
                model_class = EncuestaDerechoHumanoAlimentario
            else:
                return None

            survey_data = survey.model_dump(exclude_unset=True, exclude={'id', 'type', 'fecha_creacion', 'email'})

            if not survey_data:
                return None

            set_clause = ", ".join([f"{key} = %s" for key in survey_data.keys()])
            params = list(survey_data.values())
            params.append(id)

            query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s RETURNING *"
            cur.execute(query, tuple(params))
            updated_row = cur.fetchone()

            if updated_row:
                if not isinstance(updated_row, dict):
                    updated_row = {desc[0]: val for desc, val in zip(cur.description, updated_row)}
                
                if 'type' not in updated_row:
                    updated_row['type'] = survey.type

                return model_class(**updated_row)
            
            return None

    def get_all_locations(self) -> List[SurveyLocationInfo]:
        with get_db_cursor() as cur:
            query = """
                SELECT 'agrohub' as type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_agrohub WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != ''
                UNION ALL
                SELECT 'instituciones educativas' as type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_educativas WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != ''
                UNION ALL
                SELECT 'caracterizacion agro-alimentaria' as type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_derecho_humano_alimentario WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != '';
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append(SurveyLocationInfo(
                    type=row['type'],
                    latitud=row['latitud'],
                    longitud=row['longitud'],
                    municipio=row['municipio'],
                    fecha_aplicacion=row['fecha_aplicacion']
                ))
            return results
