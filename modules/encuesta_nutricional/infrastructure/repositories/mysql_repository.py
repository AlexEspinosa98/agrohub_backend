import json
from datetime import datetime
from typing import List, Optional

from database.mysql_connection import get_db_cursor
from modules.encuesta_nutricional.domain.entities import (
    EncuestaNutricionalCreate,
    EncuestaNutricionalUpdate,
    MiembroCreate,
    MiembroUpdate,
    PersonaNutricionalCreate,
    PersonaNutricionalUpdate,
)

_ENCUESTA_UPDATABLE = [
    "nombre_encuestador", "cedula_encuestador", "fecha_aplicacion",
    "codigo_cuestionario", "municipio", "vereda_comunidad",
    "num_personas_hogar", "num_mujeres_hogar", "hay_menores_18",
    "num_ninos_menores_5", "fuente_ingreso_principal", "tiene_huerta_o_animales",
    "jefatura_hogar", "estabilidad_ingreso",
    "dias_cereales_tuberculos", "dias_leguminosas", "dias_carnes_pescado_huevo",
    "dias_lacteos", "dias_frutas", "dias_verduras", "dias_grasas",
    "dias_azucares_ultraprocesados", "puntaje_diversidad_dietetica",
    "frecuencia_frutas_semana", "frecuencia_verduras_semana",
    "frecuencia_bebidas_azucaradas", "comidas_por_dia",
    "frecuencia_comida_fuera_hogar", "proporcion_autoconsumo",
    "alimentos_preferidos", "preocupacion_alimentos_acabaran",
    "alimentos_se_acabaron", "adulto_omitio_comida_principal",
    "sintio_hambre_sin_comer", "puntaje_inseguridad_alimentaria",
    "clasificacion_seguridad_alimentaria", "consentimiento_informado",
    "observaciones_encuestador",
]

_MIEMBRO_UPDATABLE = [
    "percepcion_estado_nutricional", "cambio_peso_no_intencional",
    "nino_en_control_crecimiento", "peso_kg", "talla_cm",
    "circunferencia_cintura_cm", "perimetro_brazo_cm",
    "grupo_perimetro_brazo", "imc_calculado",
]

_PERSONA_UPDATABLE = [
    "nombre", "edad_anios", "sexo", "area_residencia", "nivel_educativo",
]


def _deserialize_encuesta(row: dict) -> dict:
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
        self._create_tables()

    def _create_tables(self):
        with get_db_cursor() as cur:
            # Tabla maestra de participantes
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

            # Tabla de encuestas (datos del hogar)
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

                    -- Sección A — Hogar
                    num_personas_hogar INT,
                    num_mujeres_hogar INT,
                    hay_menores_18 BOOLEAN,
                    num_ninos_menores_5 INT,
                    fuente_ingreso_principal VARCHAR(100),
                    tiene_huerta_o_animales BOOLEAN,
                    jefatura_hogar VARCHAR(50),
                    estabilidad_ingreso VARCHAR(100),

                    -- Sección C — Hábitos del hogar
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

                    -- Sección D — ELCSA
                    preocupacion_alimentos_acabaran BOOLEAN,
                    alimentos_se_acabaron BOOLEAN,
                    adulto_omitio_comida_principal BOOLEAN,
                    sintio_hambre_sin_comer BOOLEAN,
                    puntaje_inseguridad_alimentaria INT,
                    clasificacion_seguridad_alimentaria VARCHAR(60),

                    -- Cierre
                    consentimiento_informado BOOLEAN NOT NULL,
                    observaciones_encuestador TEXT,

                    -- Metadata
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # Tabla de miembros (vincula persona ↔ encuesta + mediciones Sección B)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS encuesta_nutricional_miembros (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    encuesta_id INT NOT NULL,
                    persona_id INT NOT NULL,

                    -- Sección B — Estado nutricional (mediciones de esta encuesta)
                    percepcion_estado_nutricional VARCHAR(20),
                    cambio_peso_no_intencional BOOLEAN,
                    nino_en_control_crecimiento VARCHAR(10),
                    peso_kg DECIMAL(6,2),
                    talla_cm DECIMAL(6,2),
                    circunferencia_cintura_cm DECIMAL(6,2),
                    perimetro_brazo_cm DECIMAL(6,2),
                    grupo_perimetro_brazo VARCHAR(30),
                    imc_calculado DECIMAL(6,2),

                    -- Metadata
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

    # ------------------------------------------------------------------
    # Personas nutricionales
    # ------------------------------------------------------------------

    def _upsert_persona(self, cur, cedula: str, nombre: Optional[str],
                        edad_anios: Optional[int], sexo: Optional[str],
                        area_residencia: Optional[str], nivel_educativo: Optional[str]) -> int:
        """Inserta o actualiza una persona por cédula. Devuelve su id."""
        cur.execute(
            """
            INSERT INTO personas_nutricionales
                (cedula, nombre, edad_anios, sexo, area_residencia, nivel_educativo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = LAST_INSERT_ID(id),
                nombre = COALESCE(VALUES(nombre), nombre),
                edad_anios = COALESCE(VALUES(edad_anios), edad_anios),
                sexo = COALESCE(VALUES(sexo), sexo),
                area_residencia = COALESCE(VALUES(area_residencia), area_residencia),
                nivel_educativo = COALESCE(VALUES(nivel_educativo), nivel_educativo)
            """,
            (cedula, nombre, edad_anios, sexo, area_residencia, nivel_educativo),
        )
        return cur.lastrowid

    def get_persona_by_cedula(self, cedula: str) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM personas_nutricionales WHERE cedula = %s AND is_active = 1",
                (cedula,),
            )
            return cur.fetchone()

    def get_persona_by_id(self, persona_id: int) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM personas_nutricionales WHERE id = %s AND is_active = 1",
                (persona_id,),
            )
            return cur.fetchone()

    def update_persona(self, persona_id: int, data: PersonaNutricionalUpdate) -> bool:
        fields = []
        values = []
        update_data = data.model_dump(exclude_none=True)
        for field in _PERSONA_UPDATABLE:
            if field in update_data:
                fields.append(f"{field} = %s")
                values.append(update_data[field])
        if not fields:
            return False
        values.append(persona_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE personas_nutricionales SET {', '.join(fields)} WHERE id = %s AND is_active = 1",
                values,
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Encuesta (hogar)
    # ------------------------------------------------------------------

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
                    num_personas_hogar, num_mujeres_hogar, hay_menores_18,
                    num_ninos_menores_5, fuente_ingreso_principal, tiene_huerta_o_animales,
                    jefatura_hogar, estabilidad_ingreso,
                    dias_cereales_tuberculos, dias_leguminosas, dias_carnes_pescado_huevo,
                    dias_lacteos, dias_frutas, dias_verduras, dias_grasas,
                    dias_azucares_ultraprocesados, puntaje_diversidad_dietetica,
                    frecuencia_frutas_semana, frecuencia_verduras_semana,
                    frecuencia_bebidas_azucaradas, comidas_por_dia,
                    frecuencia_comida_fuera_hogar, proporcion_autoconsumo,
                    alimentos_preferidos, preocupacion_alimentos_acabaran,
                    alimentos_se_acabaron, adulto_omitio_comida_principal,
                    sintio_hambre_sin_comer, puntaje_inseguridad_alimentaria,
                    clasificacion_seguridad_alimentaria, consentimiento_informado,
                    observaciones_encuestador
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    data.nombre_encuestador, data.cedula_encuestador, data.fecha_aplicacion,
                    data.codigo_cuestionario, data.municipio, data.vereda_comunidad,
                    data.num_personas_hogar, data.num_mujeres_hogar, data.hay_menores_18,
                    data.num_ninos_menores_5, data.fuente_ingreso_principal, data.tiene_huerta_o_animales,
                    data.jefatura_hogar, data.estabilidad_ingreso,
                    data.dias_cereales_tuberculos, data.dias_leguminosas, data.dias_carnes_pescado_huevo,
                    data.dias_lacteos, data.dias_frutas, data.dias_verduras, data.dias_grasas,
                    data.dias_azucares_ultraprocesados, data.puntaje_diversidad_dietetica,
                    data.frecuencia_frutas_semana, data.frecuencia_verduras_semana,
                    data.frecuencia_bebidas_azucaradas, data.comidas_por_dia,
                    data.frecuencia_comida_fuera_hogar, data.proporcion_autoconsumo,
                    alimentos_json, data.preocupacion_alimentos_acabaran,
                    data.alimentos_se_acabaron, data.adulto_omitio_comida_principal,
                    data.sintio_hambre_sin_comer, data.puntaje_inseguridad_alimentaria,
                    data.clasificacion_seguridad_alimentaria, data.consentimiento_informado,
                    data.observaciones_encuestador,
                ),
            )
            encuesta_id = cur.lastrowid
            now = datetime.now()
            numero = f"SAN-{now.strftime('%Y%m%d')}-{encuesta_id:06d}"
            cur.execute(
                "UPDATE encuestas_nutricionales SET numero_encuesta = %s WHERE id = %s",
                (numero, encuesta_id),
            )
            for miembro in data.miembros:
                self._insert_miembro(cur, encuesta_id, miembro)

        return {"id": encuesta_id, "numero_encuesta": numero, "miembros_creados": len(data.miembros)}

    def get_by_numero(self, numero_encuesta: str) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM encuestas_nutricionales WHERE numero_encuesta = %s AND is_active = 1",
                (numero_encuesta,),
            )
            row = cur.fetchone()
        return _deserialize_encuesta(row) if row else None

    def get_detail(self, numero_encuesta: str) -> Optional[dict]:
        encuesta = self.get_by_numero(numero_encuesta)
        if not encuesta:
            return None
        encuesta["miembros"] = self.list_miembros(encuesta["id"])
        return encuesta

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
            "SELECT e.numero_encuesta, e.nombre_encuestador, e.cedula_encuestador, "
            "e.fecha_aplicacion, e.municipio, e.vereda_comunidad, "
            "COUNT(m.id) AS total_miembros "
            "FROM encuestas_nutricionales e "
            "LEFT JOIN encuesta_nutricional_miembros m "
            "  ON m.encuesta_id = e.id AND m.is_active = 1 "
            "WHERE e.is_active = 1"
        )
        params: List = []
        if nombre_encuestador:
            query += " AND e.nombre_encuestador LIKE %s"
            params.append(f"%{nombre_encuestador}%")
        if municipio:
            query += " AND e.municipio = %s"
            params.append(municipio)
        if vereda_comunidad:
            query += " AND e.vereda_comunidad LIKE %s"
            params.append(f"%{vereda_comunidad}%")
        if numero_encuesta:
            query += " AND e.numero_encuesta = %s"
            params.append(numero_encuesta)
        if cedula_encuestador:
            query += " AND e.cedula_encuestador = %s"
            params.append(cedula_encuestador)
        offset = (page - 1) * page_size
        query += " GROUP BY e.id ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        with get_db_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def update(self, numero_encuesta: str, data: EncuestaNutricionalUpdate) -> bool:
        fields = []
        values = []
        update_data = data.model_dump(exclude_none=True)
        for field in _ENCUESTA_UPDATABLE:
            if field not in update_data:
                continue
            value = update_data[field]
            if field == "alimentos_preferidos":
                value = json.dumps(value, ensure_ascii=False)
            fields.append(f"{field} = %s")
            values.append(value)
        if not fields:
            return False
        values.append(numero_encuesta)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE encuestas_nutricionales SET {', '.join(fields)} "
                f"WHERE numero_encuesta = %s AND is_active = 1",
                values,
            )
            return cur.rowcount > 0

    def soft_delete(self, numero_encuesta: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE encuestas_nutricionales SET is_active = 0, deleted_at = NOW() "
                "WHERE numero_encuesta = %s AND is_active = 1",
                (numero_encuesta,),
            )
            if cur.rowcount == 0:
                return False
            # Los miembros se desactivan en cascada (ON DELETE CASCADE borra físico,
            # aquí hacemos soft delete manual)
            cur.execute(
                "UPDATE encuesta_nutricional_miembros m "
                "JOIN encuestas_nutricionales e ON e.id = m.encuesta_id "
                "SET m.is_active = 0, m.deleted_at = NOW() "
                "WHERE e.numero_encuesta = %s",
                (numero_encuesta,),
            )
            return True

    # ------------------------------------------------------------------
    # Miembros
    # ------------------------------------------------------------------

    def _insert_miembro(self, cur, encuesta_id: int, miembro: MiembroCreate) -> int:
        persona_id = self._upsert_persona(
            cur,
            cedula=miembro.cedula_participante,
            nombre=miembro.nombre_participante,
            edad_anios=miembro.edad_anios,
            sexo=miembro.sexo,
            area_residencia=miembro.area_residencia,
            nivel_educativo=miembro.nivel_educativo,
        )
        cur.execute(
            """
            INSERT INTO encuesta_nutricional_miembros (
                encuesta_id, persona_id,
                percepcion_estado_nutricional, cambio_peso_no_intencional,
                nino_en_control_crecimiento, peso_kg, talla_cm,
                circunferencia_cintura_cm, perimetro_brazo_cm,
                grupo_perimetro_brazo, imc_calculado
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                encuesta_id, persona_id,
                miembro.percepcion_estado_nutricional, miembro.cambio_peso_no_intencional,
                miembro.nino_en_control_crecimiento, miembro.peso_kg, miembro.talla_cm,
                miembro.circunferencia_cintura_cm, miembro.perimetro_brazo_cm,
                miembro.grupo_perimetro_brazo, miembro.imc_calculado,
            ),
        )
        return cur.lastrowid

    def add_miembro(self, numero_encuesta: str, miembro: MiembroCreate) -> Optional[dict]:
        encuesta = self.get_by_numero(numero_encuesta)
        if not encuesta:
            return None
        with get_db_cursor() as cur:
            mid = self._insert_miembro(cur, encuesta["id"], miembro)
        return {"id": mid, "encuesta_id": encuesta["id"]}

    def list_miembros(self, encuesta_id: int) -> List[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id, m.encuesta_id, m.persona_id,
                    m.is_active, m.created_at, m.updated_at, m.deleted_at,
                    p.cedula  AS cedula_participante,
                    p.nombre  AS nombre_participante,
                    p.edad_anios, p.sexo, p.area_residencia, p.nivel_educativo,
                    m.percepcion_estado_nutricional, m.cambio_peso_no_intencional,
                    m.nino_en_control_crecimiento, m.peso_kg, m.talla_cm,
                    m.circunferencia_cintura_cm, m.perimetro_brazo_cm,
                    m.grupo_perimetro_brazo, m.imc_calculado
                FROM encuesta_nutricional_miembros m
                JOIN personas_nutricionales p ON p.id = m.persona_id
                WHERE m.encuesta_id = %s AND m.is_active = 1
                """,
                (encuesta_id,),
            )
            return cur.fetchall()

    def get_miembro(self, encuesta_id: int, miembro_id: int) -> Optional[dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id, m.encuesta_id, m.persona_id,
                    m.is_active, m.created_at, m.updated_at, m.deleted_at,
                    p.cedula  AS cedula_participante,
                    p.nombre  AS nombre_participante,
                    p.edad_anios, p.sexo, p.area_residencia, p.nivel_educativo,
                    m.percepcion_estado_nutricional, m.cambio_peso_no_intencional,
                    m.nino_en_control_crecimiento, m.peso_kg, m.talla_cm,
                    m.circunferencia_cintura_cm, m.perimetro_brazo_cm,
                    m.grupo_perimetro_brazo, m.imc_calculado
                FROM encuesta_nutricional_miembros m
                JOIN personas_nutricionales p ON p.id = m.persona_id
                WHERE m.id = %s AND m.encuesta_id = %s AND m.is_active = 1
                """,
                (miembro_id, encuesta_id),
            )
            return cur.fetchone()

    def update_miembro(self, encuesta_id: int, miembro_id: int, data: MiembroUpdate) -> bool:
        update_data = data.model_dump(exclude_none=True)
        changed = False

        # nombre_participante → personas_nutricionales.nombre; resto 1:1
        PERSONA_MAP = {
            "nombre_participante": "nombre",
            "edad_anios": "edad_anios",
            "sexo": "sexo",
            "area_residencia": "area_residencia",
            "nivel_educativo": "nivel_educativo",
        }
        persona_cols = {col: update_data[field]
                        for field, col in PERSONA_MAP.items() if field in update_data}

        if persona_cols:
            pf = [f"p.{col} = %s" for col in persona_cols]
            pv = list(persona_cols.values()) + [miembro_id, encuesta_id]
            with get_db_cursor() as cur:
                cur.execute(
                    f"UPDATE personas_nutricionales p "
                    f"JOIN encuesta_nutricional_miembros m ON m.persona_id = p.id "
                    f"SET {', '.join(pf)} "
                    f"WHERE m.id = %s AND m.encuesta_id = %s",
                    pv,
                )
                changed = changed or cur.rowcount > 0

        miembro_cols = {f: update_data[f] for f in _MIEMBRO_UPDATABLE if f in update_data}

        if miembro_cols:
            mf = [f"{f} = %s" for f in miembro_cols]
            mv = list(miembro_cols.values()) + [miembro_id, encuesta_id]
            with get_db_cursor() as cur:
                cur.execute(
                    f"UPDATE encuesta_nutricional_miembros SET {', '.join(mf)} "
                    f"WHERE id = %s AND encuesta_id = %s AND is_active = 1",
                    mv,
                )
                changed = changed or cur.rowcount > 0

        return changed

    def soft_delete_miembro(self, encuesta_id: int, miembro_id: int) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE encuesta_nutricional_miembros "
                "SET is_active = 0, deleted_at = NOW() "
                "WHERE id = %s AND encuesta_id = %s AND is_active = 1",
                (miembro_id, encuesta_id),
            )
            return cur.rowcount > 0
