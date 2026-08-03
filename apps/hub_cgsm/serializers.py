from rest_framework import serializers


def _text(**kwargs):
    return serializers.CharField(required=False, allow_null=True, allow_blank=True, **kwargs)


def _int(**kwargs):
    return serializers.IntegerField(required=False, allow_null=True, **kwargs)


def _float(**kwargs):
    return serializers.FloatField(required=False, allow_null=True, **kwargs)


def _bool(**kwargs):
    kwargs.setdefault("required", False)
    return serializers.BooleanField(allow_null=True, **kwargs)


def _list(**kwargs):
    return serializers.ListField(child=serializers.CharField(), required=False, allow_null=True, **kwargs)


class EncuestaActorSerializer(serializers.Serializer):
    fecha_creacion = serializers.DateField(required=False, allow_null=True)
    id_actor = serializers.CharField(required=False)
    email = _text()
    nombre_completo = _text()
    rol_hub = _list()
    organizacion = _text()
    numero_identificacion = serializers.CharField()
    contacto = _text()
    direccion_comunidad = _text()
    fotografia_actor = _text()
    id_activo = serializers.CharField(required=False)
    tipo_activo = _list()
    nombre_codigo_activo = serializers.CharField()
    propietario_id = _text()
    numero_serie = _text()
    estado_activo = _text()
    permisos_licencias = _list()
    fotografia_activo = _text()
    rol_en_activo = _text()
    fecha_asignacion = serializers.DateField(required=False, allow_null=True)
    observaciones = _text()
    autorizo_datos = _bool(required=True)
    activos_bioseguridad = _bool(required=True)


class EncuestaFaenaSerializer(serializers.Serializer):
    id_faena = serializers.CharField(required=False)
    email = _text()
    tipo_faena = _text()
    fecha_inicio = _text()
    fecha_cierre = _text()
    email_actor = _text()
    coordinador_faena = _text()
    punto_inicial_gps = _text()
    punto_final_gps = _text()
    nombre_sector = _text()
    superficie_intervenida = serializers.FloatField()
    metodo_utilizado = _list()
    numero_personas = serializers.IntegerField()
    horas_trabajadas = serializers.FloatField()
    fotografia_antes = _text()
    fotografia_despues = _text()
    checklist_bioseguridad = _list()
    biomasa_humeda_kg = serializers.FloatField()
    biomasa_seca_kg = _float()
    destino_biomasa = _list()
    numero_sacos = serializers.IntegerField()
    punto_acopio_asociado = serializers.CharField()
    oxigeno_disuelto_mgL = serializers.FloatField()
    turbidez_NTU = serializers.FloatField()
    salinidad_prom = serializers.FloatField()
    cpue = _float()
    incidencias_reportadas = _text()
    comentarios_comunitarios = _text()
    firma_digital_coordinador = _bool()
    validacion_institucional = _text()


class EncuestaPuntoAcopioSerializer(serializers.Serializer):
    email = _text()
    id_punto = _text()
    nombre_referencia = _text()
    tipo_punto = _text()
    ubicacion = _text()
    sector_comunidad = _text()
    fotografia_georreferenciada = _text()
    fecha_entrega = serializers.DateTimeField(required=False, allow_null=True)
    cantidad_humedo_kg = _float()
    cantidad_seco_kg = _float()
    numero_sacos_unidades = _int()
    estado_biomasa = _text()
    observaciones_biomasa = _text()
    destino_previsto = _list()
    plazo_permanencia = _text()
    encargado_gestion = _text()
    registro_transporte = _text()
    evidencia_fotografica_documento = _text()
    checklist_bioseguridad = _list()
    alertas_automaticas = _bool()
    firma_digital_responsable = _bool()
    validacion_institucional = _text()


class EncuestaMonitoreoAmbientalSerializer(serializers.Serializer):
    email = _text()
    id_monitoreo = _text()
    fecha = _text()
    hora = _text()
    cuadrilla_equipo_responsable = _text()
    nombre_sector_punto = _text()
    ubicacion_gps = _text()
    fotografia_sitio = _text()
    oxigeno_disuelto_mg_l = _float()
    turbidez_ntu = _float()
    salinidad_prom = _float()
    ph = _text()
    temperatura_c = _text()
    cpue = _text()
    observaciones_fauna = _text()
    registro_fotografico_fauna = _text()
    incidencias_ambientales = _text()
    comentarios_comunitarios = _text()
    firma_digital_responsable = _text()
    validacion_institucional = _text()


SERIALIZER_BY_TYPE = {
    "actores": EncuestaActorSerializer,
    "faena": EncuestaFaenaSerializer,
    "acopio": EncuestaPuntoAcopioSerializer,
    "ambiental": EncuestaMonitoreoAmbientalSerializer,
}
