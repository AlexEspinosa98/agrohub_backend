import uuid

from django.db import models


def generate_id():
    return str(uuid.uuid4())


class EncuestaActor(models.Model):
    """Sección A/B/C/D del formulario de actores del HUB CGSM.

    NOTE: the original FastAPI repository for this table mixed up Postgres-only
    SQL (execute_values/ON CONFLICT/RETURNING) against a MySQL connection and
    referenced field names that don't even exist on the domain entity — it
    never actually worked. This model follows the field set from the Pydantic
    domain entity (modules/hub_cgsm/domain_hub_cgsm/entities.py), which is the
    real contract the mobile client sends.
    """

    fecha_creacion = models.DateField(null=True, blank=True)

    id_actor = models.CharField(max_length=191, unique=True, default=generate_id)
    email = models.TextField(null=True, blank=True)
    nombre_completo = models.TextField(null=True, blank=True)
    rol_hub = models.JSONField(null=True, blank=True)
    organizacion = models.TextField(null=True, blank=True)
    numero_identificacion = models.TextField()
    contacto = models.TextField(null=True, blank=True)
    direccion_comunidad = models.TextField(null=True, blank=True)
    fotografia_actor = models.TextField(null=True, blank=True)

    id_activo = models.CharField(max_length=191, default=generate_id)
    tipo_activo = models.JSONField(null=True, blank=True)
    nombre_codigo_activo = models.TextField()
    propietario_id = models.TextField(null=True, blank=True)
    numero_serie = models.TextField(null=True, blank=True)
    estado_activo = models.TextField(null=True, blank=True)
    permisos_licencias = models.JSONField(null=True, blank=True)
    fotografia_activo = models.TextField(null=True, blank=True)

    rol_en_activo = models.TextField(null=True, blank=True)
    fecha_asignacion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    autorizo_datos = models.BooleanField(null=True, blank=True)
    activos_bioseguridad = models.BooleanField(null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuestas_actores"

    SURVEY_TYPE = "actores"


class EncuestaFaena(models.Model):
    id_faena = models.CharField(max_length=191, unique=True, default=generate_id)
    email = models.TextField(null=True, blank=True)
    tipo_faena = models.TextField(null=True, blank=True)
    fecha_inicio = models.CharField(max_length=100, null=True, blank=True)
    fecha_cierre = models.CharField(max_length=100, null=True, blank=True)
    email_actor = models.TextField(null=True, blank=True)
    coordinador_faena = models.TextField(null=True, blank=True)

    punto_inicial_gps = models.TextField(null=True, blank=True)
    punto_final_gps = models.TextField(null=True, blank=True)
    nombre_sector = models.TextField(null=True, blank=True)

    superficie_intervenida = models.FloatField(null=True, blank=True)
    metodo_utilizado = models.JSONField(null=True, blank=True)
    numero_personas = models.IntegerField(null=True, blank=True)
    horas_trabajadas = models.FloatField(null=True, blank=True)
    fotografia_antes = models.TextField(null=True, blank=True)
    fotografia_despues = models.TextField(null=True, blank=True)
    checklist_bioseguridad = models.JSONField(null=True, blank=True)

    biomasa_humeda_kg = models.FloatField(null=True, blank=True)
    biomasa_seca_kg = models.FloatField(null=True, blank=True)
    destino_biomasa = models.JSONField(null=True, blank=True)
    numero_sacos = models.IntegerField(null=True, blank=True)
    punto_acopio_asociado = models.TextField(null=True, blank=True)

    oxigeno_disuelto_mgL = models.FloatField(null=True, blank=True)
    turbidez_NTU = models.FloatField(null=True, blank=True)
    salinidad_prom = models.FloatField(null=True, blank=True)
    cpue = models.FloatField(null=True, blank=True)

    incidencias_reportadas = models.TextField(null=True, blank=True)
    comentarios_comunitarios = models.TextField(null=True, blank=True)
    firma_digital_coordinador = models.BooleanField(null=True, blank=True)
    validacion_institucional = models.TextField(null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuestas_faenas"

    SURVEY_TYPE = "faena"


class PuntoAcopioBiomasa(models.Model):
    email = models.TextField(null=True, blank=True)

    id_punto = models.CharField(max_length=191, unique=True, null=True, blank=True)
    nombre_referencia = models.TextField(null=True, blank=True)
    tipo_punto = models.TextField(null=True, blank=True)
    ubicacion = models.TextField(null=True, blank=True)
    sector_comunidad = models.TextField(null=True, blank=True)
    fotografia_georreferenciada = models.TextField(null=True, blank=True)

    fecha_entrega = models.DateTimeField(null=True, blank=True)
    cantidad_humedo_kg = models.FloatField(null=True, blank=True)
    cantidad_seco_kg = models.FloatField(null=True, blank=True)
    numero_sacos_unidades = models.IntegerField(null=True, blank=True)
    estado_biomasa = models.TextField(null=True, blank=True)
    observaciones_biomasa = models.TextField(null=True, blank=True)

    destino_previsto = models.JSONField(null=True, blank=True)
    plazo_permanencia = models.TextField(null=True, blank=True)
    encargado_gestion = models.TextField(null=True, blank=True)
    registro_transporte = models.TextField(null=True, blank=True)
    evidencia_fotografica_documento = models.TextField(null=True, blank=True)

    checklist_bioseguridad = models.JSONField(null=True, blank=True)
    alertas_automaticas = models.BooleanField(null=True, blank=True)
    firma_digital_responsable = models.BooleanField(null=True, blank=True)
    validacion_institucional = models.TextField(null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "puntos_acopio_biomasa"

    SURVEY_TYPE = "acopio"


class MonitoreoAmbiental(models.Model):
    email = models.TextField(null=True, blank=True)
    id_monitoreo = models.CharField(max_length=191, unique=True, null=True, blank=True)
    fecha = models.CharField(max_length=100, null=True, blank=True)
    hora = models.CharField(max_length=100, null=True, blank=True)
    cuadrilla_equipo_responsable = models.TextField(null=True, blank=True)
    nombre_sector_punto = models.TextField(null=True, blank=True)
    ubicacion_gps = models.TextField(null=True, blank=True)
    fotografia_sitio = models.TextField(null=True, blank=True)

    oxigeno_disuelto_mg_l = models.FloatField(null=True, blank=True)
    turbidez_ntu = models.FloatField(null=True, blank=True)
    salinidad_prom = models.FloatField(null=True, blank=True)
    ph = models.CharField(max_length=100, null=True, blank=True)
    temperatura_c = models.CharField(max_length=100, null=True, blank=True)

    cpue = models.CharField(max_length=100, null=True, blank=True)
    observaciones_fauna = models.TextField(null=True, blank=True)
    registro_fotografico_fauna = models.TextField(null=True, blank=True)

    incidencias_ambientales = models.TextField(null=True, blank=True)
    comentarios_comunitarios = models.TextField(null=True, blank=True)
    firma_digital_responsable = models.TextField(null=True, blank=True)
    validacion_institucional = models.TextField(null=True, blank=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoreos_ambientales"

    SURVEY_TYPE = "ambiental"
