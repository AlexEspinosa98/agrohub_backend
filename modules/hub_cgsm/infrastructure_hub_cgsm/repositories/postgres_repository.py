from modules.hub_cgsm.domain_hub_cgsm.entities import EncuestaActores, EncuestaFaena, EncuestaPuntoAcopio, EncuestaMonitoreoAmbiental, Survey
from modules.hub_cgsm.domain_hub_cgsm.repositories import EncuestaRepository
from database.connection import get_db_cursor
from typing import List, Union, Optional
from datetime import date
from psycopg2.extras import execute_values

class PostgresEncuestaRepository(EncuestaRepository):
    def __init__(self):
        self._create_tables()

    def _create_tables(self):
        with get_db_cursor() as cur:
            # Table for EncuestaActores
            cur.execute("""
            CREATE TABLE IF NOT EXISTS encuestas_actores (
                id SERIAL PRIMARY KEY,
                email TEXT,
                fecha_creacion DATE,
                id_actor TEXT UNIQUE,
                nombre_completo TEXT,
                rol_hub TEXT[],
                organizacion TEXT,
                numero_identificacion TEXT,
                contacto TEXT,
                direccion_comunidad TEXT,
                fotografia_actor TEXT,
                id_activo TEXT,
                tipo_activo TEXT[],
                nombre_codigo_activo TEXT,
                propietario_id TEXT,
                numero_serie TEXT,
                estado_activo TEXT,
                permisos_licencias TEXT[],
                fotografia_activo TEXT,
                rol_en_activo TEXT,
                fecha_asignacion DATE,
                observaciones TEXT,
                autorizo_datos BOOLEAN,
                activos_bioseguridad BOOLEAN,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Table for EncuestaFaena
            cur.execute("""
            CREATE TABLE IF NOT EXISTS encuestas_faenas (
                id SERIAL PRIMARY KEY,
                email TEXT,
                id_faena TEXT UNIQUE,
                tipo_faena TEXT,
                fecha_inicio DATE,
                fecha_cierre DATE,
                email_actor TEXT,
                coordinador_faena TEXT,
                punto_inicial_gps TEXT,
                punto_final_gps TEXT,
                nombre_sector TEXT,

                superficie_intervenida DOUBLE PRECISION,
                metodo_utilizado TEXT[],
                numero_personas INT,
                horas_trabajadas DOUBLE PRECISION,
                fotografia_antes TEXT,
                fotografia_despues TEXT,
                checklist_bioseguridad TEXT[],

                biomasa_humeda_kg DOUBLE PRECISION,
                biomasa_seca_kg DOUBLE PRECISION,
                destino_biomasa TEXT[],
                numero_sacos INT,
                punto_acopio_asociado TEXT,
                oxigeno_disuelto_mgL DOUBLE PRECISION,
                turbidez_NTU DOUBLE PRECISION,
                salinidad_prom DOUBLE PRECISION,
                cpue DOUBLE PRECISION,
                incidencias_reportadas TEXT,
                comentarios_comunitarios TEXT,
                firma_digital_coordinador BOOLEAN,
                validacion_institucional TEXT,

                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Table for EncuestaPuntoAcopio
            cur.execute("""
            CREATE TABLE IF NOT EXISTS puntos_acopio_biomasa (
                id SERIAL PRIMARY KEY,
                email TEXT,

                -- Sección A. Identificación del Punto de Acopio
                id_punto TEXT UNIQUE,
                nombre_referencia TEXT,
                tipo_punto TEXT,
                ubicacion TEXT,
                sector_comunidad TEXT,
                fotografia_georreferenciada TEXT,

                -- Sección B. Datos de Biomasa Depositada
                fecha_entrega TIMESTAMP,
                cantidad_humedo_kg DOUBLE PRECISION,
                cantidad_seco_kg DOUBLE PRECISION,
                numero_sacos_unidades INT,
                estado_biomasa TEXT,
                observaciones_biomasa TEXT,

                -- Sección C. Destino y Gestión
                destino_previsto TEXT[], -- Lista de valores
                plazo_permanencia TEXT,
                encargado_gestion TEXT,
                registro_transporte TEXT,
                evidencia_fotografica_documento TEXT,

                -- Sección D. Control y Trazabilidad
                checklist_bioseguridad TEXT[],
                alertas_automaticas BOOLEAN,
                firma_digital_responsable BOOLEAN,
                validacion_institucional TEXT,

                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Table for EncuestaMonitoreoAmbiental
            cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoreos_ambientales (
                id SERIAL PRIMARY KEY,
                email TEXT,
                id_monitoreo TEXT UNIQUE,
                fecha TEXT,
                hora TEXT,
                cuadrilla_equipo_responsable TEXT,
                nombre_sector_punto TEXT,
                ubicacion_gps TEXT,
                fotografia_sitio TEXT,
                oxigeno_disuelto_mg_l TEXT,
                turbidez_ntu TEXT,
                salinidad_prom TEXT,
                ph TEXT,
                temperatura_c TEXT,
                cpue TEXT,
                observaciones_fauna TEXT,
                registro_fotografico_fauna TEXT,
                incidencias_ambientales TEXT,
                comentarios_comunitarios TEXT,
                firma_digital_responsable TEXT,
                validacion_institucional TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

    def save_bulk(self, surveys: List[Survey]) -> List[Survey]:
        with get_db_cursor() as cur:
            actores_to_insert = []
            faenas_to_insert = []
            acopio_to_insert = []
            ambiental_to_insert = []

            for survey in surveys:
                if isinstance(survey, EncuestaActores):
                    actores_to_insert.append((
                        survey.email, survey.fecha_creacion, survey.id_actor, survey.nombre_completo, survey.rol_hub, survey.organizacion,
                        survey.numero_identificacion, survey.contacto, survey.direccion_comunidad, survey.fotografia_actor, survey.id_activo,
                        survey.tipo_activo, survey.nombre_codigo_activo, survey.propietario_id, survey.numero_serie, survey.estado_activo,
                        survey.permisos_licencias, survey.fotografia_activo, survey.rol_en_activo, survey.fecha_asignacion,
                        survey.observaciones, survey.autorizo_datos, survey.activos_bioseguridad
                    ))
                elif isinstance(survey, EncuestaFaena):
                    faenas_to_insert.append((
                        survey.email, survey.id_faena, survey.tipo_faena, survey.fecha_inicio, survey.hora_inicio, survey.fecha_hora_cierre,
                        survey.cuadrilla_responsable, survey.coordinador_faena, survey.punto_inicial_gps, survey.punto_final_gps,
                        survey.nombre_sector, survey.mapa_offline, survey.superficie_intervenida, survey.metodo_utilizado,
                        survey.numero_personas, survey.horas_trabajadas, survey.fotografias_antes_despues, survey.checklist_bioseguridad,
                        survey.biomasa_humeda_kg, survey.biomasa_seca_kg, survey.destino_biomasa, survey.numero_sacos,
                        survey.punto_acopio_asociado, survey.oxigeno_disuelto_mgL, survey.turbidez_NTU, survey.salinidad_prom,
                        survey.cpue, survey.incidencias_reportadas, survey.comentarios_comunitarios, survey.firma_digital_coordinador,
                        survey.validacion_institucional
                    ))
                elif isinstance(survey, EncuestaPuntoAcopio):
                    acopio_to_insert.append((
                        survey.email, survey.id_punto, survey.nombre_referencia, survey.tipo_punto, survey.ubicacion_gps, survey.sector_comunidad,
                        survey.fotografia_georreferenciada, survey.id_faena_asociada, survey.fecha_hora_entrega, survey.cantidad_humedo_kg,
                        survey.cantidad_seco_kg, survey.numero_sacos_unidades, survey.estado_biomasa, survey.observaciones_biomasa,
                        survey.destino_previsto, survey.plazo_permanencia, survey.encargado_gestion, survey.registro_transporte,
                        survey.evidencia_fotografica_documento, survey.checklist_bioseguridad, survey.alertas_automaticas,
                        survey.firma_digital_responsable, survey.validacion_institucional
                    ))
                elif isinstance(survey, EncuestaMonitoreoAmbiental):
                    ambiental_to_insert.append((
                        survey.email, survey.id_monitoreo, survey.fecha, survey.hora, survey.cuadrilla_equipo_responsable, survey.nombre_sector_punto,
                        survey.ubicacion_gps, survey.fotografia_sitio, survey.oxigeno_disuelto_mg_l, survey.turbidez_ntu,
                        survey.salinidad_prom, survey.ph, survey.temperatura_c, survey.cpue, survey.observaciones_fauna,
                        survey.registro_fotografico_fauna, survey.incidencias_ambientales, survey.comentarios_comunitarios,
                        survey.firma_digital_responsable, survey.validacion_institucional
                    ))
            
            if actores_to_insert:
                execute_values(
                    cur,
                    """INSERT INTO encuestas_actores (
                        email, fecha_creacion, id_actor, nombre_completo, rol_hub, organizacion,
                        numero_identificacion, contacto, direccion_comunidad, fotografia_actor, id_activo,
                        tipo_activo, nombre_codigo_activo, propietario_id, numero_serie, estado_activo,
                        permisos_licencias, fotografia_activo, rol_en_activo, fecha_asignacion,
                        observaciones, autorizo_datos, activos_bioseguridad
                    ) VALUES %s""",
                    actores_to_insert
                )

            if faenas_to_insert:
                execute_values(
                    cur,
                    """INSERT INTO encuestas_faenas (
                        email, id_faena, tipo_faena, fecha_inicio, hora_inicio, fecha_hora_cierre,
                        cuadrilla_responsable, coordinador_faena, punto_inicial_gps, punto_final_gps,
                        nombre_sector, mapa_offline, superficie_intervenida, metodo_utilizado,
                        numero_personas, horas_trabajadas, fotografias_antes_despues, checklist_bioseguridad,
                        biomasa_humeda_kg, biomasa_seca_kg, destino_biomasa, numero_sacos,
                        punto_acopio_asociado, oxigeno_disuelto_mgL, turbidez_NTU, salinidad_prom,
                        cpue, incidencias_reportadas, comentarios_comunitarios, firma_digital_coordinador,
                        validacion_institucional
                    ) VALUES %s""",
                    faenas_to_insert
                )

            if acopio_to_insert:
                execute_values(
                    cur,
                    """INSERT INTO puntos_acopio_biomasa (
                        email, id_punto, nombre_referencia, tipo_punto, ubicacion_gps, sector_comunidad,
                        fotografia_georreferenciada, id_faena_asociada, fecha_hora_entrega, cantidad_humedo_kg,
                        cantidad_seco_kg, numero_sacos_unidades, estado_biomasa, observaciones_biomasa,
                        destino_previsto, plazo_permanencia, encargado_gestion, registro_transporte,
                        evidencia_fotografica_documento, checklist_bioseguridad, alertas_automaticas,
                        firma_digital_responsable, validacion_institucional
                    ) VALUES %s""",
                    acopio_to_insert
                )

            if ambiental_to_insert:
                execute_values(
                    cur,
                    """INSERT INTO monitoreos_ambientales (
                        email, id_monitoreo, fecha, hora, cuadrilla_equipo_responsable, nombre_sector_punto,
                        ubicacion_gps, fotografia_sitio, oxigeno_disuelto_mg_l, turbidez_ntu,
                        salinidad_prom, ph, temperatura_c, cpue, observaciones_fauna,
                        registro_fotografico_fauna, incidencias_ambientales, comentarios_comunitarios,
                        firma_digital_responsable, validacion_institucional
                    ) VALUES %s""",
                    ambiental_to_insert
                )

        return surveys

    def get_all(self, page: int, page_size: int, email: Optional[str] = None, survey_type: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, id: Optional[int] = None) -> List[Survey]:
        if not survey_type:
            return []

        offset = (page - 1) * page_size
        params = []

        tables = {
            "actores": ("encuestas_actores", EncuestaActores),
            "faena": ("encuestas_faenas", EncuestaFaena),
            "acopio": ("puntos_acopio_biomasa", EncuestaPuntoAcopio),
            "ambiental": ("monitoreos_ambientales", EncuestaMonitoreoAmbiental),
        }
        
        type_map = {
            "EncuestaActores": "actores",
            "EncuestaFaena": "faena",
            "EncuestaPuntoAcopio": "acopio",
            "EncuestaMonitoreoAmbiental": "ambiental"
        }
        
        lookup_survey_type = type_map.get(survey_type, survey_type)

        if lookup_survey_type not in tables:
            return []

        table_name, model = tables[lookup_survey_type]
        base_query = f"SELECT * FROM {table_name}"
        where_clauses = []
        
        if email:
            where_clauses.append("email = %s")
            params.append(email)
        if start_date:
            where_clauses.append("fecha_registro >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("fecha_registro <= %s")
            params.append(end_date)
        if id:
            where_clauses.append("id = %s")
            params.append(id)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        
        base_query += " ORDER BY fecha_registro DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        with get_db_cursor() as cur:
            cur.execute(base_query, tuple(params))
            rows = cur.fetchall()
            
            results = []
            if not rows:
                return results

            columns = [desc[0] for desc in cur.description]
            for row_tuple in rows:
                row = dict(zip(columns, row_tuple))
                
                results.append(model(**row))
        return results

    def update(self, id: int, survey: Survey) -> Optional[Survey]:
        with get_db_cursor() as cur:
            table_name = None
            model_class = None
            
            if isinstance(survey, EncuestaActores):
                table_name = "encuestas_actores"
                model_class = EncuestaActores
            elif isinstance(survey, EncuestaFaena):
                table_name = "encuestas_faenas"
                model_class = EncuestaFaena
            elif isinstance(survey, EncuestaPuntoAcopio):
                table_name = "puntos_acopio_biomasa"
                model_class = EncuestaPuntoAcopio
            elif isinstance(survey, EncuestaMonitoreoAmbiental):
                table_name = "monitoreos_ambientales"
                model_class = EncuestaMonitoreoAmbiental
            else:
                return None

            survey_data = survey.model_dump(exclude_unset=True, exclude={'id', 'email', 'fecha_registro'})

            if not survey_data:
                return None

            set_clause = ", ".join([f"{key} = %s" for key in survey_data.keys()])
            params = list(survey_data.values())
            params.append(id)

            query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s RETURNING *"
            
            cur.execute(query, tuple(params))
            updated_row_tuple = cur.fetchone()

            if updated_row_tuple:
                updated_row = {desc[0]: val for desc, val in zip(cur.description, updated_row_tuple)}
                return model_class(**updated_row)
            
            return None
    
    def save_actor_survey(self, survey: EncuestaActores) -> EncuestaActores:
        with get_db_cursor() as cur:
            if isinstance(survey, EncuestaActores):
                cur.execute(
                    """INSERT INTO encuestas_actores (
                        email, fecha_creacion, id_actor, nombre_completo, rol_hub, organizacion,
                        numero_identificacion, contacto, direccion_comunidad, fotografia_actor, id_activo,
                        tipo_activo, nombre_codigo_activo, propietario_id, numero_serie, estado_activo,
                        permisos_licencias, fotografia_activo, rol_en_activo, fecha_asignacion,
                        observaciones, autorizo_datos, activos_bioseguridad
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_actor) DO UPDATE SET
                        email = EXCLUDED.email,
                        fecha_creacion = EXCLUDED.fecha_creacion,
                        nombre_completo = EXCLUDED.nombre_completo,
                        rol_hub = EXCLUDED.rol_hub,
                        organizacion = EXCLUDED.organizacion,
                        numero_identificacion = EXCLUDED.numero_identificacion,
                        contacto = EXCLUDED.contacto,
                        direccion_comunidad = EXCLUDED.direccion_comunidad,
                        fotografia_actor = EXCLUDED.fotografia_actor,
                        id_activo = EXCLUDED.id_activo,
                        tipo_activo = EXCLUDED.tipo_activo,
                        nombre_codigo_activo = EXCLUDED.nombre_codigo_activo,
                        propietario_id = EXCLUDED.propietario_id,
                        numero_serie = EXCLUDED.numero_serie,
                        estado_activo = EXCLUDED.estado_activo,
                        permisos_licencias = EXCLUDED.permisos_licencias,
                        fotografia_activo = EXCLUDED.fotografia_activo,
                        rol_en_activo = EXCLUDED.rol_en_activo,
                        fecha_asignacion = EXCLUDED.fecha_asignacion,
                        observaciones = EXCLUDED.observaciones,
                        autorizo_datos = EXCLUDED.autorizo_datos,
                        activos_bioseguridad = EXCLUDED.activos_bioseguridad
                    """,
                    (
                        survey.email, survey.fecha_creacion, survey.id_actor, survey.nombre_completo, survey.rol_hub, survey.organizacion,
                        survey.numero_identificacion, survey.contacto, survey.direccion_comunidad, survey.fotografia_actor, survey.id_activo,
                        survey.tipo_activo, survey.nombre_codigo_activo, survey.propietario_id, survey.numero_serie, survey.estado_activo,
                        survey.permisos_licencias, survey.fotografia_activo, survey.rol_en_activo, survey.fecha_asignacion,
                        survey.observaciones, survey.autorizo_datos, survey.activos_bioseguridad
                    )
                )
        return survey
        
    def save_faena_survey(self, survey: EncuestaFaena) -> EncuestaFaena:
        with get_db_cursor() as cur:
            if isinstance(survey, EncuestaFaena):
                cur.execute(
                    """INSERT INTO encuestas_faenas (
                        email, id_faena, tipo_faena, fecha_inicio, fecha_cierre, email_actor, coordinador_faena,
                        punto_inicial_gps, punto_final_gps, nombre_sector, superficie_intervenida, metodo_utilizado,
                        numero_personas, horas_trabajadas, fotografia_antes, fotografia_despues, checklist_bioseguridad,
                        biomasa_humeda_kg, biomasa_seca_kg, destino_biomasa, numero_sacos, punto_acopio_asociado,
                        oxigeno_disuelto_mgL, turbidez_NTU, salinidad_prom, cpue, incidencias_reportadas,
                        comentarios_comunitarios, firma_digital_coordinador, validacion_institucional
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id_faena) DO UPDATE SET
                        email = EXCLUDED.email,
                        tipo_faena = EXCLUDED.tipo_faena,
                        fecha_inicio = EXCLUDED.fecha_inicio,
                        fecha_cierre = EXCLUDED.fecha_cierre,
                        email_actor = EXCLUDED.email_actor,
                        coordinador_faena = EXCLUDED.coordinador_faena,
                        punto_inicial_gps = EXCLUDED.punto_inicial_gps,
                        punto_final_gps = EXCLUDED.punto_final_gps,
                        nombre_sector = EXCLUDED.nombre_sector,
                        superficie_intervenida = EXCLUDED.superficie_intervenida,
                        metodo_utilizado = EXCLUDED.metodo_utilizado,
                        numero_personas = EXCLUDED.numero_personas,
                        horas_trabajadas = EXCLUDED.horas_trabajadas,
                        fotografia_antes = EXCLUDED.fotografia_antes,
                        fotografia_despues = EXCLUDED.fotografia_despues,
                        checklist_bioseguridad = EXCLUDED.checklist_bioseguridad,
                        biomasa_humeda_kg = EXCLUDED.biomasa_humeda_kg,
                        biomasa_seca_kg = EXCLUDED.biomasa_seca_kg,
                        destino_biomasa = EXCLUDED.destino_biomasa,
                        numero_sacos = EXCLUDED.numero_sacos,
                        punto_acopio_asociado = EXCLUDED.punto_acopio_asociado,
                        oxigeno_disuelto_mgL = EXCLUDED.oxigeno_disuelto_mgL,
                        turbidez_NTU = EXCLUDED.turbidez_NTU,
                        salinidad_prom = EXCLUDED.salinidad_prom,
                        cpue = EXCLUDED.cpue,
                        incidencias_reportadas = EXCLUDED.incidencias_reportadas,
                        comentarios_comunitarios = EXCLUDED.comentarios_comunitarios,
                        firma_digital_coordinador = EXCLUDED.firma_digital_coordinador,
                        validacion_institucional = EXCLUDED.validacion_institucional
                    """,
                    (
                        survey.email, survey.id_faena, survey.tipo_faena, survey.fecha_inicio, survey.fecha_cierre, survey.email_actor, survey.coordinador_faena,
                        survey.punto_inicial_gps, survey.punto_final_gps, survey.nombre_sector, survey.superficie_intervenida, survey.metodo_utilizado,
                        survey.numero_personas, survey.horas_trabajadas, survey.fotografia_antes, survey.fotografia_despues, survey.checklist_bioseguridad,
                        survey.biomasa_humeda_kg, survey.biomasa_seca_kg, survey.destino_biomasa, survey.numero_sacos, survey.punto_acopio_asociado,
                        survey.oxigeno_disuelto_mgL, survey.turbidez_NTU, survey.salinidad_prom, survey.cpue, survey.incidencias_reportadas,
                        survey.comentarios_comunitarios, survey.firma_digital_coordinador, survey.validacion_institucional
                    )
                )
        return survey

    def save_punto_acopio_survey(self, survey: EncuestaPuntoAcopio) -> EncuestaPuntoAcopio:
        with get_db_cursor() as cur:
            if isinstance(survey, EncuestaPuntoAcopio):
                cur.execute(
                    """INSERT INTO puntos_acopio_biomasa (
                        email, id_punto, nombre_referencia, tipo_punto, ubicacion, sector_comunidad,
                        fotografia_georreferenciada, fecha_entrega, cantidad_humedo_kg, cantidad_seco_kg,
                        numero_sacos_unidades, estado_biomasa, observaciones_biomasa, destino_previsto,
                        plazo_permanencia, encargado_gestion, registro_transporte, evidencia_fotografica_documento,
                        checklist_bioseguridad, alertas_automaticas, firma_digital_responsable, validacion_institucional
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (id_punto) DO UPDATE SET
                        email = EXCLUDED.email,
                        nombre_referencia = EXCLUDED.nombre_referencia,
                        tipo_punto = EXCLUDED.tipo_punto,
                        ubicacion = EXCLUDED.ubicacion,
                        sector_comunidad = EXCLUDED.sector_comunidad,
                        fotografia_georreferenciada = EXCLUDED.fotografia_georreferenciada,
                        fecha_entrega = EXCLUDED.fecha_entrega,
                        cantidad_humedo_kg = EXCLUDED.cantidad_humedo_kg,
                        cantidad_seco_kg = EXCLUDED.cantidad_seco_kg,
                        numero_sacos_unidades = EXCLUDED.numero_sacos_unidades,
                        estado_biomasa = EXCLUDED.estado_biomasa,
                        observaciones_biomasa = EXCLUDED.observaciones_biomasa,
                        destino_previsto = EXCLUDED.destino_previsto,
                        plazo_permanencia = EXCLUDED.plazo_permanencia,
                        encargado_gestion = EXCLUDED.encargado_gestion,
                        registro_transporte = EXCLUDED.registro_transporte,
                        evidencia_fotografica_documento = EXCLUDED.evidencia_fotografica_documento,
                        checklist_bioseguridad = EXCLUDED.checklist_bioseguridad,
                        alertas_automaticas = EXCLUDED.alertas_automaticas,
                        firma_digital_responsable = EXCLUDED.firma_digital_responsable,
                        validacion_institucional = EXCLUDED.validacion_institucional
                    """,
                    (
                        survey.email, survey.id_punto, survey.nombre_referencia, survey.tipo_punto, survey.ubicacion, survey.sector_comunidad,
                        survey.fotografia_georreferenciada, survey.fecha_entrega, survey.cantidad_humedo_kg, survey.cantidad_seco_kg,
                        survey.numero_sacos_unidades, survey.estado_biomasa, survey.observaciones_biomasa, survey.destino_previsto,
                        survey.plazo_permanencia, survey.encargado_gestion, survey.registro_transporte, survey.evidencia_fotografica_documento,
                        survey.checklist_bioseguridad, survey.alertas_automaticas, survey.firma_digital_responsable, survey.validacion_institucional
                    )
                )
        return survey