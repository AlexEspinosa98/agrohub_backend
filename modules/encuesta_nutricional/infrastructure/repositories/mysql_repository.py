import json
from datetime import date, datetime
from typing import List, Optional

from database.mysql_connection import get_db_cursor
from modules.encuesta_nutricional.domain.entities import (
    EncuestaNutricionalCreate,
    EncuestaNutricionalUpdate,
)

_UPDATABLE_FIELDS = [
    "nombre_encuestador",
    "cedula_encuestador",
    "fecha_aplicacion",
    "codigo_cuestionario",
    "municipio",
    "vereda_comunidad",
    "nombre_participante",
    "edad_anios",
    "sexo",
    "area_residencia",
    "nivel_educativo",
    "num_personas_hogar",
    "num_mujeres_hogar",
    "hay_menores_18",
    "num_ninos_menores_5",
    "fuente_ingreso_principal",
    "tiene_huerta_o_animales",
    "jefatura_hogar",
    "estabilidad_ingreso",
    "percepcion_estado_nutricional",
    "cambio_peso_no_intencional",
    "nino_en_control_crecimiento",
    "peso_kg",
    "talla_cm",
    "circunferencia_cintura_cm",
    "perimetro_brazo_cm",
    "grupo_perimetro_brazo",
    "imc_calculado",
    "dias_cereales_tuberculos",
    "dias_leguminosas",
    "dias_carnes_pescado_huevo",
    "dias_lacteos",
    "dias_frutas",
    "dias_verduras",
    "dias_grasas",
    "dias_azucares_ultraprocesados",
    "puntaje_diversidad_dietetica",
    "frecuencia_frutas_semana",
    "frecuencia_verduras_semana",
    "frecuencia_bebidas_azucaradas",
    "comidas_por_dia",
    "frecuencia_comida_fuera_hogar",
    "proporcion_autoconsumo",
    "alimentos_preferidos",
    "preocupacion_alimentos_acabaran",
    "alimentos_se_acabaron",
    "adulto_omitio_comida_principal",
    "sintio_hambre_sin_comer",
    "puntaje_inseguridad_alimentaria",
    "clasificacion_seguridad_alimentaria",
    "consentimiento_informado",
    "cedula_participante",
    "observaciones_encuestador",
]


def _serialize(row: dict) -> dict:
    if not row:
        return row
    row = dict(row)
    if row.get("alimentos_preferidos") and isinstance(row["alimentos_preferidos"], str):
        try:
            row["alimentos_preferidos"] = json.loads(row["alimentos_preferidos"])
        except (json.JSONDecodeError, TypeError):
            row["alimentos_preferidos"] = None
    return row


class EncuestaNutricionalRepository:
    def __init__(self):
        self._create_table()

    def _create_table(self):
        with get_db_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS encuestas_nutricionales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_encuesta VARCHAR(50) UNIQUE,

                    -- Encabezado
                    nombre_encuestador VARCHAR(255) NOT NULL,
                    cedula_encuestador VARCHAR(50) NOT NULL,
                    fecha_aplicacion DATE NOT NULL,
                    codigo_cuestionario VARCHAR(100),
                    municipio VARCHAR(100) NOT NULL,
                    vereda_comunidad VARCHAR(255) NOT NULL,

                    -- Sección A
                    nombre_participante VARCHAR(255),
                    edad_anios INT,
                    sexo VARCHAR(20),
                    area_residencia VARCHAR(20),
                    nivel_educativo VARCHAR(50),
                    num_personas_hogar INT,
                    num_mujeres_hogar INT,
                    hay_menores_18 BOOLEAN,
                    num_ninos_menores_5 INT,
                    fuente_ingreso_principal VARCHAR(100),
                    tiene_huerta_o_animales BOOLEAN,
                    jefatura_hogar VARCHAR(50),
                    estabilidad_ingreso VARCHAR(100),

                    -- Sección B
                    percepcion_estado_nutricional VARCHAR(20),
                    cambio_peso_no_intencional BOOLEAN,
                    nino_en_control_crecimiento VARCHAR(10),
                    peso_kg DECIMAL(6,2),
                    talla_cm DECIMAL(6,2),
                    circunferencia_cintura_cm DECIMAL(6,2),
                    perimetro_brazo_cm DECIMAL(6,2),
                    grupo_perimetro_brazo VARCHAR(30),
                    imc_calculado DECIMAL(6,2),

                    -- Sección C
                    dias_cereales_tuberculos INT,
                    dias_leguminosas INT,
                    dias_carnes_pescado_huevo INT,
                    dias_lacteos INT,
                    dias_frutas INT,
                    dias_verduras INT,
                    dias_grasas INT,
                    dias_azucares_ultraprocesados INT,
                    puntaje_diversidad_dietetica INT,
                    frecuencia_frutas_semana VARCHAR(30),
                    frecuencia_verduras_semana VARCHAR(30),
                    frecuencia_bebidas_azucaradas VARCHAR(30),
                    comidas_por_dia VARCHAR(20),
                    frecuencia_comida_fuera_hogar VARCHAR(30),
                    proporcion_autoconsumo VARCHAR(30),
                    alimentos_preferidos TEXT,

                    -- Sección D
                    preocupacion_alimentos_acabaran BOOLEAN,
                    alimentos_se_acabaron BOOLEAN,
                    adulto_omitio_comida_principal BOOLEAN,
                    sintio_hambre_sin_comer BOOLEAN,
                    puntaje_inseguridad_alimentaria INT,
                    clasificacion_seguridad_alimentaria VARCHAR(60),

                    -- Cierre
                    consentimiento_informado BOOLEAN NOT NULL,
                    cedula_participante VARCHAR(50) NOT NULL,
                    observaciones_encuestador TEXT,

                    -- Metadata
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

    def create(self, data: EncuestaNutricionalCreate) -> dict:
        alimentos_json = (
            json.dumps(data.alimentos_preferidos, ensure_ascii=False)
            if data.alimentos_preferidos is not None
            else None
        )
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO encuestas_nutricionales (
                    nombre_encuestador, cedula_encuestador, fecha_aplicacion,
                    codigo_cuestionario, municipio, vereda_comunidad,
                    nombre_participante, edad_anios, sexo, area_residencia,
                    nivel_educativo, num_personas_hogar, num_mujeres_hogar,
                    hay_menores_18, num_ninos_menores_5, fuente_ingreso_principal,
                    tiene_huerta_o_animales, jefatura_hogar, estabilidad_ingreso,
                    percepcion_estado_nutricional, cambio_peso_no_intencional,
                    nino_en_control_crecimiento, peso_kg, talla_cm,
                    circunferencia_cintura_cm, perimetro_brazo_cm, grupo_perimetro_brazo,
                    imc_calculado, dias_cereales_tuberculos, dias_leguminosas,
                    dias_carnes_pescado_huevo, dias_lacteos, dias_frutas, dias_verduras,
                    dias_grasas, dias_azucares_ultraprocesados, puntaje_diversidad_dietetica,
                    frecuencia_frutas_semana, frecuencia_verduras_semana,
                    frecuencia_bebidas_azucaradas, comidas_por_dia,
                    frecuencia_comida_fuera_hogar, proporcion_autoconsumo,
                    alimentos_preferidos, preocupacion_alimentos_acabaran,
                    alimentos_se_acabaron, adulto_omitio_comida_principal,
                    sintio_hambre_sin_comer, puntaje_inseguridad_alimentaria,
                    clasificacion_seguridad_alimentaria, consentimiento_informado,
                    cedula_participante, observaciones_encuestador
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    data.nombre_encuestador,
                    data.cedula_encuestador,
                    data.fecha_aplicacion,
                    data.codigo_cuestionario,
                    data.municipio,
                    data.vereda_comunidad,
                    data.nombre_participante,
                    data.edad_anios,
                    data.sexo,
                    data.area_residencia,
                    data.nivel_educativo,
                    data.num_personas_hogar,
                    data.num_mujeres_hogar,
                    data.hay_menores_18,
                    data.num_ninos_menores_5,
                    data.fuente_ingreso_principal,
                    data.tiene_huerta_o_animales,
                    data.jefatura_hogar,
                    data.estabilidad_ingreso,
                    data.percepcion_estado_nutricional,
                    data.cambio_peso_no_intencional,
                    data.nino_en_control_crecimiento,
                    data.peso_kg,
                    data.talla_cm,
                    data.circunferencia_cintura_cm,
                    data.perimetro_brazo_cm,
                    data.grupo_perimetro_brazo,
                    data.imc_calculado,
                    data.dias_cereales_tuberculos,
                    data.dias_leguminosas,
                    data.dias_carnes_pescado_huevo,
                    data.dias_lacteos,
                    data.dias_frutas,
                    data.dias_verduras,
                    data.dias_grasas,
                    data.dias_azucares_ultraprocesados,
                    data.puntaje_diversidad_dietetica,
                    data.frecuencia_frutas_semana,
                    data.frecuencia_verduras_semana,
                    data.frecuencia_bebidas_azucaradas,
                    data.comidas_por_dia,
                    data.frecuencia_comida_fuera_hogar,
                    data.proporcion_autoconsumo,
                    alimentos_json,
                    data.preocupacion_alimentos_acabaran,
                    data.alimentos_se_acabaron,
                    data.adulto_omitio_comida_principal,
                    data.sintio_hambre_sin_comer,
                    data.puntaje_inseguridad_alimentaria,
                    data.clasificacion_seguridad_alimentaria,
                    data.consentimiento_informado,
                    data.cedula_participante,
                    data.observaciones_encuestador,
                ),
            )
            new_id = cur.lastrowid
            now = datetime.now()
            numero = f"SAN-{now.strftime('%Y%m%d')}-{new_id:06d}"
            cur.execute(
                "UPDATE encuestas_nutricionales SET numero_encuesta = %s WHERE id = %s",
                (numero, new_id),
            )
        return {"id": new_id, "numero_encuesta": numero}

    def get_by_numero(self, numero_encuesta: str) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM encuestas_nutricionales WHERE numero_encuesta = %s AND is_active = 1",
                (numero_encuesta,),
            )
            return _serialize(cur.fetchone())

    def get_detail(self, numero_encuesta: str) -> Optional[dict]:
        return self.get_by_numero(numero_encuesta)

    def list_surveys(
        self,
        nombre_encuestador: Optional[str] = None,
        municipio: Optional[str] = None,
        vereda_comunidad: Optional[str] = None,
        numero_encuesta: Optional[str] = None,
        cedula_encuestador: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[dict]:
        query = (
            "SELECT numero_encuesta, nombre_encuestador, cedula_encuestador, "
            "fecha_aplicacion, municipio, vereda_comunidad, cedula_participante, "
            "nombre_participante "
            "FROM encuestas_nutricionales WHERE is_active = 1"
        )
        params: List = []

        if nombre_encuestador:
            query += " AND nombre_encuestador LIKE %s"
            params.append(f"%{nombre_encuestador}%")
        if municipio:
            query += " AND municipio = %s"
            params.append(municipio)
        if vereda_comunidad:
            query += " AND vereda_comunidad LIKE %s"
            params.append(f"%{vereda_comunidad}%")
        if numero_encuesta:
            query += " AND numero_encuesta = %s"
            params.append(numero_encuesta)
        if cedula_encuestador:
            query += " AND cedula_encuestador = %s"
            params.append(cedula_encuestador)

        offset = (page - 1) * page_size
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        with get_db_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def update(self, numero_encuesta: str, data: EncuestaNutricionalUpdate) -> bool:
        fields = []
        values = []
        update_data = data.model_dump(exclude_none=True)

        for field in _UPDATABLE_FIELDS:
            if field not in update_data:
                continue
            value = update_data[field]
            if field == "alimentos_preferidos":
                value = json.dumps(value, ensure_ascii=False) if value is not None else None
            fields.append(f"{field} = %s")
            values.append(value)

        if not fields:
            return False

        values.append(numero_encuesta)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE encuestas_nutricionales SET {', '.join(fields)} WHERE numero_encuesta = %s AND is_active = 1",
                values,
            )
            return cur.rowcount > 0

    def soft_delete(self, numero_encuesta: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE encuestas_nutricionales SET is_active = 0, deleted_at = NOW() WHERE numero_encuesta = %s AND is_active = 1",
                (numero_encuesta,),
            )
            return cur.rowcount > 0
