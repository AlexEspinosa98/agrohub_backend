from datetime import date
from typing import List, Optional, Union

from data_characterization.domain.entities import (
    EncuestaAgrohub,
    EncuestaEducativa,
    EncuestaDerechoHumanoAlimentario,
    SurveyLocationInfo,
)
from data_characterization.domain.repositories import EncuestaRepository
from database.connection import get_db_cursor

SurveyType = Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]


class PostgresEncuestaRepository(EncuestaRepository):
    """Repositorio MySQL para encuestas (nombre legado mantenido para compatibilidad)."""

    def __init__(self):
        self._create_tables()

    def _create_tables(self):
        with get_db_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS encuestas_agrohub (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email TEXT,
                    nombre_aplicador TEXT,
                    fecha_aplicacion DATE,
                    municipio TEXT,
                    vereda TEXT,
                    nombre_organizacion TEXT,
                    tipo_organizacion TEXT,
                    anio_conformacion INT,
                    numero_miembros INT,
                    numero_nucleos_familiares INT,
                    cobertura_territorial TEXT,
                    representante_legal TEXT,
                    contacto TEXT,
                    tipos_agricultura TEXT,
                    cultivan_hortalizas TEXT,
                    cuales_hortalizas TEXT,
                    area_hortalizas INT,
                    destino_hortalizas TEXT,
                    actividades_complementarias TEXT,
                    tiene_patio TEXT,
                    area_patio INT,
                    condiciones_terreno TEXT,
                    formalizacion TEXT,
                    asociatividad TEXT,
                    experiencia_proyectos TEXT,
                    descripcion_experiencia TEXT,
                    tiene_estatutos_plan TEXT,
                    acceso_mercado TEXT,
                    frecuencia_venta TEXT,
                    manejo_administrativo TEXT,
                    tecnologias_usadas TEXT,
                    otras_tecnologias TEXT,
                    capacidad_aprendizaje TEXT,
                    comentarios TEXT,
                    conectividad TEXT,
                    expectativas TEXT,
                    compromisos TEXT,
                    limitaciones TEXT,
                    latitud TEXT,
                    longitud TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS encuestas_educativas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email TEXT,
                    nombre_aplicador TEXT,
                    fecha_aplicacion DATE,
                    municipio TEXT,
                    vereda TEXT,
                    nombre_institucion TEXT,
                    codigo_dane TEXT,
                    nombre_directivo TEXT,
                    contacto TEXT,
                    tipo_institucion TEXT,
                    sedes TEXT,
                    numero_estudiantes INT,
                    numero_docentes INT,
                    grados_atiende TEXT,
                    tiene_prae TINYINT(1),
                    prae_descripcion TEXT,
                    experiencia_proyectos TINYINT(1),
                    descripcion_proyectos TEXT,
                    tiene_huerta TINYINT(1),
                    area_huerta INT,
                    uso_huerta TEXT,
                    temas_agroambientales TEXT,
                    espacio_agrohub TINYINT(1),
                    area_agrohub INT,
                    condiciones_terreno TEXT,
                    internet TEXT,
                    espacios_complementarios TINYINT(1),
                    cantidad_espacios INT,
                    laboratorio TINYINT(1),
                    laboratorio_funciona TINYINT(1),
                    actores_comunitarios TEXT,
                    tiene_alianzas TINYINT(1),
                    descripcion_alianzas TEXT,
                    tiene_semilleros TINYINT(1),
                    nombre_grupo TEXT,
                    interes_agricultura TEXT,
                    medios_comunicacion TEXT,
                    comentarios TEXT,
                    anexa_documentos TINYINT(1),
                    expectativas TEXT,
                    compromisos TEXT,
                    limitaciones TEXT,
                    latitud TEXT,
                    longitud TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS encuestas_derecho_humano_alimentario (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email TEXT,
                    fecha_aplicacion DATE,
                    nombre_jefe_hogar TEXT,
                    edad INT,
                    genero TEXT,
                    departamento TEXT,
                    municipio TEXT,
                    subregion TEXT,
                    numero_miembros_hogar INT,
                    nivel_educativo TEXT,
                    nombre_encuestador TEXT,
                    cargo_encuestador TEXT,
                    dedicado_agricultura TINYINT(1),
                    cultivos_principales TEXT,
                    razon_produccion TEXT,
                    cobertura_necesidades TINYINT(1),
                    meses_escasez TEXT,
                    cambios_produccion TEXT,
                    razon_cambios TEXT,
                    acceso_insumos_agricolas TINYINT(1),
                    asistencia_tecnica TINYINT(1),
                    compra_suficiente_alimentos TINYINT(1),
                    acceso_mercado TINYINT(1),
                    distancia_mercado TEXT,
                    alimento_asequible TINYINT(1),
                    reduccion_consumo TINYINT(1),
                    ayuda_alimentaria TINYINT(1),
                    dieta_balanceada TINYINT(1),
                    consumo_grupos_alimenticios TEXT,
                    agua_potable_preparacion TINYINT(1),
                    enfermedades_transmitidas TINYINT(1),
                    alimentos_culturalmente_aceptables TINYINT(1),
                    higiene_manipulacion TINYINT(1),
                    conoce_derecho_alimentacion TINYINT(1),
                    cree_derecho_respetado TINYINT(1),
                    medidas_mejorar_acceso TEXT,
                    latitud TEXT,
                    longitud TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )

    # ---------- Helpers ----------
    def _insert_and_id(self, sql: str, params: tuple) -> int:
        with get_db_cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid

    # ---------- Create / Bulk ----------
    def save_bulk(self, surveys: List[SurveyType]) -> List[SurveyType]:
        with get_db_cursor() as cur:
            for survey in surveys:
                if isinstance(survey, EncuestaAgrohub):
                    cur.execute(
                        """
                        INSERT INTO encuestas_agrohub (
                            email, nombre_aplicador, fecha_aplicacion, municipio, vereda, nombre_organizacion, tipo_organizacion,
                            anio_conformacion, numero_miembros, numero_nucleos_familiares, cobertura_territorial, representante_legal, contacto,
                            tipos_agricultura, cultivan_hortalizas, cuales_hortalizas, area_hortalizas, destino_hortalizas, actividades_complementarias, tiene_patio, area_patio, condiciones_terreno,
                            formalizacion, asociatividad, experiencia_proyectos, descripcion_experiencia, tiene_estatutos_plan, acceso_mercado, frecuencia_venta, manejo_administrativo,
                            tecnologias_usadas, otras_tecnologias, capacidad_aprendizaje, comentarios, conectividad,
                            expectativas, compromisos, limitaciones, latitud, longitud
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            survey.email,
                            survey.nombre_aplicador,
                            survey.fecha_aplicacion,
                            survey.municipio,
                            survey.vereda,
                            survey.nombre_organizacion,
                            survey.tipo_organizacion,
                            survey.anio_conformacion,
                            survey.numero_miembros,
                            survey.numero_nucleos_familiares,
                            survey.cobertura_territorial,
                            survey.representante_legal,
                            survey.contacto,
                            survey.tipos_agricultura,
                            survey.cultivan_hortalizas,
                            survey.cuales_hortalizas,
                            survey.area_hortalizas,
                            survey.destino_hortalizas,
                            survey.actividades_complementarias,
                            survey.tiene_patio,
                            survey.area_patio,
                            survey.condiciones_terreno,
                            survey.formalizacion,
                            survey.asociatividad,
                            survey.experiencia_proyectos,
                            survey.descripcion_experiencia,
                            survey.tiene_estatutos_plan,
                            survey.acceso_mercado,
                            survey.frecuencia_venta,
                            survey.manejo_administrativo,
                            survey.tecnologias_usadas,
                            survey.otras_tecnologias,
                            survey.capacidad_aprendizaje,
                            survey.comentarios,
                            survey.conectividad,
                            survey.expectativas,
                            survey.compromisos,
                            survey.limitaciones,
                            survey.latitud,
                            survey.longitud,
                        ),
                    )
                    survey.id = cur.lastrowid
                elif isinstance(survey, EncuestaEducativa):
                    cur.execute(
                        """
                        INSERT INTO encuestas_educativas (
                            email, nombre_aplicador, fecha_aplicacion, municipio, vereda, nombre_institucion, codigo_dane, nombre_directivo, contacto,
                            tipo_institucion, sedes, numero_estudiantes, numero_docentes, grados_atiende, tiene_prae, prae_descripcion,
                            experiencia_proyectos, descripcion_proyectos, tiene_huerta, area_huerta, uso_huerta, temas_agroambientales,
                            espacio_agrohub, area_agrohub, condiciones_terreno, internet, espacios_complementarios, cantidad_espacios, laboratorio, laboratorio_funciona,
                            actores_comunitarios, tiene_alianzas, descripcion_alianzas,
                            tiene_semilleros, nombre_grupo, interes_agricultura, medios_comunicacion,
                            comentarios, anexa_documentos,
                            expectativas, compromisos, limitaciones,
                            latitud, longitud
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            survey.email,
                            survey.nombre_aplicador,
                            survey.fecha_aplicacion,
                            survey.municipio,
                            survey.vereda,
                            survey.nombre_institucion,
                            survey.codigo_dane,
                            survey.nombre_directivo,
                            survey.contacto,
                            survey.tipo_institucion,
                            survey.sedes,
                            survey.numero_estudiantes,
                            survey.numero_docentes,
                            survey.grados_atiende,
                            survey.tiene_prae,
                            survey.prae_descripcion,
                            survey.experiencia_proyectos,
                            survey.descripcion_proyectos,
                            survey.tiene_huerta,
                            survey.area_huerta,
                            survey.uso_huerta,
                            survey.temas_agroambientales,
                            survey.espacio_agrohub,
                            survey.area_agrohub,
                            survey.condiciones_terreno,
                            survey.internet,
                            survey.espacios_complementarios,
                            survey.cantidad_espacios,
                            survey.laboratorio,
                            survey.laboratorio_funciona,
                            survey.actores_comunitarios,
                            survey.tiene_alianzas,
                            survey.descripcion_alianzas,
                            survey.tiene_semilleros,
                            survey.nombre_grupo,
                            survey.interes_agricultura,
                            survey.medios_comunicacion,
                            survey.comentarios,
                            survey.anexa_documentos,
                            survey.expectativas,
                            survey.compromisos,
                            survey.limitaciones,
                            survey.latitud,
                            survey.longitud,
                        ),
                    )
                    survey.id = cur.lastrowid
                elif isinstance(survey, EncuestaDerechoHumanoAlimentario):
                    cur.execute(
                        """
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
                        """,
                        (
                            survey.email,
                            survey.fecha_aplicacion,
                            survey.nombre_jefe_hogar,
                            survey.edad,
                            survey.genero,
                            survey.departamento,
                            survey.municipio,
                            survey.subregion,
                            survey.numero_miembros_hogar,
                            survey.nivel_educativo,
                            survey.nombre_encuestador,
                            survey.cargo_encuestador,
                            survey.dedicado_agricultura,
                            survey.cultivos_principales,
                            survey.razon_produccion,
                            survey.cobertura_necesidades,
                            survey.meses_escasez,
                            survey.cambios_produccion,
                            survey.razon_cambios,
                            survey.acceso_insumos_agricolas,
                            survey.asistencia_tecnica,
                            survey.compra_suficiente_alimentos,
                            survey.acceso_mercado,
                            survey.distancia_mercado,
                            survey.alimento_asequible,
                            survey.reduccion_consumo,
                            survey.ayuda_alimentaria,
                            survey.dieta_balanceada,
                            survey.consumo_grupos_alimenticios,
                            survey.agua_potable_preparacion,
                            survey.enfermedades_transmitidas,
                            survey.alimentos_culturalmente_aceptables,
                            survey.higiene_manipulacion,
                            survey.conoce_derecho_alimentacion,
                            survey.cree_derecho_respetado,
                            survey.medidas_mejorar_acceso,
                            survey.latitud,
                            survey.longitud,
                        ),
                    )
                    survey.id = cur.lastrowid
        return surveys

    # ---------- Read ----------
    def _fetch_table(
        self,
        table: str,
        type_name: str,
        page: int,
        page_size: int,
        email: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        id: Optional[int],
    ) -> List[dict]:
        where, params = [], []
        if email:
            where.append("email = %s")
            params.append(email)
        if start_date:
            where.append("fecha_creacion >= %s")
            params.append(start_date)
        if end_date:
            where.append("fecha_creacion <= %s")
            params.append(end_date)
        if id:
            where.append("id = %s")
            params.append(id)

        sql = f"SELECT * FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY fecha_creacion DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])

        with get_db_cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            for row in rows:
                row["type"] = type_name
            return rows

    def get_all(
        self,
        page: int,
        page_size: int,
        email: Optional[str] = None,
        survey_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        id: Optional[int] = None,
    ) -> List[dict]:
        if survey_type == "agrohub":
            return self._fetch_table("encuestas_agrohub", "agrohub", page, page_size, email, start_date, end_date, id)
        if survey_type == "educativa":
            return self._fetch_table("encuestas_educativas", "educativa", page, page_size, email, start_date, end_date, id)
        if survey_type == "derecho_humano_alimentario":
            return self._fetch_table(
                "encuestas_derecho_humano_alimentario",
                "derecho_humano_alimentario",
                page,
                page_size,
                email,
                start_date,
                end_date,
                id,
            )

        # Sin filtro de tipo: traer de todas y combinar
        results = []
        results += self._fetch_table("encuestas_agrohub", "agrohub", page, page_size, email, start_date, end_date, id)
        results += self._fetch_table("encuestas_educativas", "educativa", page, page_size, email, start_date, end_date, id)
        results += self._fetch_table(
            "encuestas_derecho_humano_alimentario",
            "derecho_humano_alimentario",
            page,
            page_size,
            email,
            start_date,
            end_date,
            id,
        )
        results.sort(key=lambda r: r.get("fecha_creacion"), reverse=True)
        return results

    # ---------- Update ----------
    def update(self, id: int, survey: SurveyType) -> Optional[SurveyType]:
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

        survey_data = survey.model_dump(exclude_unset=True, exclude={"id", "type", "fecha_creacion"})
        if not survey_data:
            return None

        set_clause = ", ".join([f"{key} = %s" for key in survey_data.keys()])
        params = list(survey_data.values()) + [id]

        with get_db_cursor() as cur:
            cur.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = %s", tuple(params))
            if cur.rowcount == 0:
                return None
            cur.execute(f"SELECT * FROM {table_name} WHERE id = %s", (id,))
            row = cur.fetchone()
            if not row:
                return None
            return model_class(**row)

    # ---------- Locations ----------
    def get_all_locations(self) -> List[SurveyLocationInfo]:
        results: List[SurveyLocationInfo] = []
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT 'agrohub' AS type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_agrohub
                    WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != ''"""
            )
            for row in cur.fetchall():
                results.append(
                    SurveyLocationInfo(
                        type=row["type"],
                        latitud=row["latitud"],
                        longitud=row["longitud"],
                        municipio=row.get("municipio"),
                        fecha_aplicacion=row.get("fecha_aplicacion"),
                    )
                )

            cur.execute(
                """SELECT 'instituciones educativas' AS type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_educativas
                    WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != ''"""
            )
            for row in cur.fetchall():
                results.append(
                    SurveyLocationInfo(
                        type=row["type"],
                        latitud=row["latitud"],
                        longitud=row["longitud"],
                        municipio=row.get("municipio"),
                        fecha_aplicacion=row.get("fecha_aplicacion"),
                    )
                )

            cur.execute(
                """SELECT 'caracterizacion agro-alimentaria' AS type, latitud, longitud, municipio, fecha_aplicacion FROM encuestas_derecho_humano_alimentario
                    WHERE latitud IS NOT NULL AND latitud != '' AND longitud IS NOT NULL AND longitud != ''"""
            )
            for row in cur.fetchall():
                results.append(
                    SurveyLocationInfo(
                        type=row["type"],
                        latitud=row["latitud"],
                        longitud=row["longitud"],
                        municipio=row.get("municipio"),
                        fecha_aplicacion=row.get("fecha_aplicacion"),
                    )
                )
        return results
