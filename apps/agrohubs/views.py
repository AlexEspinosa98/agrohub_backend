import json

from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agrohubs import services
from apps.agrohubs.catalogos import DEPARTAMENTOS, GRUPOS_ETNICOS
from apps.agrohubs.models import AgroHub
from apps.agrohubs.serializers import AgroHubCreateSerializer, AgroHubUpdateSerializer
from apps.asistencia_eventos.catalogos import COMUNIDADES_INDIGENAS_SUGERIDAS
from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.permissions import IsAdminOrInvestigadorRole, IsAuthenticatedWithRole

_AUTH = [TokenHeaderAuthentication]
# Administran el registro: admin, superadmin e investigador.
_ADMIN_ONLY = [IsAuthenticatedWithRole, IsAdminOrInvestigadorRole]
# El geovisor es abierto: puntos y detalle no piden token.
_PUBLICO = [AllowAny]


def _nombre(usuario):
    return (getattr(usuario, "name", None) or getattr(usuario, "email", None)) if usuario else None


def _url_video(agrohub):
    return default_storage.url(agrohub.video) if agrohub.video else None


def _dispositivo(a: AgroHub):
    if not a.dispositivo:
        return None
    try:
        nombre = services.nombres_dispositivos([a.dispositivo]).get(a.dispositivo)
    except Exception:  # noqa: BLE001 — si la base de IoT no responde, la ficha igual se entrega
        nombre = None
    return {"device_id": a.dispositivo, "nombre": nombre}


def _detalle(a: AgroHub, admin=False) -> dict:
    data = {
        "id": a.id,
        "numero": a.numero,
        "nombre": a.nombre,
        "familias": a.familias,
        "lugar": {
            "departamento": a.departamento,
            "municipio": a.municipio,
            "es_cabecera_municipal": a.es_cabecera_municipal,
            "vereda": a.vereda,
        },
        "asociaciones": a.asociaciones,
        "grupo_etnico": a.grupo_etnico,
        "comunidad": a.comunidad,
        "cultivos": a.cultivos,
        "coordenadas": {"latitud": float(a.latitud), "longitud": float(a.longitud)},
        "video": _url_video(a),
        "dispositivo": _dispositivo(a),
    }
    if admin:
        data.update(
            tipologia=a.tipologia,
            responsable=a.responsable,
            celular=a.celular,
            tipo_fuente=a.tipo_fuente,
            punto_captacion=a.punto_captacion,
            creado_por=_nombre(a.creado_por),
            creado_por_id=a.creado_por_id,
            editado_por=_nombre(a.editado_por),
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
    return data


def _obtener(agrohub_id: int) -> AgroHub:
    agrohub = AgroHub.objects.select_related("creado_por", "editado_por").filter(id=agrohub_id).first()
    if not agrohub:
        raise NotFound("AgroHub no encontrado")
    return agrohub


def _ok(message, data, code=status.HTTP_200_OK):
    return Response({"status": code, "message": message, "data": data}, status=code)


def _validar_dispositivo(device_id, excluir_id=None):
    """El gateway debe existir (activo) y no estar asociado a otro AgroHub."""
    if not device_id:
        return
    device_id = device_id.strip()
    if not services.dispositivo_activo(device_id):
        raise ValidationError({"dispositivo": f"No existe un dispositivo activo con id '{device_id}'."})
    ocupado = AgroHub.objects.filter(dispositivo=device_id)
    if excluir_id:
        ocupado = ocupado.exclude(id=excluir_id)
    otro = ocupado.first()
    if otro:
        raise ValidationError({"dispositivo": f"El dispositivo '{device_id}' ya está asociado al AgroHub '{otro.numero}'."})


def _validar_numero_unico(numero, excluir_id=None):
    if numero and services.numero_en_uso(numero, excluir_id):
        raise ValidationError({"numero": f"Ya existe un AgroHub con el número '{numero}'."})


@api_view(["GET"])
@authentication_classes([])
@permission_classes(_PUBLICO)
def puntos(request):
    data = [
        {
            "id": a.id,
            "numero": a.numero,
            "nombre": a.nombre,
            "latitud": float(a.latitud),
            "longitud": float(a.longitud),
            "municipio": a.municipio,
            "departamento": a.departamento,
            "tiene_dispositivo": bool(a.dispositivo),
        }
        for a in services.filtrar_puntos(request.query_params)
    ]
    return _ok("puntos", data)


def _listar(request):
    qs = AgroHub.objects.select_related("creado_por", "editado_por")
    q = (request.query_params.get("q") or "").strip()
    if q:
        # familias es JSON: se busca en Python (son pocas fichas) y se une con el resto.
        ids_familia = [
            a.id for a in AgroHub.objects.only("id", "familias") if any(q.lower() in f.lower() for f in a.familias)
        ]
        qs = qs.filter(
            Q(numero__icontains=q) | Q(nombre__icontains=q) | Q(municipio__icontains=q) | Q(departamento__icontains=q)
            | Q(vereda__icontains=q) | Q(id__in=ids_familia)
        )
    try:
        page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        page = int(request.query_params.get("page", 1))
    except ValueError as exc:
        raise ParseError("page y page_size deben ser enteros") from exc
    paginador = Paginator(qs.order_by("numero"), page_size)
    try:
        pagina = paginador.page(page)
    except EmptyPage:
        pagina = paginador.page(paginador.num_pages)
    return _ok(
        "agrohubs",
        {
            "total": paginador.count,
            "page": pagina.number,
            "page_size": page_size,
            "total_pages": paginador.num_pages,
            "results": [_detalle(a, admin=True) for a in pagina.object_list],
        },
    )


def _crear(request):
    if "data" in request.data:
        try:
            payload = json.loads(request.data["data"])
        except (TypeError, ValueError) as exc:
            raise ParseError("El campo 'data' debe ser un JSON válido") from exc
    else:
        payload = request.data
    serializer = AgroHubCreateSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    _validar_numero_unico(serializer.validated_data["numero"])
    _validar_dispositivo(serializer.validated_data.get("dispositivo"))
    agrohub = services.crear(
        serializer.validated_data, creado_por=request.user, video=request.FILES.get("video")
    )
    return _ok("agrohub creado", _detalle(agrohub, admin=True), status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ADMIN_ONLY)
def agrohubs_list_create(request):
    if request.method == "POST":
        return _crear(request)
    return _listar(request)


def _actualizar(request, agrohub_id):
    agrohub = _obtener(agrohub_id)
    serializer = AgroHubUpdateSerializer(data=request.data, context={"agrohub": agrohub})
    serializer.is_valid(raise_exception=True)
    _validar_numero_unico(serializer.validated_data.get("numero"), excluir_id=agrohub.id)
    _validar_dispositivo(serializer.validated_data.get("dispositivo"), excluir_id=agrohub.id)
    agrohub = services.actualizar(agrohub, serializer.validated_data, editado_por=request.user)
    return _ok("agrohub actualizado", _detalle(agrohub, admin=True))


def _eliminar(request, agrohub_id):
    services.eliminar(_obtener(agrohub_id))
    return Response(status=status.HTTP_204_NO_CONTENT)


class AgroHubDetailView(APIView):
    """Una URL, permisos distintos por método: GET es público (geovisor); PUT/DELETE exigen token
    y rol admin/superadmin."""

    authentication_classes = _AUTH

    def get_permissions(self):
        clases = _PUBLICO if self.request.method == "GET" else _ADMIN_ONLY
        return [c() for c in clases]

    def get(self, request, agrohub_id):
        return _ok("agrohub", _detalle(_obtener(agrohub_id)))

    def put(self, request, agrohub_id):
        return _actualizar(request, agrohub_id)

    def delete(self, request, agrohub_id):
        return _eliminar(request, agrohub_id)


agrohub_detail = AgroHubDetailView.as_view()


@api_view(["GET"])
@authentication_classes([])
@permission_classes(_PUBLICO)
def agrohub_datos(request, agrohub_id: int):
    """Datos abiertos del lugar: última lectura ambiental y de suelo del gateway asociado."""
    agrohub = _obtener(agrohub_id)
    if not agrohub.dispositivo:
        raise NotFound("Este AgroHub no tiene un dispositivo IoT asociado")
    data = {"agrohub_id": agrohub.id, "numero": agrohub.numero, **services.lecturas_publicas(agrohub.dispositivo)}
    return _ok("datos", data)


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ADMIN_ONLY)
def dispositivos_disponibles(request):
    """Gateways activos sin AgroHub asociado: alimenta el selector del formulario del admin."""
    data = [{"device_id": d.device_id, "nombre": d.nombre} for d in services.dispositivos_disponibles()]
    return _ok("dispositivos disponibles", data)


@api_view(["POST", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_ADMIN_ONLY)
def agrohub_video(request, agrohub_id: int):
    agrohub = _obtener(agrohub_id)
    if request.method == "DELETE":
        services.quitar_video(agrohub)
        return Response(status=status.HTTP_204_NO_CONTENT)
    upload = request.FILES.get("video")
    if not upload:
        raise ParseError("Falta el archivo de video (campo 'video')")
    services.guardar_video(agrohub, upload)
    agrohub.editado_por = request.user
    agrohub.save(update_fields=["editado_por", "updated_at"])
    return _ok("video guardado", {"id": agrohub.id, "video": _url_video(agrohub)})


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ADMIN_ONLY)
def catalogos(request):
    return _ok(
        "catalogos",
        {
            "departamentos": DEPARTAMENTOS,
            "grupos_etnicos": GRUPOS_ETNICOS,
            "comunidades": COMUNIDADES_INDIGENAS_SUGERIDAS,
            "asociaciones": services.valores_usados("asociaciones"),
            "cultivos": services.valores_usados("cultivos"),
        },
    )
