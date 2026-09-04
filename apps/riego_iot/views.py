import secrets
from datetime import datetime, timedelta, timezone

from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.response import Response

from apps.riego_iot.models import (
    Dispositivo, EstadoConexion, EstadoValvula, Healthcheck, LecturaAmbiente, LecturaSuelo,
)
from apps.riego_iot.mosquitto_admin import MosquittoAdminError, crear_credencial, eliminar_credencial, rotar_password
from apps.riego_iot.permissions import TieneApiKeyRiego
from apps.riego_iot.serializers import DispositivoCrearSerializer, DispositivoSerializer

# Ventana usada para decidir "conectado ahora" cuando no hay un status/LWT reciente que lo diga
# explícitamente — coincide con la ventana de 3 minutos del manual UG56 (sección 08) para el
# failover nube->local, mismo criterio con el que el propio gateway decide "perdí la nube".
VENTANA_CONEXION = timedelta(minutes=3)

_API_KEY_HEADER = OpenApiParameter(
    "X-API-Key", str, OpenApiParameter.HEADER, required=True,
    description="API key única de administración de riego IoT (interna, no es la del usuario final).",
)

_LECTURA_QUERY_PARAMS = [
    _API_KEY_HEADER,
    OpenApiParameter("desde", str, OpenApiParameter.QUERY, description="ISO 8601. Default: hasta - 7 días."),
    OpenApiParameter("hasta", str, OpenApiParameter.QUERY, description="ISO 8601. Default: ahora."),
    OpenApiParameter("limite", int, OpenApiParameter.QUERY, description="Tope de filas, máx. 5000.", default=500),
]

def _resumen_fields():
    return {
        "device_id": serializers.CharField(),
        "en_linea": serializers.BooleanField(),
        "ultimo_visto": serializers.DateTimeField(allow_null=True),
        "modo_control": serializers.ChoiceField(choices=["nube", "local"], allow_null=True),
        "ambiente": inline_serializer("AmbienteResumen", {
            "medido_en": serializers.DateTimeField(), "temperatura": serializers.FloatField(allow_null=True),
            "humedad": serializers.FloatField(allow_null=True), "dev_eui": serializers.CharField(allow_null=True),
        }, allow_null=True),
        "suelo": inline_serializer("SueloResumen", {
            "medido_en": serializers.DateTimeField(), "humedad_suelo": serializers.FloatField(allow_null=True),
            "temperatura_suelo": serializers.FloatField(allow_null=True), "conductividad": serializers.FloatField(allow_null=True),
            "dev_eui": serializers.CharField(allow_null=True),
        }, allow_null=True),
        "valvulas": inline_serializer("ValvulasResumen", {
            "medido_en": serializers.DateTimeField(), "ro1": serializers.BooleanField(allow_null=True),
            "ro2": serializers.BooleanField(allow_null=True),
            "origen": serializers.ChoiceField(choices=["auto", "remoto", "manual", "reportado"], allow_null=True),
            "ultimo_comando": serializers.CharField(allow_null=True),
        }, allow_null=True),
        "health": inline_serializer("HealthResumen", {
            "medido_en": serializers.DateTimeField(), "mqtt_conectado": serializers.BooleanField(allow_null=True),
            "modo_control": serializers.ChoiceField(choices=["nube", "local"], allow_null=True),
            "override_manual": serializers.BooleanField(allow_null=True), "valvulas": serializers.JSONField(allow_null=True),
        }, allow_null=True),
    }


ResumenDispositivoSerializer = type("ResumenDispositivoSerializer", (serializers.Serializer,), _resumen_fields())
_RESUMEN_RESPONSE = ResumenDispositivoSerializer()


def _generar_password():
    return secrets.token_hex(16)


def _obtener_dispositivo_o_404(device_id):
    dispositivo = Dispositivo.objects.filter(device_id=device_id).first()
    if not dispositivo:
        raise NotFound(f"No existe el dispositivo '{device_id}'.")
    return dispositivo


@extend_schema(
    methods=["GET"],
    tags=["riego-iot"],
    summary="Listar gateways registrados",
    parameters=[
        _API_KEY_HEADER,
        OpenApiParameter("solo_activos", str, OpenApiParameter.QUERY, description="'true' para excluir los dados de baja."),
    ],
    responses={200: DispositivoSerializer(many=True)},
)
@extend_schema(
    methods=["POST"],
    tags=["riego-iot"],
    summary="Registrar un gateway nuevo (crea su credencial MQTT real en Mosquitto)",
    description=(
        "Efecto colateral real: crea usuario+ACL en Mosquitto (mosquitto_admin.crear_credencial) "
        "y recarga el broker. La contraseña generada se devuelve UNA sola vez — no queda guardada "
        "en ningún lado en texto plano, ver `nota` en la respuesta."
    ),
    parameters=[_API_KEY_HEADER],
    request=DispositivoCrearSerializer,
    examples=[OpenApiExample("Registrar gateway", value={
        "device_id": "device0017", "client_id": "ug56-agrohub17", "nombre": "Finca La Esperanza",
    }, request_only=True)],
    responses={
        201: OpenApiResponse(
            response=inline_serializer("DispositivoCreado", {
                "device_id": serializers.CharField(), "client_id": serializers.CharField(),
                "base_topic": serializers.CharField(), "password": serializers.CharField(),
                "nota": serializers.CharField(),
            }),
            examples=[OpenApiExample("Creado", value={
                "device_id": "device0017", "client_id": "ug56-agrohub17", "base_topic": "ahub/device0017",
                "password": "3f9a1c...(32 hex)", "nota": "Guarda esta contraseña ahora — no se puede volver a consultar. ...",
            })],
        ),
        400: OpenApiResponse(description="device_id/client_id con formato inválido, o ya existe un dispositivo activo con ese device_id."),
        502: OpenApiResponse(description="Falló mosquitto_admin (no se pudo escribir la credencial o recargar el broker)."),
    },
)
@api_view(["GET", "POST"])
@permission_classes([TieneApiKeyRiego])
def dispositivos(request):
    if request.method == "GET":
        qs = Dispositivo.objects.all().order_by("device_id")
        if request.query_params.get("solo_activos") == "true":
            qs = qs.filter(activo=True)
        return Response(DispositivoSerializer(qs, many=True).data)

    serializer = DispositivoCrearSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    existente = Dispositivo.objects.filter(device_id=datos["device_id"]).first()
    if existente and existente.activo:
        raise ValidationError(
            f"Ya existe un dispositivo activo con device_id '{datos['device_id']}'. "
            f"Elimínalo primero o usa otro device_id."
        )

    base_topic = f"ahub/{datos['device_id']}"
    password = _generar_password()

    try:
        crear_credencial(datos["client_id"], datos["device_id"], password)
    except MosquittoAdminError as e:
        return Response({"detail": str(e)}, status=502)

    now = datetime.now(timezone.utc)
    Dispositivo.objects.update_or_create(
        device_id=datos["device_id"],
        defaults={
            "base_topic": base_topic,
            "client_id": datos["client_id"],
            "nombre": datos.get("nombre"),
            "activo": True,
            "primera_vez_visto": now,
            "ultima_vez_visto": now,
            "creado_en": now,
        },
    )

    return Response(
        {
            "device_id": datos["device_id"],
            "client_id": datos["client_id"],
            "base_topic": base_topic,
            "password": password,
            "nota": (
                "Guarda esta contraseña ahora — no se puede volver a consultar. Configurar en "
                "el gateway: host back.alunaia.co, puerto 8883, TLS, usuario y Client ID = "
                "client_id, keepalive 15s, clean session desactivado (ver manual UG56, sección 03)."
            ),
        },
        status=201,
    )


@extend_schema(
    methods=["GET"],
    tags=["riego-iot"],
    summary="Detalle de un gateway registrado",
    parameters=[_API_KEY_HEADER],
    responses={200: DispositivoSerializer, 404: OpenApiResponse(description="No existe ese device_id.")},
)
@extend_schema(
    methods=["DELETE"],
    tags=["riego-iot"],
    summary="Dar de baja un gateway (revoca su credencial MQTT, no borra sus lecturas históricas)",
    parameters=[_API_KEY_HEADER],
    responses={
        204: OpenApiResponse(description="Credencial eliminada de Mosquitto y dispositivo marcado inactivo."),
        400: OpenApiResponse(description="El dispositivo no tiene client_id registrado (fue detectado solo por telemetría) — hay que borrar su credencial a mano en Mosquitto."),
        404: OpenApiResponse(description="No existe ese device_id."),
        502: OpenApiResponse(description="Falló mosquitto_admin al eliminar la credencial."),
    },
)
@api_view(["GET", "DELETE"])
@permission_classes([TieneApiKeyRiego])
def dispositivo_detalle(request, device_id):
    dispositivo = _obtener_dispositivo_o_404(device_id)

    if request.method == "GET":
        return Response(DispositivoSerializer(dispositivo).data)

    if not dispositivo.client_id:
        raise ValidationError(
            f"'{device_id}' no tiene client_id registrado (fue creado antes de esta API, o solo "
            f"se detectó por telemetría) — elimina su credencial a mano en Mosquitto primero."
        )

    try:
        eliminar_credencial(dispositivo.client_id)
    except MosquittoAdminError as e:
        return Response({"detail": str(e)}, status=502)

    dispositivo.activo = False
    dispositivo.save(update_fields=["activo"])
    # Las lecturas históricas NO se borran — solo se corta el acceso y se marca inactivo.
    return Response(status=204)


@extend_schema(
    tags=["riego-iot"],
    summary="Rotar la contraseña MQTT de un gateway",
    description="La contraseña anterior deja de funcionar de inmediato al aplicarse (recarga el broker).",
    parameters=[_API_KEY_HEADER],
    request=None,
    responses={
        200: OpenApiResponse(
            response=inline_serializer("PasswordRotado", {
                "client_id": serializers.CharField(), "password": serializers.CharField(), "nota": serializers.CharField(),
            }),
            examples=[OpenApiExample("OK", value={
                "client_id": "ug56-agrohub1", "password": "9c2e...(32 hex)",
                "nota": "Guarda esta contraseña ahora y actualízala en el gateway — la anterior deja de funcionar de inmediato.",
            })],
        ),
        400: OpenApiResponse(description="El dispositivo no tiene client_id registrado."),
        404: OpenApiResponse(description="No existe ese device_id."),
        502: OpenApiResponse(description="Falló mosquitto_admin al rotar la contraseña."),
    },
)
@api_view(["POST"])
@permission_classes([TieneApiKeyRiego])
def rotar_password_dispositivo(request, device_id):
    dispositivo = _obtener_dispositivo_o_404(device_id)
    if not dispositivo.client_id:
        raise ValidationError(f"'{device_id}' no tiene client_id registrado.")

    password = _generar_password()
    try:
        rotar_password(dispositivo.client_id, password)
    except MosquittoAdminError as e:
        return Response({"detail": str(e)}, status=502)

    return Response({
        "client_id": dispositivo.client_id,
        "password": password,
        "nota": "Guarda esta contraseña ahora y actualízala en el gateway — la anterior deja de funcionar de inmediato.",
    })


def _resumen_dispositivo(device_id):
    health = Healthcheck.objects.filter(device_id=device_id).order_by("-medido_en").first()
    conexion = EstadoConexion.objects.filter(device_id=device_id).order_by("-recibido_en").first()
    ambiente = LecturaAmbiente.objects.filter(device_id=device_id).order_by("-medido_en").first()
    suelo = LecturaSuelo.objects.filter(device_id=device_id).order_by("-medido_en").first()
    valvulas = EstadoValvula.objects.filter(device_id=device_id).order_by("-medido_en").first()

    ultimo_visto = None
    for fila in (health, ambiente, suelo):
        if fila and fila.medido_en:
            ultimo_visto = max(ultimo_visto, fila.medido_en) if ultimo_visto else fila.medido_en

    en_linea = bool(
        conexion and conexion.estado == "online"
        and ultimo_visto and (datetime.now(timezone.utc) - ultimo_visto) <= VENTANA_CONEXION
    )

    def _serializar(instancia, campos):
        if not instancia:
            return None
        return {campo: getattr(instancia, campo) for campo in campos}

    return {
        "device_id": device_id,
        "en_linea": en_linea,
        "ultimo_visto": ultimo_visto,
        "modo_control": health.modo_control if health else None,
        "ambiente": _serializar(ambiente, ["medido_en", "temperatura", "humedad", "dev_eui"]),
        "suelo": _serializar(suelo, ["medido_en", "humedad_suelo", "temperatura_suelo", "conductividad", "dev_eui"]),
        "valvulas": _serializar(valvulas, ["medido_en", "ro1", "ro2", "origen", "ultimo_comando"]),
        "health": _serializar(health, ["medido_en", "mqtt_conectado", "modo_control", "override_manual", "valvulas"]),
    }


@extend_schema(
    tags=["riego-iot"],
    summary="Resumen en vivo de todos los gateways activos",
    description="Última lectura de cada tipo (ambiente/suelo/válvulas/health) por dispositivo — la forma más rápida de ver qué está reportando cada uno ahora mismo.",
    parameters=[_API_KEY_HEADER],
    responses={200: ResumenDispositivoSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([TieneApiKeyRiego])
def dashboard_resumen(request):
    """Todos los gateways activos con su último dato de cada tipo — las variables que se están
    enviando ahora mismo, de un vistazo."""
    ids = Dispositivo.objects.filter(activo=True).order_by("device_id").values_list("device_id", flat=True)
    return Response([_resumen_dispositivo(device_id) for device_id in ids])


@extend_schema(
    tags=["riego-iot"],
    summary="Resumen en vivo de un gateway puntual",
    parameters=[_API_KEY_HEADER],
    responses={200: _RESUMEN_RESPONSE, 404: OpenApiResponse(description="No existe ese device_id.")},
)
@api_view(["GET"])
@permission_classes([TieneApiKeyRiego])
def dashboard_detalle(request, device_id):
    _obtener_dispositivo_o_404(device_id)
    return Response(_resumen_dispositivo(device_id))


def _rango_fechas(request):
    hasta = parse_datetime(request.query_params.get("hasta", "")) or datetime.now(timezone.utc)
    desde = parse_datetime(request.query_params.get("desde", "")) or (hasta - timedelta(days=7))
    try:
        limite = int(request.query_params.get("limite", 500))
    except ValueError:
        raise ParseError("limite debe ser un entero.")
    return desde, hasta, min(limite, 5000)


@extend_schema(
    tags=["riego-iot"],
    summary="Histórico de lecturas de ambiente (temperatura/humedad) de un gateway",
    parameters=_LECTURA_QUERY_PARAMS,
    responses={200: inline_serializer("LecturaAmbienteItem", {
        "medido_en": serializers.DateTimeField(), "temperatura": serializers.FloatField(allow_null=True),
        "humedad": serializers.FloatField(allow_null=True), "dev_eui": serializers.CharField(allow_null=True),
        "recuperado": serializers.BooleanField(),
    }, many=True)},
)
@api_view(["GET"])
@permission_classes([TieneApiKeyRiego])
def lecturas_ambiente_dispositivo(request, device_id):
    desde, hasta, limite = _rango_fechas(request)
    qs = (
        LecturaAmbiente.objects.filter(device_id=device_id, medido_en__range=(desde, hasta))
        .order_by("-medido_en")[:limite]
    )
    return Response([
        {
            "medido_en": r.medido_en, "temperatura": r.temperatura, "humedad": r.humedad,
            "dev_eui": r.dev_eui, "recuperado": r.recuperado,
        }
        for r in qs
    ])


@extend_schema(
    tags=["riego-iot"],
    summary="Histórico de lecturas de suelo (humedad/temperatura/conductividad) de un gateway",
    parameters=_LECTURA_QUERY_PARAMS,
    responses={200: inline_serializer("LecturaSueloItem", {
        "medido_en": serializers.DateTimeField(), "humedad_suelo": serializers.FloatField(allow_null=True),
        "temperatura_suelo": serializers.FloatField(allow_null=True), "conductividad": serializers.FloatField(allow_null=True),
        "dev_eui": serializers.CharField(allow_null=True), "recuperado": serializers.BooleanField(),
    }, many=True)},
)
@api_view(["GET"])
@permission_classes([TieneApiKeyRiego])
def lecturas_suelo_dispositivo(request, device_id):
    desde, hasta, limite = _rango_fechas(request)
    qs = (
        LecturaSuelo.objects.filter(device_id=device_id, medido_en__range=(desde, hasta))
        .order_by("-medido_en")[:limite]
    )
    return Response([
        {
            "medido_en": r.medido_en, "humedad_suelo": r.humedad_suelo,
            "temperatura_suelo": r.temperatura_suelo, "conductividad": r.conductividad,
            "dev_eui": r.dev_eui, "recuperado": r.recuperado,
        }
        for r in qs
    ])
