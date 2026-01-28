from pydantic import BaseModel, Field
from typing import Optional, Union, List, Literal
from datetime import date, datetime
from uuid import uuid4


def generate_id():
    return str(uuid4())


class EncuestaActores(BaseModel):
    fecha_creacion: Optional[date] = Field(default_factory=date.today)

    # Sección A. Datos del Actor
    id_actor: Optional[str] = Field(default_factory=generate_id)
    email : Optional[str] = None
    nombre_completo: Optional[str] = None
    rol_hub: Optional[List[str]] = None # List[Literal['pescador', 'recolector', 'cuadrilla', 'autoridad ambiental', 'investigador', 'ONG', 'otro']]
    organizacion: Optional[str] = None
    numero_identificacion: str
    contacto: Optional[str] = None
    direccion_comunidad: Optional[str] = None # Literal['Nueva Venecia', 'Buenavista', 'Trojas de Cataca', 'otro']
    fotografia_actor: Optional[str] = None

    # Sección B. Datos de Activos
    id_activo: Optional[str] = Field(default_factory=generate_id)
    tipo_activo: Optional[List[str]] = None #List[Literal['embarcación', 'motor', 'guadaña acuática', 'red', 'rastrillo', 'boom de contención', 'EPP', 'otro']]
    nombre_codigo_activo: str
    propietario_id: Optional[str] = None  # Debe coincidir con id_actor
    numero_serie: Optional[str] = None
    estado_activo: Optional[str] = None  # Literal['operativo', 'requiere mantenimiento', 'fuera de servicio']
    permisos_licencias: Optional[List[str]] = None  # PDF/foto o número de permiso
    fotografia_activo: Optional[str] = None

    # Sección C. Relación Actor–Activo
    rol_en_activo: Optional[str]
    fecha_asignacion: Optional[date] = None
    observaciones: Optional[str] = None

    # Sección D. Seguridad y Consentimiento
    autorizo_datos: Optional[bool] = Field(..., description="Autorizo el uso de mis datos según Ley de Habeas Data")
    activos_bioseguridad: Optional[bool] = Field(..., description="Confirmo que los activos cumplen normas de bioseguridad")


class EncuestaFaena(BaseModel):
    # Sección A. Identificación de la Faena
    id_faena: str = Field(default_factory=generate_id)
    email: Optional[str] = None
    tipo_faena: Optional[str] = None # Literal['remoción artesanal', 'remoción mecánica', 'monitoreo ambiental', 'patrullaje comunitario', 'otro']
    fecha_inicio: Optional[str] = None
    fecha_cierre: Optional[str] = None
    email_actor: Optional[str] = None  # List[str] = Field(..., description="IDs de actores responsables, desde Módulo 1")
    coordinador_faena: Optional[str] = None  # Nombre desde lista desplegable

    # Sección B. Ubicación y Georreferenciación
    punto_inicial_gps: Optional[str]  # Formato lat,long o texto
    punto_final_gps: Optional[str]
    nombre_sector: Optional[str]

    # Sección C. Actividad y Operativa
    superficie_intervenida: float = Field(..., description="m² o ha")
    metodo_utilizado: Optional[List[str]] = None #Literal['guadaña', 'rastrillo', 'barcaza artesanal', 'harvester', 'boom de contención', 'otro']
    numero_personas: int
    horas_trabajadas: float = Field(..., description="Calculadas por check-in/out, ajustable manualmente")
    fotografia_antes: Optional[str] = None # Optional[List[str]] = Field(None, description="URLs o paths de fotos")
    fotografia_despues: Optional[str] = None # Optional[List[str]] = Field(None, description="URLs o paths de fotos")
    checklist_bioseguridad: Optional[List[str]] = None # List[Literal['limpieza de equipos', 'uso de EPP', 'disposición temporal de biomasa', 'protocolos cumplidos']]

    # Sección D. Datos de Captura de Biomasa
    biomasa_humeda_kg: float
    biomasa_seca_kg: Optional[float] = None
    destino_biomasa: Optional[List[str]] = None
    numero_sacos: int
    punto_acopio_asociado: str  # ID o referencia desde Módulo 1

    # Sección E. Monitoreo Ambiental
    oxigeno_disuelto_mgL: float
    turbidez_NTU: float
    salinidad_prom: float
    cpue: Optional[float] = None

    # Sección F. Observaciones y Validación
    incidencias_reportadas: Optional[str] = None
    comentarios_comunitarios: Optional[str] = None
    firma_digital_coordinador: Optional[bool] = Field(None, description="Archivo, dibujo o PIN")
    validacion_institucional: Optional[str] = None #Optional[Literal['✔ validado', '✘ pendiente']] = None


class EncuestaPuntoAcopio(BaseModel):
    # Sección A. Identificación del Punto de Acopio
    email: Optional[str] = None

    id_punto: Optional[str] = Field(default=None, description="ID auto-generado del punto (UUID local, sincronizable)")
    nombre_referencia: Optional[str] = Field(default=None, description="Nombre o referencia local del punto")
    tipo_punto: Optional[str] = Field(default=None, description="Tipo de punto (plataforma flotante, cancha de secado, compostaje, bioenergía, otro)")
    ubicacion: Optional[str] = Field(default=None, description="Coordenadas GPS del punto")
    sector_comunidad: Optional[str] = Field(default=None, description="Sector o comunidad asociada")
    fotografia_georreferenciada: Optional[str] = Field(default=None, description="Fotografía capturada en campo")

    #  Sección B. Datos de Biomasa Depositada
    # id_faena_asociada: Optional[str] = Field(default=None, description="ID de faena asociada")
    fecha_entrega: Optional[datetime] = Field(default=None, description="Fecha y hora de entrega")
    cantidad_humedo_kg: Optional[float] = Field(default=None, description="Cantidad depositada (peso húmedo en kg)")
    cantidad_seco_kg: Optional[float] = Field(default=None, description="Cantidad tras escurrido (peso seco en kg)")
    numero_sacos_unidades: Optional[int] = Field(default=None, description="Número de sacos o unidades")
    estado_biomasa: Optional[str] = Field(default=None, description="Estado de la biomasa (recién cortada, en escurrido, lista para disposición final)")
    observaciones_biomasa: Optional[str] = Field(default=None, description="Observaciones libres")

    # Sección C. Destino y Gestión
    destino_previsto: Optional[List[str]] = Field(default=None, description="Destino previsto (compostaje, biofertilizante, bioenergía, disposición controlada, otro)")
    plazo_permanencia: Optional[str] = Field(default=None, description="Plazo estimado de permanencia en el punto")
    encargado_gestion: Optional[str] = Field(default=None, description="Encargado de gestión (Actor/Organización)")
    registro_transporte: Optional[str] = Field(default=None, description="Registro de transporte (barcaza, camión, canoa) y matrícula/código")
    evidencia_fotografica_documento: Optional[str] = Field(default=None, description="Evidencia fotográfica o documento del traslado")

    # Sección D. Control y Trazabilidad
    checklist_bioseguridad: Optional[List[str]] = Field(default=None, description="Checklist de bioseguridad")
    alertas_automaticas: Optional[bool] = Field(default=None, description="Alertas automáticas si se supera capacidad")
    firma_digital_responsable: Optional[bool] = Field(default=None, description="Firma digital o PIN del responsable de acopio")
    validacion_institucional: Optional[str] = Field(default=None, description="Validación institucional (✔ validado / ✘ pendiente)")


class EncuestaMonitoreoAmbiental(BaseModel):
    #  Sección A. Identificación del Monitoreo
    email: Optional[str] = None
    id_monitoreo: Optional[str] = Field(default=None, description="ID auto-generado del monitoreo (UUID local)")
    fecha: Optional[str] = None
    hora: Optional[str] = None
    cuadrilla_equipo_responsable: Optional[str] = None
    nombre_sector_punto: Optional[str] = None
    ubicacion_gps: Optional[str] = None
    fotografia_sitio: Optional[str] = None

    #  Sección B. Parámetros de Calidad de Agua
    oxigeno_disuelto_mg_l: Optional[float] = Field(default=None, description="Oxígeno disuelto (mg/L)")
    turbidez_ntu: Optional[float] = Field(default=None, description="Turbidez (NTU)")
    salinidad_prom: Optional[float] = Field(default=None, description="Salinidad (‰)")
    ph: Optional[str] = None
    temperatura_c: Optional[str] = None

    #  Sección C. Biodiversidad y Pesca Asociada
    cpue: Optional[str] = Field(default=None, description="Captura por Unidad de Esfuerzo (nº peces/hora)")
    observaciones_fauna: Optional[str] = None
    registro_fotografico_fauna: Optional[str] = None

    #  Sección D. Observaciones y Validación
    incidencias_ambientales: Optional[str] = None
    comentarios_comunitarios: Optional[str] = None
    firma_digital_responsable: Optional[str] = None
    validacion_institucional: Optional[str] = Field(default=None, description="✔ validado / ✘ pendiente, solo perfiles Corpamag/Invemar")

Survey = Union[EncuestaActores, EncuestaFaena, EncuestaPuntoAcopio, EncuestaMonitoreoAmbiental]


class SurveyListRequest(BaseModel):
    email: str
    surveys: List[Survey]
