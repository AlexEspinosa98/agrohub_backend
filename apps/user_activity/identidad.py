"""API interna de la identidad única de AgroHub.

La usa el backend de la red social (AgroHub Social) para que una persona tenga UNA cuenta: el mismo
usuario y la misma contraseña en el panel, la bitácora, Huertas abiertas y la red social. La red
social sigue con sus perfiles, comunidades y su propio JWT; lo que delega aquí es quién es la
persona y si su contraseña es correcta.

No es para navegadores: exige el header `X-Identidad-Clave` igual a `IDENTIDAD_CLAVE` del
servidor (secreto compartido entre los dos backends). Sin esa variable, todo responde 404.

    POST /user-activity/identidad/verificar            {identificador, password} → 200 persona | 401
    POST /user-activity/identidad/registrar            {email, password, name}  → 201 creada | 200 ya era suya | 409
    POST /user-activity/identidad/usuarios/<id>/contrasena  {password}           → 200
    GET  /user-activity/identidad/usuarios/<id>                                  → 200 persona
    POST /user-activity/identidad/usuarios/<id>/sesion                           → 200 sesión del panel
    POST /user-activity/identidad/canjear              {ticket}                  → 200 persona | 401

Y una ruta para el propio panel (con `Authorization: Token <sesión del panel>`, sin la clave):

    POST /user-activity/identidad/ticket                                         → 200 {ticket}

Con esas tres, quien ya inició sesión en un lado entra al otro sin volver a escribir la
contraseña: el panel firma un ticket de 2 minutos que la red social canjea aquí; y la red social
pide una sesión del panel para la persona que ya autenticó con su propio JWT.
"""
import hmac

from django.core import signing

from django.conf import settings
from django.db import IntegrityError
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.contrasenas import hash_password, verificar_usuario
from apps.user_activity.models import User


class ClaveIdentidad(BasePermission):
    def has_permission(self, request, view):
        esperada = getattr(settings, "IDENTIDAD_CLAVE", "") or ""
        recibida = request.META.get("HTTP_X_IDENTIDAD_CLAVE", "") or ""
        if not esperada:
            raise NotFound()
        return bool(recibida) and hmac.compare_digest(esperada, recibida)


def persona(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "identification": u.identification,
        "role": u.role or "user",
        # La red social lo usa para unir a la persona a la comunidad de su municipio al entrar
        "municipio": (u.association.municipality if u.association_id and u.association else None),
    }


class VerificarSerializer(serializers.Serializer):
    identificador = serializers.CharField(max_length=255)
    password = serializers.CharField(trim_whitespace=False, max_length=512)


class RegistrarSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(trim_whitespace=False, max_length=512)
    name = serializers.CharField(max_length=255)


class ContrasenaSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=512)


_DECORADORES = dict(auth=[], perms=[ClaveIdentidad])


@api_view(["POST"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def verificar(request):
    from apps.user_activity.views import _find_user_by_login

    s = VerificarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    u = _find_user_by_login(s.validated_data["identificador"])
    if not u or not verificar_usuario(u, s.validated_data["password"]):
        return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"status": 200, "message": "ok", "data": persona(u)})


@api_view(["POST"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def registrar(request):
    s = RegistrarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    email = s.validated_data["email"].strip().lower()
    existente = User.objects.filter(email__iexact=email).first()
    if existente:
        # Misma persona con la misma contraseña: se enlaza. Otra contraseña: que entre con la suya.
        if verificar_usuario(existente, s.validated_data["password"]):
            return Response({"status": 200, "message": "ya existía", "data": persona(existente)})
        return Response(
            {"detail": "Ya existe una cuenta AgroHub con este correo. Inicia sesión con esa contraseña."},
            status=status.HTTP_409_CONFLICT,
        )
    try:
        u = User.objects.create(
            name=s.validated_data["name"].strip(),
            email=email,
            password_hash=hash_password(s.validated_data["password"]),
            role="user",
        )
    except IntegrityError:
        return Response({"detail": "Ya existe una cuenta AgroHub con este correo."}, status=status.HTTP_409_CONFLICT)
    return Response({"status": 201, "message": "creada", "data": persona(u)}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def usuario(request, user_id: int):
    u = User.objects.filter(id=user_id).first()
    if not u:
        raise NotFound("Usuario no encontrado")
    return Response({"status": 200, "message": "ok", "data": persona(u)})


@api_view(["POST"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def contrasena(request, user_id: int):
    s = ContrasenaSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    u = User.objects.filter(id=user_id).first()
    if not u:
        raise NotFound("Usuario no encontrado")
    u.password_hash = hash_password(s.validated_data["password"])
    u.password_hash_alt = None
    u.save(update_fields=["password_hash", "password_hash_alt"])
    return Response({"status": 200, "message": "contraseña actualizada", "data": persona(u)})


TICKET_SAL = "agrohub-identidad-ticket"
TICKET_SEGUNDOS = 120


@api_view(["POST"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([])
def ticket(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Inicia sesión en el panel"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"status": 200, "message": "ok", "data": {
        "ticket": signing.dumps({"u": request.user.id}, salt=TICKET_SAL),
        "segundos": TICKET_SEGUNDOS,
    }})


@api_view(["POST"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def canjear(request):
    try:
        datos = signing.loads(str(request.data.get("ticket") or ""), salt=TICKET_SAL, max_age=TICKET_SEGUNDOS)
        u = User.objects.get(id=int(datos["u"]))
    except (signing.BadSignature, KeyError, TypeError, ValueError, User.DoesNotExist):
        return Response({"detail": "Ticket inválido o vencido"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"status": 200, "message": "ok", "data": persona(u)})


@api_view(["POST"])
@authentication_classes(_DECORADORES["auth"])
@permission_classes(_DECORADORES["perms"])
def sesion(request, user_id: int):
    from apps.user_activity.views import abrir_sesion

    u = User.objects.filter(id=user_id).first()
    if u is None:
        raise NotFound()
    return Response({"status": 200, "message": "login ok", "data": abrir_sesion(u, "red-social")})
