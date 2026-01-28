from pydantic import BaseModel, Field
from typing import Optional, Union, List, Literal
from datetime import date, datetime

class EncuestaAgrohub(BaseModel):
    id: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    type: Literal['agrohub']
    email: Optional[str] = None
    # Metadatos
    nombre_aplicador: Optional[str] = None
    fecha_aplicacion: Optional[date] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None
    nombre_organizacion: Optional[str] = None
    tipo_organizacion: Optional[str] = None

    # 1. Información General
    anio_conformacion: Optional[int] = None
    numero_miembros: Optional[int] = None
    numero_nucleos_familiares: Optional[int] = None
    cobertura_territorial: Optional[str] = None
    representante_legal: Optional[str] = None
    contacto: Optional[str] = None

    # 2. Perfil Productivo y Agroecológico
    tipos_agricultura: Optional[str] = None
    cultivan_hortalizas: Optional[str] = None
    cuales_hortalizas: Optional[str] = None
    area_hortalizas: Optional[int] = None
    destino_hortalizas: Optional[str] = None
    actividades_complementarias: Optional[str] = None
    tiene_patio: Optional[str] = None
    area_patio: Optional[int] = None
    condiciones_terreno: Optional[str] = None

    # 3. Madurez Organizativa
    formalizacion: Optional[str] = None
    asociatividad: Optional[str] = None
    experiencia_proyectos: Optional[str] = None
    descripcion_experiencia: Optional[str] = None
    tiene_estatutos_plan: Optional[str] = None
    acceso_mercado: Optional[str] = None
    frecuencia_venta: Optional[str] = None
    manejo_administrativo: Optional[str] = None

    # 4. Apropiación Tecnológica
    tecnologias_usadas: Optional[str] = None
    otras_tecnologias: Optional[str] = None
    capacidad_aprendizaje: Optional[str] = None
    comentarios: Optional[str] = None
    conectividad: Optional[str] = None

    # 5. Perspectivas
    expectativas: Optional[str] = None
    compromisos: Optional[str] = None
    limitaciones: Optional[str] = None

    # 6. Geolocalización
    latitud: Optional[str] = None
    longitud: Optional[str] = None


class EncuestaEducativa(BaseModel):
    id: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    type: Literal['educativa']
    email: Optional[str] = None
    # Metadatos
    nombre_aplicador: Optional[str] = None
    fecha_aplicacion: Optional[date] = None
    municipio: Optional[str] = None
    vereda: Optional[str] = None
    nombre_institucion: Optional[str] = None
    codigo_dane: Optional[str] = None
    nombre_directivo: Optional[str] = None
    contacto: Optional[str] = None

    # 1. Información General
    tipo_institucion: Optional[str] = None
    sedes: Optional[str] = None
    numero_estudiantes: Optional[int] = None
    numero_docentes: Optional[int] = None
    grados_atiende: Optional[str] = None
    tiene_prae: Optional[bool] = None
    prae_descripcion: Optional[str] = None

    # 2. Experiencia y Enfoque
    experiencia_proyectos: Optional[bool] = None
    descripcion_proyectos: Optional[str] = None
    tiene_huerta: Optional[bool] = None
    area_huerta: Optional[int] = None
    uso_huerta: Optional[str] = None
    temas_agroambientales: Optional[str] = None

    # 3. Infraestructura
    espacio_agrohub: Optional[bool] = None
    area_agrohub: Optional[int] = None
    condiciones_terreno: Optional[str] = None
    internet: Optional[str] = None
    espacios_complementarios: Optional[bool] = None
    cantidad_espacios: Optional[int] = None
    laboratorio: Optional[bool] = None
    laboratorio_funciona: Optional[bool] = None

    # 4. Vinculación Comunitaria
    actores_comunitarios: Optional[str] = None
    tiene_alianzas: Optional[bool] = None
    descripcion_alianzas: Optional[str] = None

    # 5. Capacidades de Innovación
    tiene_semilleros: Optional[bool] = None
    nombre_grupo: Optional[str] = None
    interes_agricultura: Optional[str] = None
    medios_comunicacion: Optional[str] = None

    # 6. Expectativas
    expectativas: Optional[str] = None
    compromisos: Optional[str] = None
    limitaciones: Optional[str] = None

    # 7. Observaciones Finales
    comentarios: Optional[str] = None
    anexa_documentos: Optional[bool] = None

    # 8. Geolocalización
    latitud: Optional[str] = None
    longitud: Optional[str] = None


class EncuestaDerechoHumanoAlimentario(BaseModel):
    id: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    type: Literal['derecho_humano_alimentario']
    email: Optional[str] = None

    # Metadatos y datos generales
    fecha_aplicacion: Optional[date] = None
    nombre_jefe_hogar: Optional[str] = None
    edad: Optional[int] = None
    genero: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    subregion: Optional[str] = None
    numero_miembros_hogar: Optional[int] = None
    nivel_educativo: Optional[str] = None
    nombre_encuestador: Optional[str] = None
    cargo_encuestador: Optional[str] = None

    # Agricultura Familiar
    dedicado_agricultura: Optional[bool] = None
    cultivos_principales: Optional[str] = None
    razon_produccion: Optional[str] = None

    # Disponibilidad de alimentos
    cobertura_necesidades: Optional[bool] = None
    meses_escasez: Optional[str] = None
    cambios_produccion: Optional[str] = None
    razon_cambios: Optional[str] = None
    acceso_insumos_agricolas: Optional[bool] = None
    asistencia_tecnica: Optional[bool] = None

    # Accesibilidad a alimentos
    compra_suficiente_alimentos: Optional[bool] = None
    acceso_mercado: Optional[bool] = None
    distancia_mercado: Optional[str] = None
    alimento_asequible: Optional[bool] = None
    reduccion_consumo: Optional[bool] = None
    ayuda_alimentaria: Optional[bool] = None

    # Adecuación de alimentos
    dieta_balanceada: Optional[bool] = None
    consumo_grupos_alimenticios: Optional[str] = None
    agua_potable_preparacion: Optional[bool] = None
    enfermedades_transmitidas: Optional[bool] = None
    alimentos_culturalmente_aceptables: Optional[bool] = None
    higiene_manipulacion: Optional[bool] = None

    # Percepción y conocimiento
    conoce_derecho_alimentacion: Optional[bool] = None
    cree_derecho_respetado: Optional[bool] = None
    medidas_mejorar_acceso: Optional[str] = None

    # Geolocalización
    latitud: Optional[str] = None
    longitud: Optional[str] = None


Survey = Union[EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario]


class SurveyListRequest(BaseModel):
    email: str
    surveys: List[Survey]


class SurveyLocationInfo(BaseModel):
    type: str
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    municipio: Optional[str] = None
    fecha_aplicacion: Optional[date] = None