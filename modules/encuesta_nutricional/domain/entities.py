from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Persona nutricional (tabla maestra de participantes)
# ---------------------------------------------------------------------------

class PersonaNutricionalCreate(BaseModel):
    cedula: str
    nombre: Optional[str] = None
    edad_anios: Optional[int] = Field(None, ge=0, le=120)
    sexo: Optional[str] = Field(None, description="Hombre, Mujer, Otro")
    area_residencia: Optional[str] = Field(None, description="Rural, Urbana")
    nivel_educativo: Optional[str] = Field(
        None, description="Ninguno, Primaria, Secundaria, Técnico, Universitario"
    )


class PersonaNutricionalUpdate(BaseModel):
    nombre: Optional[str] = None
    edad_anios: Optional[int] = None
    sexo: Optional[str] = None
    area_residencia: Optional[str] = None
    nivel_educativo: Optional[str] = None


class PersonaNutricionalDetail(BaseModel):
    id: int
    cedula: str
    nombre: Optional[str] = None
    edad_anios: Optional[int] = None
    sexo: Optional[str] = None
    area_residencia: Optional[str] = None
    nivel_educativo: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Miembro (vincula persona ↔ encuesta + datos Sección B)
# ---------------------------------------------------------------------------

class MiembroCreate(BaseModel):
    # Datos de la persona (se upsertean en personas_nutricionales)
    cedula_participante: str
    nombre_participante: Optional[str] = None
    edad_anios: Optional[int] = Field(None, ge=0, le=120)
    sexo: Optional[str] = Field(None, description="Hombre, Mujer, Otro")
    area_residencia: Optional[str] = Field(None, description="Rural, Urbana")
    nivel_educativo: Optional[str] = Field(
        None, description="Ninguno, Primaria, Secundaria, Técnico, Universitario"
    )

    # Sección B — Estado nutricional (mediciones de esta encuesta)
    percepcion_estado_nutricional: Optional[str] = Field(
        None, description="Muy bajo, Bajo, Adecuado, Alto, Muy alto"
    )
    cambio_peso_no_intencional: Optional[bool] = None
    nino_en_control_crecimiento: Optional[str] = Field(None, description="Sí, No, N/A")
    peso_kg: Optional[float] = Field(None, gt=0)
    talla_cm: Optional[float] = Field(None, gt=0)
    circunferencia_cintura_cm: Optional[float] = Field(None, gt=0, description="Solo adultos ≥18 años")
    perimetro_brazo_cm: Optional[float] = Field(None, gt=0)
    grupo_perimetro_brazo: Optional[str] = Field(
        None, description="Niño <5 años, Adolescente, Adulto"
    )
    imc_calculado: Optional[float] = Field(None, description="kg/m²")


class MiembroUpdate(BaseModel):
    # Datos persona
    nombre_participante: Optional[str] = None
    edad_anios: Optional[int] = None
    sexo: Optional[str] = None
    area_residencia: Optional[str] = None
    nivel_educativo: Optional[str] = None
    # Sección B
    percepcion_estado_nutricional: Optional[str] = None
    cambio_peso_no_intencional: Optional[bool] = None
    nino_en_control_crecimiento: Optional[str] = None
    peso_kg: Optional[float] = None
    talla_cm: Optional[float] = None
    circunferencia_cintura_cm: Optional[float] = None
    perimetro_brazo_cm: Optional[float] = None
    grupo_perimetro_brazo: Optional[str] = None
    imc_calculado: Optional[float] = None


class MiembroDetail(BaseModel):
    id: int
    encuesta_id: int
    persona_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # Campos de persona (via JOIN)
    cedula_participante: str
    nombre_participante: Optional[str] = None
    edad_anios: Optional[int] = None
    sexo: Optional[str] = None
    area_residencia: Optional[str] = None
    nivel_educativo: Optional[str] = None
    # Sección B
    percepcion_estado_nutricional: Optional[str] = None
    cambio_peso_no_intencional: Optional[bool] = None
    nino_en_control_crecimiento: Optional[str] = None
    peso_kg: Optional[float] = None
    talla_cm: Optional[float] = None
    circunferencia_cintura_cm: Optional[float] = None
    perimetro_brazo_cm: Optional[float] = None
    grupo_perimetro_brazo: Optional[str] = None
    imc_calculado: Optional[float] = None


# ---------------------------------------------------------------------------
# Encuesta (datos del hogar)
# ---------------------------------------------------------------------------

class EncuestaNutricionalCreate(BaseModel):
    # --- Encabezado (obligatorio) ---
    nombre_encuestador: str
    cedula_encuestador: str
    fecha_aplicacion: date
    codigo_cuestionario: Optional[str] = None
    municipio: str = Field(..., description="Algarrobo, Fundación, Aracataca, El Retén")
    vereda_comunidad: str

    # --- Sección A — Datos del hogar ---
    num_personas_hogar: Optional[int] = Field(None, ge=1)
    num_mujeres_hogar: Optional[int] = Field(None, ge=0)
    hay_menores_18: Optional[bool] = None
    num_ninos_menores_5: Optional[int] = Field(None, ge=0)
    fuente_ingreso_principal: Optional[str] = Field(
        None,
        description="Empleo/negocio, Ayudas del gobierno, Jornalero, Cría y venta de animales",
    )
    tiene_huerta_o_animales: Optional[bool] = None
    jefatura_hogar: Optional[str] = Field(
        None, description="Padre, Madre, Hijo/a, Abuelo/a, Varios, Otro"
    )
    estabilidad_ingreso: Optional[str] = Field(
        None, description="Fijo todos los meses, Variable (temporadas), Sin ingreso fijo"
    )

    # --- Sección C — Hábitos alimentarios del hogar ---
    dias_cereales_tuberculos: Optional[int] = Field(None, ge=0, le=7)
    dias_leguminosas: Optional[int] = Field(None, ge=0, le=7)
    dias_carnes_pescado_huevo: Optional[int] = Field(None, ge=0, le=7)
    dias_lacteos: Optional[int] = Field(None, ge=0, le=7)
    dias_frutas: Optional[int] = Field(None, ge=0, le=7)
    dias_verduras: Optional[int] = Field(None, ge=0, le=7)
    dias_grasas: Optional[int] = Field(None, ge=0, le=7)
    dias_azucares_ultraprocesados: Optional[int] = Field(None, ge=0, le=7)
    puntaje_diversidad_dietetica: Optional[int] = Field(None, ge=0, le=8)
    frecuencia_frutas_semana: Optional[str] = Field(
        None, description="Ninguno, 1–2 días, 3–4 días, 5–7 días"
    )
    frecuencia_verduras_semana: Optional[str] = Field(
        None, description="Ninguno, 1–2 días, 3–4 días, 5–7 días"
    )
    frecuencia_bebidas_azucaradas: Optional[str] = Field(
        None, description="Nunca, 1–2 veces/semana, 3–4 veces/semana, Diario"
    )
    comidas_por_dia: Optional[str] = Field(None, description="1, 2, 3, 4 o más")
    frecuencia_comida_fuera_hogar: Optional[str] = Field(
        None, description="Nunca, 1–2/semana, 3–4/semana, Diario"
    )
    proporcion_autoconsumo: Optional[str] = Field(
        None, description="Nada, Poca, La mitad, La mayoría"
    )
    alimentos_preferidos: Optional[List[str]] = Field(None, max_length=5)

    # --- Sección D — Seguridad alimentaria (ELCSA) ---
    preocupacion_alimentos_acabaran: Optional[bool] = None
    alimentos_se_acabaron: Optional[bool] = None
    adulto_omitio_comida_principal: Optional[bool] = None
    sintio_hambre_sin_comer: Optional[bool] = None
    puntaje_inseguridad_alimentaria: Optional[int] = Field(None, ge=0, le=4)
    clasificacion_seguridad_alimentaria: Optional[str] = Field(
        None,
        description="Seguridad alimentaria, Inseguridad leve, Inseguridad moderada, Inseguridad severa",
    )

    # --- Cierre (obligatorio) ---
    consentimiento_informado: bool
    observaciones_encuestador: Optional[str] = None

    # --- Miembros del hogar (mínimo 1) ---
    miembros: List[MiembroCreate] = Field(..., min_length=1)


class EncuestaNutricionalUpdate(BaseModel):
    nombre_encuestador: Optional[str] = None
    cedula_encuestador: Optional[str] = None
    fecha_aplicacion: Optional[date] = None
    codigo_cuestionario: Optional[str] = None
    municipio: Optional[str] = None
    vereda_comunidad: Optional[str] = None
    num_personas_hogar: Optional[int] = None
    num_mujeres_hogar: Optional[int] = None
    hay_menores_18: Optional[bool] = None
    num_ninos_menores_5: Optional[int] = None
    fuente_ingreso_principal: Optional[str] = None
    tiene_huerta_o_animales: Optional[bool] = None
    jefatura_hogar: Optional[str] = None
    estabilidad_ingreso: Optional[str] = None
    dias_cereales_tuberculos: Optional[int] = None
    dias_leguminosas: Optional[int] = None
    dias_carnes_pescado_huevo: Optional[int] = None
    dias_lacteos: Optional[int] = None
    dias_frutas: Optional[int] = None
    dias_verduras: Optional[int] = None
    dias_grasas: Optional[int] = None
    dias_azucares_ultraprocesados: Optional[int] = None
    puntaje_diversidad_dietetica: Optional[int] = None
    frecuencia_frutas_semana: Optional[str] = None
    frecuencia_verduras_semana: Optional[str] = None
    frecuencia_bebidas_azucaradas: Optional[str] = None
    comidas_por_dia: Optional[str] = None
    frecuencia_comida_fuera_hogar: Optional[str] = None
    proporcion_autoconsumo: Optional[str] = None
    alimentos_preferidos: Optional[List[str]] = None
    preocupacion_alimentos_acabaran: Optional[bool] = None
    alimentos_se_acabaron: Optional[bool] = None
    adulto_omitio_comida_principal: Optional[bool] = None
    sintio_hambre_sin_comer: Optional[bool] = None
    puntaje_inseguridad_alimentaria: Optional[int] = None
    clasificacion_seguridad_alimentaria: Optional[str] = None
    consentimiento_informado: Optional[bool] = None
    observaciones_encuestador: Optional[str] = None


class ResumenMunicipioItem(BaseModel):
    municipio: str
    total_encuestas: int
    total_miembros: int


class EncuestaNutricionalListItem(BaseModel):
    numero_encuesta: str
    nombre_encuestador: str
    cedula_encuestador: str
    fecha_aplicacion: date
    municipio: str
    vereda_comunidad: str
    total_miembros: int


class EncuestaNutricionalDetail(BaseModel):
    id: int
    numero_encuesta: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    nombre_encuestador: str
    cedula_encuestador: str
    fecha_aplicacion: date
    codigo_cuestionario: Optional[str] = None
    municipio: str
    vereda_comunidad: str
    num_personas_hogar: Optional[int] = None
    num_mujeres_hogar: Optional[int] = None
    hay_menores_18: Optional[bool] = None
    num_ninos_menores_5: Optional[int] = None
    fuente_ingreso_principal: Optional[str] = None
    tiene_huerta_o_animales: Optional[bool] = None
    jefatura_hogar: Optional[str] = None
    estabilidad_ingreso: Optional[str] = None
    dias_cereales_tuberculos: Optional[int] = None
    dias_leguminosas: Optional[int] = None
    dias_carnes_pescado_huevo: Optional[int] = None
    dias_lacteos: Optional[int] = None
    dias_frutas: Optional[int] = None
    dias_verduras: Optional[int] = None
    dias_grasas: Optional[int] = None
    dias_azucares_ultraprocesados: Optional[int] = None
    puntaje_diversidad_dietetica: Optional[int] = None
    frecuencia_frutas_semana: Optional[str] = None
    frecuencia_verduras_semana: Optional[str] = None
    frecuencia_bebidas_azucaradas: Optional[str] = None
    comidas_por_dia: Optional[str] = None
    frecuencia_comida_fuera_hogar: Optional[str] = None
    proporcion_autoconsumo: Optional[str] = None
    alimentos_preferidos: Optional[List[str]] = None
    preocupacion_alimentos_acabaran: Optional[bool] = None
    alimentos_se_acabaron: Optional[bool] = None
    adulto_omitio_comida_principal: Optional[bool] = None
    sintio_hambre_sin_comer: Optional[bool] = None
    puntaje_inseguridad_alimentaria: Optional[int] = None
    clasificacion_seguridad_alimentaria: Optional[str] = None
    consentimiento_informado: bool
    observaciones_encuestador: Optional[str] = None
    miembros: List[MiembroDetail] = []
