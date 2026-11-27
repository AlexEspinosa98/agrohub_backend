"""Endpoints de Huertas abiertas. Contrato completo: docs/API_HUERTAS_ABIERTAS.md.

Todas las respuestas usan el sobre del resto del backend: {status, message, data}.
`<ref>` acepta el id numérico del AgroHub o su número ("AH-001" / "ah-001", como el slug de la web).
"""
import hashlib
import re
import uuid
from datetime import datetime, time, timezone as dt_timezone

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.agrohubs.models import AgroHub
from apps.huertas import ciclo, lecturas, permisos, plan, recomendaciones, seguimiento
from apps.huertas.models import Cama, Cuidador, Cultivo, CultivoCambio, CultivoEtapa, Movimiento, Reporte
from apps.huertas.serializers import (
    CalibrarSerializer,
    CamaConfigSerializer,
    CamaPlanSerializer,
    CuidadorSerializer,
    CultivoSerializer,
    IntercambiarSerializer,
    ModeracionSerializer,
    RegarSerializer,
    ReporteSerializer,
)
from apps.user_activity.authentication import TokenHeaderAuthentication

_AUTH = [TokenHeaderAuthentication]
_ABIERTO = [AllowAny]
TAG = "Huertas abiertas"
_REF = OpenApiParameter("ref", str, OpenApiParameter.PATH, description="Id del AgroHub o su número (AH-002 / ah-002).")
_ZONA = OpenApiParameter("zona", str, OpenApiParameter.PATH, description="Nombre público de la cama (A, B, C…).")


def _doc(resumen, descripcion="", request=None, parametros=(), metodos=None):
    return extend_schema(
        tags=[TAG], summary=resumen, description=descripcion, request=request,
        responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT}, parameters=list(parametros), methods=metodos,
    )  # cada vista revisa permisos con apps.huertas.permisos según el AgroHub


class LecturaPublicaThrottle(AnonRateThrottle):
    rate = "120/min"


class ReporteIPThrottle(SimpleRateThrottle):
    """Reportes abiertos: por IP (una comunidad puede compartir conexión, así que es holgado)."""

    scope = "huertas_reporte_ip"
    rate = "12/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ReporteDispositivoThrottle(SimpleRateThrottle):
    """Y por dispositivo: la web manda un identificador propio en `X-Dispositivo`."""

    scope = "huertas_reporte_dispositivo"
    rate = "4/hour"

    def get_cache_key(self, request, view):
        disp = (request.META.get("HTTP_X_DISPOSITIVO") or "").strip()[:64]
        if request.method != "POST" or not disp:
            return None
        return self.cache_format % {"scope": self.scope, "ident": hashlib.sha256(disp.encode()).hexdigest()[:24]}


def _ok(message, data, code=status.HTTP_200_OK):
    return Response({"status": code, "message": message, "data": data}, status=code)


def _agrohub(ref):
    ref = str(ref).strip()
    qs = AgroHub.objects.all()
    a = qs.filter(id=int(ref)).first() if ref.isdigit() else qs.filter(numero__iexact=ref).first()
    if not a:
        raise NotFound("AgroHub no encontrado")
    return a


def _cama(agrohub, zona):
    c = Cama.objects.filter(agrohub=agrohub, zona__iexact=zona).select_related("cultivo").first()
    if not c:
        raise NotFound(f"La huerta no tiene una cama «{zona}».")
    return c


def _instante(valor, nombre):
    if not valor:
        return None
    if valor.isdigit():  # milisegundos, como `t` de las lecturas
        return datetime.fromtimestamp(int(valor) / 1000, tz=dt_timezone.utc)
    dt = parse_datetime(valor)
    if dt is None:
        d = parse_date(valor)
        if d is None:
            raise ValidationError({nombre: "Usa una fecha (AAAA-MM-DD), fecha y hora ISO o milisegundos."})
        dt = datetime.combine(d, time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _url(ruta):
    """URL completa del archivo: el front vive en otro dominio y una ruta relativa
    (/api/agrohub/media/...) le da 404."""
    if not ruta:
        return None
    url = default_storage.url(ruta)
    if url.startswith("/"):
        from django.conf import settings

        url = f"{settings.PUBLIC_BACKEND_ORIGIN}{url}"
    return url


# ======================================================================== HB01 · Biblioteca


def _invalidar_biblioteca():
    cache.delete("huertas:cultivos")


@_doc("Biblioteca de cultivos (pública)", "Las fichas activas con umbrales, etapas, vecinas y fuentes. Caché de 5 min.", metodos=["GET"])
@_doc("Crear un cultivo (equipo)", "Solo admin, superadmin o investigador. Queda en el registro de cambios.", request=CultivoSerializer, metodos=["POST"])
@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def cultivos(request):
    if request.method == "GET":
        datos = cache.get("huertas:cultivos")
        if datos is None:
            datos = [c.ficha_dict() for c in Cultivo.objects.filter(activo=True).prefetch_related("etapas")]
            cache.set("huertas:cultivos", datos, 300)
        resp = _ok("cultivos", datos)
        resp["Cache-Control"] = "public, max-age=300"
        return resp

    permisos.exigir_equipo(request.user)
    s = CultivoSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    if Cultivo.objects.filter(id=d["id"]).exists():
        raise ValidationError({"id": f"Ya existe el cultivo «{d['id']}»."})
    with transaction.atomic():
        etapas = d.pop("etapas")
        c = Cultivo.objects.create(**d, editado_por=request.user)
        CultivoEtapa.objects.bulk_create(
            [CultivoEtapa(cultivo=c, orden=i, **e) for i, e in enumerate(etapas)]
        )
        CultivoCambio.objects.create(cultivo=c, usuario=request.user, cambios={"creado": True})
    _invalidar_biblioteca()
    return _ok("cultivo creado", c.ficha_dict(), status.HTTP_201_CREATED)


@_doc("Ficha de un cultivo (pública)", metodos=["GET"])
@_doc("Editar un cultivo (equipo)", "Cambio parcial; cada valor modificado queda en /cultivos/<id>/cambios.", request=CultivoSerializer, metodos=["PUT", "PATCH"])
@api_view(["GET", "PUT", "PATCH"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def cultivo_detalle(request, cultivo_id):
    c = Cultivo.objects.prefetch_related("etapas").filter(id=cultivo_id).first()
    if not c or (not c.activo and request.method == "GET" and not permisos.es_equipo(request.user)):
        raise NotFound("Cultivo no encontrado")
    if request.method == "GET":
        return _ok("cultivo", c.ficha_dict())

    permisos.exigir_equipo(request.user)
    s = CultivoSerializer(instance=c, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    d = dict(s.validated_data)
    d.pop("id", None)
    antes = c.ficha_dict()
    cambios = {}
    with transaction.atomic():
        etapas = d.pop("etapas", None)
        for campo, valor in d.items():
            if antes.get(campo) != valor:
                cambios[campo] = [antes.get(campo), valor]
                setattr(c, campo, valor)
        if etapas is not None:
            nuevas = [{"tipo": e["tipo"], "nombre": e["nombre"], "desde": e["desde"]} for e in etapas]
            if nuevas != antes["etapas"]:
                cambios["etapas"] = [antes["etapas"], nuevas]
                c.etapas.all().delete()
                CultivoEtapa.objects.bulk_create([CultivoEtapa(cultivo=c, orden=i, **e) for i, e in enumerate(nuevas)])
        if cambios:
            c.editado_por = request.user
            c.save()
            CultivoCambio.objects.create(cultivo=c, usuario=request.user, cambios=cambios)
    _invalidar_biblioteca()
    c = Cultivo.objects.prefetch_related("etapas").get(pk=c.pk)
    return _ok("cultivo actualizado" if cambios else "sin cambios", {**c.ficha_dict(), "cambios": cambios})


@_doc("Quién cambió qué en una ficha (equipo)")
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def cultivo_cambios(request, cultivo_id):
    permisos.exigir_equipo(request.user)
    datos = [
        {"usuario_id": x.usuario_id, "usuario": getattr(x.usuario, "name", None), "cambios": x.cambios, "creado_en": x.creado_en}
        for x in CultivoCambio.objects.filter(cultivo_id=cultivo_id).select_related("usuario")[:100]
    ]
    return _ok("cambios", datos)


# ======================================================================== HB07 · Permisos


@_doc("Qué puede hacer la sesión actual en esta huerta", "Sin token responde los permisos de cualquier persona (mirar y reportar).", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def agrohub_permisos(request, ref):
    a = _agrohub(ref)
    return _ok("permisos", {"agrohub_id": a.id, "numero": a.numero, **permisos.permisos(request.user, a)})


@_doc("Cuidadores de la huerta (equipo)", "GET lista; POST asigna a un usuario (usuario_id).", request=CuidadorSerializer, parametros=[_REF])
@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def cuidadores(request, ref):
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    if request.method == "POST":
        from apps.user_activity.models import User

        s = CuidadorSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if s.validated_data.get("usuario_id"):
            u = User.objects.filter(id=s.validated_data["usuario_id"]).first()
        else:
            from apps.user_activity.views import _find_user_by_login

            u = _find_user_by_login(s.validated_data["identificador"].strip())
        if not u:
            raise ValidationError({"identificador": "No hay una cuenta con ese teléfono, cédula o correo."})
        Cuidador.objects.get_or_create(agrohub=a, usuario=u, defaults={"asignado_por": request.user})
    datos = [
        {"usuario_id": c.usuario_id, "nombre": c.usuario.name, "telefono": c.usuario.phone, "asignado_en": c.creado_en}
        for c in Cuidador.objects.filter(agrohub=a).select_related("usuario")
    ]
    return _ok("cuidadores", datos, status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK)


@_doc("Quitar un cuidador (equipo)", parametros=[_REF])
@api_view(["DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def cuidador_quitar(request, ref, usuario_id):
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    borrados, _ = Cuidador.objects.filter(agrohub=a, usuario_id=usuario_id).delete()
    if not borrados:
        raise NotFound("Esa persona no cuida esta huerta.")
    return _ok("cuidador quitado", None)


# ======================================================================== Camas (config técnica)


def _validar_cama_tecnica(agrohub, datos, excluir=None):
    zona_gw, valvula = datos.get("gateway_zona"), datos.get("valvula")
    if bool(zona_gw) != bool(valvula):
        raise ValidationError({"valvula": "La zona del gateway y la válvula van juntas (o ninguna)."})
    if zona_gw:
        repetida = Cama.objects.filter(agrohub=agrohub, gateway_zona=zona_gw, valvula=valvula)
        if excluir:
            repetida = repetida.exclude(pk=excluir.pk)
        if repetida.exists():
            raise ValidationError({"valvula": f"La válvula {valvula} de {zona_gw} ya gobierna otra cama."})


@_doc("Camas de la huerta con su configuración técnica (equipo)", "POST crea una cama: zona (A, B…), gateway_zona (z1…), valvula (RO1/RO2) y sensor (dev_eui).", request=CamaConfigSerializer, parametros=[_REF])
@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def camas(request, ref):
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    if request.method == "POST":
        s = CamaConfigSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if not d.get("zona"):
            raise ValidationError({"zona": "Ponle un nombre a la cama (A, B, C…)."})
        d["zona"] = d["zona"].upper()
        if Cama.objects.filter(agrohub=a, zona=d["zona"]).exists():
            raise ValidationError({"zona": f"Ya hay una cama «{d['zona']}»."})
        _validar_cama_tecnica(a, d)
        d.setdefault("orden", Cama.objects.filter(agrohub=a).count())
        Cama.objects.create(agrohub=a, **d)
    return _ok("camas", plan.plan_dict(a, equipo=True), status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK)


@_doc("Editar o borrar la configuración técnica de una cama (equipo)", request=CamaConfigSerializer, parametros=[_REF, _ZONA])
@api_view(["PUT", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def cama_config(request, ref, zona):
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    c = _cama(a, zona)
    if request.method == "DELETE":
        if c.cultivo_id:
            raise ValidationError({"zona": "La cama tiene un cultivo: déjala en descanso antes de borrarla."})
        c.delete()
        return _ok("cama borrada", plan.plan_dict(a, equipo=True))
    s = CamaConfigSerializer(data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    if "zona" in d:
        d["zona"] = d["zona"].upper()
        if Cama.objects.filter(agrohub=a, zona=d["zona"]).exclude(pk=c.pk).exists():
            raise ValidationError({"zona": f"Ya hay una cama «{d['zona']}»."})
    _validar_cama_tecnica(a, {"gateway_zona": d.get("gateway_zona", c.gateway_zona), "valvula": d.get("valvula", c.valvula)}, excluir=c)
    for k, v in d.items():
        setattr(c, k, v)
    if "gateway_zona" in d or "valvula" in d:
        c.umbral_abrir = c.umbral_cerrar = c.envio_resultado = None
    if d:
        c.origen = "equipo"
    c.save()
    return _ok("cama actualizada", plan.plan_dict(a, equipo=True))


@_doc("Sondas de tierra y válvulas que reporta el gateway (equipo)", "Para armar las camas: qué dev_eui reportó en los últimos 7 días y a qué cama está asignado.", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def sensores(request, ref):
    """Sondas de tierra y zonas/válvulas que reporta el gateway, para armar las camas."""
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    if not a.dispositivo:
        return _ok("sin gateway", {"dispositivo": None, "sensores": [], "zonas": {}})
    asignados = dict(Cama.objects.filter(agrohub=a).exclude(sensor=None).values_list("sensor", "zona"))
    datos = lecturas.sensores_del_gateway(a.dispositivo)
    for s in datos:
        s["cama"] = asignados.get(s["sensor"])
    return _ok("sensores", {"dispositivo": a.dispositivo, "sensores": datos, "zonas": lecturas.zonas_del_gateway(a.dispositivo)})


# ======================================================================== HB02 · Plan de siembra


def _respuesta_plan(request, a, mensaje, extra=None, code=status.HTTP_200_OK):
    data = plan.plan_dict(a, equipo=permisos.es_equipo(request.user))
    if extra:
        data.update(extra)
    return _ok(mensaje, data, code)


@_doc("Plan de siembra (público)", "Cada cama con su cultivo, edad, etapa, umbral calculado, historial y estado del último envío al gateway.", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def agrohub_plan(request, ref):
    a = _agrohub(ref)
    return _respuesta_plan(request, a, "plan")


@_doc("Cambiar el plan de una cama (cuidador o equipo)", "Sembrar (cultivo_id + sembrado_el), dejar en descanso (cultivo_id: null), marcar cosecha o calibrar (ajuste ±6). Recalcula el umbral y, si está activado, lo envía al gateway.", request=CamaPlanSerializer, parametros=[_REF, _ZONA])
@api_view(["PUT"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def plan_cama(request, ref, zona):
    a = _agrohub(ref)
    permisos.exigir_cuidar(request.user, a)
    c = _cama(a, zona)
    s = CamaPlanSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    c, movs = plan.cambiar_cama(a, c, s.validated_data, request.user)
    envio = plan.recalcular_y_enviar(a, [c]) if movs else None
    return _respuesta_plan(request, a, "plan actualizado" if movs else "sin cambios", {
        "envio": envio, "movimientos_nuevos": [_mov(m) for m in movs],
    })


@_doc("Intercambiar los cultivos de dos camas (cuidador o equipo)", "Cada cama conserva su calibración.", request=IntercambiarSerializer, parametros=[_REF])
@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def plan_intercambiar(request, ref):
    a = _agrohub(ref)
    permisos.exigir_cuidar(request.user, a)
    s = IntercambiarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    za, zb = (z.upper() for z in s.validated_data["zonas"])
    camas_, movs = plan.intercambiar(a, za, zb, request.user)
    envio = plan.recalcular_y_enviar(a, camas_)
    return _respuesta_plan(request, a, "camas intercambiadas", {"envio": envio, "movimientos_nuevos": [_mov(m) for m in movs]})


@_doc("Reenviar todos los umbrales al gateway (equipo)", parametros=[_REF])
@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def plan_reenviar(request, ref):
    """Vuelve a mandar al gateway el umbral de todas las camas (equipo técnico)."""
    a = _agrohub(ref)
    permisos.exigir_equipo(request.user)
    envio = plan.recalcular_y_enviar(a, forzar=True)
    return _respuesta_plan(request, a, "umbrales reenviados", {"envio": envio})


# ======================================================================== Riego desde la huerta


@_doc("Abrir o cerrar el riego de una cama (cuidador o equipo)", "Orden manual a la válvula, sin reintento. resultado: enviada (hubo eco) o sin_eco.", request=RegarSerializer, parametros=[_REF, _ZONA])
@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def cama_regar(request, ref, zona):
    """Abrir o cerrar la válvula de una cama (HU-14 de riego-iot, para quien cuida la huerta).
    Sin reintento automático: es equipo real en campo. `enviada` = el gateway hizo eco;
    `sin_eco` = no respondió en 5 s (la orden pudo llegar o no)."""
    a = _agrohub(ref)
    permisos.exigir_cuidar(request.user, a)
    c = _cama(a, zona)
    s = RegarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    if not (a.dispositivo and c.conectada):
        raise ValidationError({"zona": "Esta cama no está conectada a una válvula del gateway."})
    from apps.riego_iot import control_mqtt

    accion = s.validated_data["accion"]
    try:
        r = control_mqtt.enviar_comando_valvula(a.dispositivo, c.gateway_zona, c.valvula, accion)
    except control_mqtt.MqttNoDisponible as exc:
        return _ok(str(exc), {"resultado": "error"}, status.HTTP_503_SERVICE_UNAVAILABLE)
    if r["resultado"] == "invalida":
        raise ValidationError({"comando": r["errores"]})
    nombre = c.cultivo.nombre.lower() if c.cultivo_id else "en descanso"
    Movimiento.objects.create(
        agrohub=a, cama=c, tipo="riego", usuario=request.user,
        texto=f"Se {'abrió' if accion == 'abrir' else 'cerró'} el riego de la cama {c.zona} ({nombre}) a mano",
        datos={"accion": accion, "resultado": r["resultado"]},
    )
    return _ok("orden enviada" if r["resultado"] == "enviada" else "el gateway no confirmó la orden", {
        "zona": c.zona, "accion": accion, "resultado": r["resultado"],
    })


# ======================================================================== HB03 · Lecturas


@_doc("Lecturas abiertas por cama (público)", "Agregadas cada 30 min con la forma de `Lectura` del frontend. Ventana máxima 8 días (por defecto 2). Sin datos no se rellena: enLinea=false y valores null.", parametros=[_REF, OpenApiParameter("desde", str, description="ISO, AAAA-MM-DD o milisegundos"), OpenApiParameter("hasta", str, description="ISO, AAAA-MM-DD o milisegundos")])
@api_view(["GET"])
@authentication_classes([])
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def agrohub_lecturas(request, ref):
    a = _agrohub(ref)
    desde = _instante(request.query_params.get("desde"), "desde")
    hasta = _instante(request.query_params.get("hasta"), "hasta")
    camas_ = list(Cama.objects.filter(agrohub=a))
    try:
        datos = lecturas.lecturas_de(a, camas_, desde, hasta)
    except ValueError as exc:
        raise ValidationError({"desde": str(exc)}) from exc
    resp = _ok("lecturas" if datos["lecturas"] else "sin datos", {"agrohub_id": a.id, "numero": a.numero, **datos})
    resp["Cache-Control"] = "public, max-age=60"
    return resp


# ======================================================================== HB04 · Reportes


_ENLACE = re.compile(r"(https?://|www\.|\.com\b|\.co\b|@\w)", re.I)


def _reporte_dict(r, ver_moderacion=False):
    d = {
        "id": r.id,
        "fecha": int(r.creado_en.timestamp() * 1000),
        "creado_en": r.creado_en,
        "autor": seguimiento.autor_publico(r),
        "zona": r.cama.zona if r.cama_id else None,
        "matas": r.matas,
        "tierra": r.tierra,
        "plaga": r.plaga,
        "riegoMano": r.riego_mano,
        "cosecha": r.cosecha,
        "nota": r.nota,
        "foto": _url(r.foto),
        "sensor": r.sensor,
    }
    if ver_moderacion:
        d["moderacion"] = r.moderacion
    return d


def _guardar_foto(agrohub, archivo):
    if archivo.size > 5 * 1024 * 1024:
        raise ValidationError({"foto": "La foto puede pesar hasta 5 MB."})
    from PIL import Image, ImageOps

    try:
        img = Image.open(archivo)
        img.verify()
        archivo.seek(0)
        img = ImageOps.exif_transpose(Image.open(archivo)).convert("RGB")  # sin metadatos (ubicación)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError({"foto": "El archivo no es una imagen válida."}) from exc
    img.thumbnail((1600, 1600))
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, "JPEG", quality=82)
    ruta = f"huertas/reportes/{agrohub.id}/{uuid.uuid4().hex}.jpg"
    return default_storage.save(ruta, ContentFile(buf.getvalue()))


@_doc("Reportes de la comunidad (público)", "Sin datos personales. Quien cuida puede pedir ?moderacion=todos.", parametros=[_REF, OpenApiParameter("limite", int), OpenApiParameter("moderacion", str)], metodos=["GET"])
@_doc("Mandar un reporte (abierto)", "JSON o multipart (con `foto`, hasta 5 MB). Límite: 12 por hora por IP y 4 por hora por dispositivo (header X-Dispositivo). Una nota con enlaces queda pendiente de revisión. El backend anota qué decía el sensor de la cama.", request=ReporteSerializer, parametros=[_REF], metodos=["POST"])
@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle, ReporteIPThrottle, ReporteDispositivoThrottle])
def agrohub_reportes(request, ref):
    a = _agrohub(ref)
    cuida = permisos.puede_cuidar(request.user, a)
    if request.method == "GET":
        qs = Reporte.objects.filter(agrohub=a).select_related("cama")
        if not (cuida and request.query_params.get("moderacion") == "todos"):
            qs = qs.filter(moderacion="visible")
        try:
            limite = max(1, min(100, int(request.query_params.get("limite", 30))))
        except ValueError:
            limite = 30
        return _ok("reportes", [_reporte_dict(r, cuida) for r in qs[:limite]])

    s = ReporteSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    zona = (d.pop("zona", None) or "").strip()
    cama = _cama(a, zona) if zona else None
    usuario = request.user if permisos.autenticado(request.user) else None
    if d["autoria"] == "nombre" and not d["autor_nombre"]:
        d["autor_nombre"] = getattr(usuario, "name", "") or ""
    # Lo que decía el sensor de esa cama en ese momento: la base de la calibración (HB08).
    sensor = hum = None
    if cama and cama.cultivo_id:
        hum = lecturas.humedad_actual(a, cama)
        if hum is not None:
            ficha = plan.fichas_por_id([cama.cultivo_id]).get(cama.cultivo_id)
            u = plan._umbral(cama, ficha)
            sensor = ciclo.estado_tierra(hum, u["abrir"], u["cerrar"], lecturas.valvula_abierta(a, cama))
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0].strip()
    moderacion = "pendiente" if (_ENLACE.search(d["nota"]) or _ENLACE.search(d["autor_nombre"])) else "visible"
    r = Reporte(
        agrohub=a, cama=cama, usuario=usuario, sensor=sensor, sensor_humedad=hum, moderacion=moderacion,
        origen_hash=hashlib.sha256(f"{ip}|{a.id}".encode()).hexdigest()[:32], **d,
    )
    foto = request.FILES.get("foto")
    if foto:
        r.foto = _guardar_foto(a, foto)
    r.save()
    mensaje = "reporte guardado" if moderacion == "visible" else "reporte guardado: se publica cuando lo revisen (trae un enlace)"
    return _ok(mensaje, _reporte_dict(r, True), status.HTTP_201_CREATED)


@_doc("Moderar un reporte (cuidador o equipo)", request=ModeracionSerializer, parametros=[_REF])
@api_view(["PUT"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def reporte_moderar(request, ref, reporte_id):
    a = _agrohub(ref)
    permisos.exigir_cuidar(request.user, a)
    r = Reporte.objects.filter(agrohub=a, id=reporte_id).select_related("cama").first()
    if not r:
        raise NotFound("Reporte no encontrado")
    s = ModeracionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    r.moderacion = s.validated_data["moderacion"]
    r.save(update_fields=["moderacion"])
    return _ok("reporte moderado", _reporte_dict(r, True))


# ======================================================================== HB05 · Bitácora


@_doc("Bitácora de la huerta", "Entradas escritas desde la huerta (POST /user-activity/logbooks con agrohub_id). Sin sesión solo las públicas.", parametros=[_REF, OpenApiParameter("desde", str), OpenApiParameter("hasta", str)])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def agrohub_bitacora(request, ref):
    from apps.user_activity.models import Logbook

    a = _agrohub(ref)
    qs = Logbook.objects.filter(agrohub=a).select_related("user").order_by("-activity_date", "-id")
    if not permisos.puede_cuidar(request.user, a):
        qs = qs.filter(publica=True)
    desde, hasta = request.query_params.get("desde"), request.query_params.get("hasta")
    if desde:
        qs = qs.filter(activity_date__gte=desde)
    if hasta:
        qs = qs.filter(activity_date__lte=hasta)
    datos = [
        {
            "id": n.id,
            "title": n.title,
            "description": n.description,
            "activity_date": n.activity_date,
            "activity_type": n.activity_type,
            "moon_phase": n.moon_phase,
            "autor": (n.user.name or "").split(" ")[0] if n.user_id else "Alguien del equipo",
            "publica": n.publica,
            "created_at": int(n.created_at.timestamp() * 1000),
        }
        for n in qs[:100]
    ]
    return _ok("bitácora", datos)


# ======================================================================== Movimientos


def _mov(m):
    return {"id": m.id, "fecha": int(m.creado_en.timestamp() * 1000), "tipo": m.tipo, "texto": m.texto, "zona": m.cama.zona if m.cama_id else None}


@_doc("Lo que ha pasado en la huerta (público)", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def agrohub_movimientos(request, ref):
    a = _agrohub(ref)
    return _ok("movimientos", [_mov(m) for m in Movimiento.objects.filter(agrohub=a).select_related("cama")[:100]])


# ======================================================================== HB08 · Recomendaciones y calibración


def _camas_con_ficha(a):
    camas_ = list(a.camas.select_related("cultivo"))
    fichas = plan.fichas_por_id([c.cultivo_id for c in camas_])
    salida = []
    for c in camas_:
        d = plan.cama_dict(c, fichas, historial=[])
        d["_ficha"] = fichas.get(c.cultivo_id)
        salida.append(d)
    return salida


@_doc("Recomendaciones por reglas (público)", "Incluye las propuestas de calibración: nunca se aplican solas.", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def agrohub_recomendaciones(request, ref):
    a = _agrohub(ref)
    reportes = list(Reporte.objects.filter(agrohub=a, moderacion="visible").select_related("cama")[:60])
    return _ok("recomendaciones", recomendaciones.recomendar(_camas_con_ficha(a), reportes))


@_doc("Aceptar una calibración (cuidador o equipo)", "Suma puntos al ajuste de la cama (tope ±6) y reenvía el umbral.", request=CalibrarSerializer, parametros=[_REF])
@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def calibracion_aceptar(request, ref):
    """Quien cuida la huerta acepta una propuesta de calibración: suma `puntos` al ajuste de la
    cama (tope ±6) y reenvía los umbrales. Nunca se aplica sola."""
    a = _agrohub(ref)
    permisos.exigir_cuidar(request.user, a)
    s = CalibrarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    c = _cama(a, s.validated_data["zona"])
    c, movs = plan.cambiar_cama(a, c, {"ajuste": c.ajuste + s.validated_data["puntos"]}, request.user)
    envio = plan.recalcular_y_enviar(a, [c]) if movs else None
    return _respuesta_plan(request, a, "calibración aplicada", {"envio": envio, "movimientos_nuevos": [_mov(m) for m in movs]})


# ======================================================================== HB06 · Seguimiento


@_doc("Último seguimiento y si hay novedades (público, no llama al modelo)", parametros=[_REF], metodos=["GET"])
@_doc("Generar el seguimiento si hay novedades", "Si la huella no cambió devuelve el guardado. Máximo uno cada 6 h por huerta y tope de gasto mensual.", parametros=[_REF], metodos=["POST"])
@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
def agrohub_seguimiento(request, ref):
    a = _agrohub(ref)
    if request.method == "GET":
        return _ok("seguimiento", seguimiento.estado(a))
    try:
        s, nuevo = seguimiento.generar(a)
    except seguimiento.SeguimientoError as exc:
        guardado = seguimiento.ultimo(a)
        return Response({
            "status": exc.status, "message": exc.mensaje,
            "data": {"seguimiento": seguimiento.a_dict(guardado) if guardado else None},
        }, status=exc.status)
    return _ok("seguimiento nuevo" if nuevo else "sin novedades: se devuelve el guardado", {
        "seguimiento": seguimiento.a_dict(s), "nuevo": nuevo, "hay_novedades": False,
    }, status.HTTP_201_CREATED if nuevo else status.HTTP_200_OK)


# ======================================================================== Todas las huertas


def _agrohub_publico(a):
    return {
        "id": a.id, "numero": a.numero, "slug": a.numero.lower(), "nombre": a.nombre,
        "municipio": a.municipio, "vereda": a.vereda, "comunidad": a.comunidad,
        "posicion": [float(a.latitud), float(a.longitud)], "con_sensores": bool(a.dispositivo),
    }


@_doc("Todas las huertas con su plan (público)", "Para el mapa y el boletín: cada AgroHub con sus camas, en una sola llamada.")
@api_view(["GET"])
@authentication_classes([])
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def huertas_todas(request):
    agrohubs = list(AgroHub.objects.prefetch_related("camas__historial").order_by("numero"))
    fichas = plan.fichas_por_id()
    datos = [
        {
            **_agrohub_publico(a),
            "camas": [plan.cama_dict(c, fichas, list(c.historial.all()[:4])) for c in a.camas.all()],
        }
        for a in agrohubs
    ]
    resp = _ok("huertas", datos)
    resp["Cache-Control"] = "public, max-age=60"
    return resp


# ======================================================================== Resumen de la huerta


@_doc("Todo lo de una huerta en una llamada (público)", "Agrohub, permisos, plan, reportes, movimientos, recomendaciones y seguimiento. Las lecturas van aparte.", parametros=[_REF])
@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_ABIERTO)
@throttle_classes([LecturaPublicaThrottle])
def agrohub_huerta(request, ref):
    """Todo lo que la página de una huerta necesita para pintarse en una sola llamada (sin las
    lecturas, que se piden aparte por ventana de tiempo)."""
    a = _agrohub(ref)
    equipo = permisos.es_equipo(request.user)
    reportes = list(Reporte.objects.filter(agrohub=a, moderacion="visible").select_related("cama")[:30])
    est = seguimiento.estado(a)
    return _ok("huerta", {
        "agrohub": _agrohub_publico(a),
        "permisos": permisos.permisos(request.user, a),
        "plan": plan.plan_dict(a, equipo=equipo),
        "reportes": [_reporte_dict(r) for r in reportes],
        "movimientos": [_mov(m) for m in Movimiento.objects.filter(agrohub=a).select_related("cama")[:30]],
        "recomendaciones": recomendaciones.recomendar(_camas_con_ficha(a), reportes),
        "seguimiento": est,
    })
