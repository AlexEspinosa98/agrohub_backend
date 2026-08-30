import secrets
from datetime import datetime, timedelta, timezone

from django.utils.dateparse import parse_datetime
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


def _generar_password():
    return secrets.token_hex(16)


def _obtener_dispositivo_o_404(device_id):
    dispositivo = Dispositivo.objects.filter(device_id=device_id).first()
    if not dispositivo:
        raise NotFound(f"No existe el dispositivo '{device_id}'.")
    return dispositivo


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


@api_view(["GET"])
@permission_classes([TieneApiKeyRiego])
def dashboard_resumen(request):
    """Todos los gateways activos con su último dato de cada tipo — las variables que se están
    enviando ahora mismo, de un vistazo."""
    ids = Dispositivo.objects.filter(activo=True).order_by("device_id").values_list("device_id", flat=True)
    return Response([_resumen_dispositivo(device_id) for device_id in ids])


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
