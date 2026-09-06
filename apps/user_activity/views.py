import hashlib
import secrets
import uuid
from datetime import date as date_cls
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotAuthenticated, NotFound, ParseError, PermissionDenied, Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.chat_service import (
    ServiceUnavailable,
    build_system_prompt,
    call_gemini,
    parse_logbook_tag,
)
from apps.user_activity.email_service import send_otp_email
from apps.user_activity.models import Association, Conversation, Logbook, Role, Session, User
from apps.user_activity.permissions import (
    HasSuperadminServerToken,
    IsAdminRole,
    IsAuthenticatedWithRole,
    IsSuperadminRole,
)
from apps.user_activity.serializers import (
    AdminUserCreateSerializer,
    AssociationCreateSerializer,
    AssociationUpdateSerializer,
    ChatRequestSerializer,
    LogbookCreateSerializer,
    LogbookUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RoleAssignSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
    SuperadminCreateSerializer,
    UserLoginSerializer,
    UserRegisterSerializer,
    UserUpdateSerializer,
)
from apps.user_activity.whatsapp_service import (
    WA_NO_TEXT_MSG,
    WA_NO_USER_MSG,
    extract_wa_payload,
    find_user_by_wa_phone,
    send_whatsapp_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_password(raw: str, hashed: str) -> bool:
    return hash_password(raw) == hashed


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


_OTP_TTL_MINUTES = 10
_OTP_COOLDOWN_SECONDS = 60


def _find_user_by_login(value: str):
    return User.objects.filter(Q(phone=value) | Q(identification=value) | Q(email=value)).first()


def _serialize_association(a: Association) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "latitude": a.latitude,
        "longitude": a.longitude,
        "department": a.department,
        "municipality": a.municipality,
        "vereda": a.vereda,
        "created_at": a.created_at,
    }


def _serialize_association_list_item(a: Association) -> dict:
    return {"id": a.id, "name": a.name, "municipality": a.municipality}


def _serialize_user_public(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "phone": u.phone,
        "identification": u.identification,
        "email": u.email,
        "association_id": u.association_id,
        "role": u.role,
        "created_at": u.created_at,
    }


def _serialize_role(r: Role) -> dict:
    return {"id": r.id, "name": r.name, "description": r.description, "created_at": r.created_at}


def _serialize_logbook(l: Logbook, association_name=None) -> dict:
    return {
        "id": l.id,
        "title": l.title,
        "description": l.description,
        "activity_date": l.activity_date,
        "created_at": l.created_at,
        "association_name": association_name,
    }


# ---------------------------------------------------------------------------
# Associations
# ---------------------------------------------------------------------------

class AssociationListCreateView(APIView):
    """GET is public (list), POST requires admin — two different permission
    sets on the same path, so this can't be a plain @api_view function."""

    authentication_classes = [TokenHeaderAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticatedWithRole(), IsAdminRole()]
        return [AllowAny()]

    def get(self, request):
        items = [_serialize_association_list_item(a) for a in Association.objects.order_by("name")]
        return Response({"status": status.HTTP_200_OK, "message": "asociaciones", "data": items})

    def post(self, request):
        serializer = AssociationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Association.objects.create(**serializer.validated_data)
        return Response(
            {"status": status.HTTP_201_CREATED, "message": "asociación creada", "data": None},
            status=status.HTTP_201_CREATED,
        )


class AssociationDetailView(APIView):
    """GET is public, PUT requires admin."""

    authentication_classes = [TokenHeaderAuthentication]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticatedWithRole(), IsAdminRole()]
        return [AllowAny()]

    def get(self, request, association_id: int):
        assoc = Association.objects.filter(id=association_id).first()
        if not assoc:
            raise NotFound("Asociación no encontrada")
        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": "asociación encontrada",
                "data": _serialize_association(assoc),
            }
        )

    def put(self, request, association_id: int):
        assoc = Association.objects.filter(id=association_id).first()
        if not assoc:
            raise NotFound("Asociación no encontrada")
        serializer = AssociationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = {k: v for k, v in serializer.validated_data.items() if v is not None}
        if not fields:
            raise ParseError("Nada para actualizar")
        for key, value in fields.items():
            setattr(assoc, key, value)
        assoc.save(update_fields=list(fields.keys()))
        return Response({"status": status.HTTP_200_OK, "message": "asociación actualizada", "data": None})


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@api_view(["POST"])
def register_user(request):
    serializer = UserRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data.get("association_id") and not Association.objects.filter(id=data["association_id"]).exists():
        raise NotFound("Asociación no encontrada")
    try:
        User.objects.create(
            name=data["name"],
            phone=data["phone"],
            identification=data["identification"],
            email=data.get("email"),
            password_hash=hash_password(data["password"]),
            association_id=data.get("association_id"),
            role=None,
        )
    except IntegrityError as exc:
        raise ParseError("Teléfono o identificación ya registrados") from exc
    return Response(
        {"status": status.HTTP_201_CREATED, "message": "usuario creado", "data": None},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([HasSuperadminServerToken])
def create_superadmin(request):
    serializer = SuperadminCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data.get("association_id") and not Association.objects.filter(id=data["association_id"]).exists():
        raise NotFound("Asociación no encontrada")
    try:
        User.objects.create(
            name=data["name"],
            phone=data["phone"],
            identification=data["identification"],
            email=data.get("email"),
            password_hash=hash_password(data["password"]),
            association_id=data.get("association_id"),
            role="superadmin",
        )
    except IntegrityError as exc:
        raise ParseError("Teléfono o identificación ya registrados") from exc
    return Response(
        {"status": status.HTTP_201_CREATED, "message": "superadmin creado", "data": None},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole, IsSuperadminRole])
def list_users(request):
    items = [_serialize_user_public(u) for u in User.objects.order_by("-created_at")]
    return Response({"status": status.HTTP_200_OK, "message": "usuarios", "data": items})


@api_view(["PUT"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole, IsSuperadminRole])
def assign_user_role(request, user_id: int):
    serializer = RoleAssignSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise NotFound("Usuario no encontrado")
    if not Role.objects.filter(name=serializer.validated_data["role"]).exists():
        raise NotFound("El rol especificado no existe")
    user.role = serializer.validated_data["role"]
    user.save(update_fields=["role"])
    return Response({"status": status.HTTP_200_OK, "message": "rol asignado", "data": None})


class UserDetailView(APIView):
    """GET is public, PUT requires admin."""

    authentication_classes = [TokenHeaderAuthentication]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticatedWithRole(), IsAdminRole()]
        return [AllowAny()]

    def get(self, request, user_id: int):
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFound("Usuario no encontrado")
        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": "usuario encontrado",
                "data": _serialize_user_public(user),
            }
        )

    def put(self, request, user_id: int):
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = {k: v for k, v in serializer.validated_data.items() if v is not None}
        if data.get("association_id") and not Association.objects.filter(id=data["association_id"]).exists():
            raise NotFound("Asociación no encontrada")
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFound("Usuario no encontrado")
        if not data:
            raise ParseError("Nada para actualizar")
        try:
            for key, value in data.items():
                setattr(user, key, value)
            user.save(update_fields=list(data.keys()))
        except IntegrityError as exc:
            raise ParseError("Datos no válidos o duplicados") from exc
        return Response({"status": status.HTTP_200_OK, "message": "usuario actualizado", "data": None})


@api_view(["POST"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole, IsAdminRole])
def admin_create_user(request):
    serializer = AdminUserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data.get("association_id") and not Association.objects.filter(id=data["association_id"]).exists():
        raise NotFound("Asociación no encontrada")
    try:
        User.objects.create(
            name=data["name"],
            phone=data["phone"],
            identification=data["identification"],
            email=data.get("email"),
            password_hash=hash_password(data["password"]),
            association_id=data.get("association_id"),
            role=data.get("role", "user"),
        )
    except IntegrityError as exc:
        raise ParseError("Teléfono o identificación ya registrados") from exc
    return Response(
        {"status": status.HTTP_201_CREATED, "message": "usuario creado", "data": None},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    user = _find_user_by_login(data["phone_or_identification"])
    if not user or not verify_password(data["password"], user.password_hash):
        return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
    token = str(uuid.uuid4())
    platform = data.get("platform")
    if platform:
        Session.objects.filter(user=user, platform=platform).delete()
    Session.objects.create(user=user, token=token, platform=platform)
    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "login ok",
            "data": {
                "token": token,
                "role": user.role or "user",
                "name": user.name,
                "email": user.email,
            },
        }
    )


@api_view(["POST"])
@authentication_classes([TokenHeaderAuthentication])
def logout(request):
    if not request.user.is_authenticated:
        raise NotAuthenticated("Falta header Authorization: Token <token>")
    Session.objects.filter(token=request.auth).delete()
    return Response({"status": status.HTTP_200_OK, "message": "sesión cerrada", "data": None})


@api_view(["POST"])
def forgot_password(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    generic_response = Response(
        {
            "status": status.HTTP_200_OK,
            "message": "Si el correo está registrado, se envió un código de verificación",
            "data": None,
        }
    )
    user = _find_user_by_login(serializer.validated_data["email"])
    if not user or not user.email:
        return generic_response

    if user.reset_otp_expires_at:
        requested_at = user.reset_otp_expires_at - timedelta(minutes=_OTP_TTL_MINUTES)
        if (timezone.now() - requested_at).total_seconds() < _OTP_COOLDOWN_SECONDS:
            raise Throttled(detail="Espera un momento antes de solicitar otro código")

    otp = generate_otp()
    user.reset_otp_hash = hash_password(otp)
    user.reset_otp_expires_at = timezone.now() + timedelta(minutes=_OTP_TTL_MINUTES)
    user.save(update_fields=["reset_otp_hash", "reset_otp_expires_at"])
    try:
        send_otp_email(user.email, otp, ttl_minutes=_OTP_TTL_MINUTES)
    except Exception as exc:  # noqa: BLE001
        raise ServiceUnavailable("No se pudo enviar el correo, intenta más tarde") from exc
    return generic_response


@api_view(["POST"])
def reset_password(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    user = _find_user_by_login(data["email"])
    otp_ok = bool(
        user
        and user.reset_otp_hash
        and user.reset_otp_expires_at
        and timezone.now() <= user.reset_otp_expires_at
        and hash_password(data["otp"]) == user.reset_otp_hash
    )
    if not otp_ok:
        raise ParseError("Código inválido o expirado")
    user.password_hash = hash_password(data["new_password"])
    user.reset_otp_hash = None
    user.reset_otp_expires_at = None
    user.save(update_fields=["password_hash", "reset_otp_hash", "reset_otp_expires_at"])
    Session.objects.filter(user=user).delete()
    return Response({"status": status.HTTP_200_OK, "message": "contraseña actualizada", "data": None})


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole, IsSuperadminRole])
def roles_list_create(request):
    if request.method == "POST":
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if Role.objects.filter(name=data["name"]).exists():
            raise ParseError("Ya existe un rol con ese nombre")
        Role.objects.create(**data)
        return Response(
            {"status": status.HTTP_201_CREATED, "message": "rol creado", "data": None},
            status=status.HTTP_201_CREATED,
        )
    items = [_serialize_role(r) for r in Role.objects.order_by("name")]
    return Response({"status": status.HTTP_200_OK, "message": "roles", "data": items})


@api_view(["PUT", "DELETE"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole, IsSuperadminRole])
def role_detail(request, role_id: int):
    role = Role.objects.filter(id=role_id).first()
    if not role:
        raise NotFound("Rol no encontrado")

    if request.method == "DELETE":
        if User.objects.filter(role=role.name).count() > 0:
            raise ParseError("No se puede eliminar: hay usuarios con este rol asignado")
        role.delete()
        return Response({"status": status.HTTP_200_OK, "message": "rol eliminado", "data": None})

    serializer = RoleUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = {k: v for k, v in serializer.validated_data.items() if v is not None}
    if data.get("name"):
        existing = Role.objects.filter(name=data["name"]).exclude(id=role_id).first()
        if existing:
            raise ParseError("Ya existe un rol con ese nombre")
    if not data:
        raise ParseError("Nada para actualizar")
    for key, value in data.items():
        setattr(role, key, value)
    role.save(update_fields=list(data.keys()))
    return Response({"status": status.HTTP_200_OK, "message": "rol actualizado", "data": None})


# ---------------------------------------------------------------------------
# Logbooks
# ---------------------------------------------------------------------------

@api_view(["POST"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def create_logbook(request):
    serializer = LogbookCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    Logbook.objects.create(
        user=request.user,
        association=None,
        title=data["title"],
        description=data["description"],
        activity_date=data["activity_date"],
    )
    return Response(
        {"status": status.HTTP_201_CREATED, "message": "bitácora creada", "data": None},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "DELETE"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def logbook_detail(request, logbook_id: int):
    logbook = Logbook.objects.select_related("association").filter(id=logbook_id).first()
    if not logbook:
        raise NotFound("Bitácora no encontrada")
    if logbook.user_id != request.user.id:
        raise PermissionDenied("No autorizado para esta bitácora")

    if request.method == "DELETE":
        logbook.delete()
        return Response({"status": status.HTTP_200_OK, "message": "bitácora eliminada", "data": None})

    if request.method == "GET":
        data = _serialize_logbook(logbook, logbook.association.name if logbook.association else None)
        return Response({"status": status.HTTP_200_OK, "message": "bitácora encontrada", "data": data})

    serializer = LogbookUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = {k: v for k, v in serializer.validated_data.items() if v is not None}
    if not data:
        raise ParseError("Nada para actualizar")
    for key, value in data.items():
        setattr(logbook, key, value)
    logbook.save()
    return Response({"status": status.HTTP_200_OK, "message": "bitácora actualizada", "data": None})


@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def list_my_logbooks(request):
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    user_id = request.query_params.get("user_id")
    association_id = request.query_params.get("association_id")
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 50))

    effective_user_id = int(user_id) if user_id else request.user.id
    if effective_user_id != request.user.id:
        raise PermissionDenied("No autorizado para este usuario")

    qs = Logbook.objects.select_related("association").filter(user_id=effective_user_id)
    if association_id:
        qs = qs.filter(association_id=association_id)
    if start_date:
        qs = qs.filter(activity_date__gte=start_date)
    if end_date:
        qs = qs.filter(activity_date__lte=end_date)
    offset = (page - 1) * page_size
    qs = qs.order_by("-activity_date")[offset : offset + page_size]

    items = [_serialize_logbook(l, l.association.name if l.association else None) for l in qs]
    return Response({"status": status.HTTP_200_OK, "message": "bitácoras del usuario", "data": items})


# ---------------------------------------------------------------------------
# Chat (Gemini)
# ---------------------------------------------------------------------------

@api_view(["POST"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def chat_with_assistant(request):
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ServiceUnavailable("GEMINI_API_KEY no configurada en el servidor")

    session_id = payload.get("session_id") or str(uuid.uuid4())

    history = list(
        Conversation.objects.filter(session_id=session_id, user_id=request.user.id)
        .order_by("-created_at")[:10]
        .values("role", "content")
    )
    history.reverse()

    associations = list(Association.objects.order_by("name").values("id", "name", "municipality"))
    assoc_by_id = {a["id"]: a for a in associations}

    system_prompt = build_system_prompt(associations, request.user.name)

    raw_reply = call_gemini(
        api_key=api_key, system_prompt=system_prompt, history=history, user_message=payload["message"]
    )

    logbook_data, reply_text = parse_logbook_tag(raw_reply)

    created_logbook = None
    required_keys = ("titulo", "descripcion", "fecha_actividad", "association_id")
    if logbook_data and all(k in logbook_data for k in required_keys):
        try:
            activity_date = date_cls.fromisoformat(logbook_data["fecha_actividad"])
            association_id = int(logbook_data["association_id"])
            assoc_info = assoc_by_id.get(association_id)
            logbook = Logbook.objects.create(
                user_id=request.user.id,
                association_id=association_id if assoc_info else None,
                title=logbook_data["titulo"],
                description=logbook_data["descripcion"],
                activity_date=activity_date,
            )
            created_logbook = {
                "id": logbook.id,
                "title": logbook_data["titulo"],
                "description": logbook_data["descripcion"],
                "activity_date": logbook_data["fecha_actividad"],
                "association_id": association_id if assoc_info else None,
                "association_name": assoc_info["name"] if assoc_info else None,
            }
        except (ValueError, TypeError):
            reply_text = (
                "Tuve un problema al registrar la bitácora. "
                "¿Puedes verificar que la fecha esté en formato correcto (YYYY-MM-DD)?"
            )

    Conversation.objects.create(
        session_id=session_id, user_id=request.user.id, role="user", content=payload["message"]
    )
    Conversation.objects.create(
        session_id=session_id, user_id=request.user.id, role="model", content=reply_text
    )

    return Response({"reply": reply_text, "session_id": session_id, "logbook_created": created_logbook})


# ---------------------------------------------------------------------------
# WhatsApp webhook (Meta Business API)
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def whatsapp_webhook(request):
    if request.method == "GET":
        return _whatsapp_verify(request)
    return _whatsapp_receive(request)


def _whatsapp_verify(request):
    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")
    verify_token = settings.WHATSAPP_VERIFY_TOKEN
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return HttpResponse(hub_challenge, content_type="text/plain")
    raise PermissionDenied("Verificación fallida")


def _whatsapp_receive(request):
    body = request.data
    wa_phone, text, phone_number_id = extract_wa_payload(body)

    if not wa_phone or not phone_number_id:
        return Response({"status": "ignored"})

    wa_token = settings.WHATSAPP_TOKEN
    if not wa_token:
        return Response({"status": "ignored"})

    if not text:
        send_whatsapp_message(phone_number_id, wa_token, wa_phone, WA_NO_TEXT_MSG)
        return Response({"status": "ok"})

    user = find_user_by_wa_phone(wa_phone)
    if not user:
        send_whatsapp_message(phone_number_id, wa_token, wa_phone, WA_NO_USER_MSG)
        return Response({"status": "ok"})

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return Response({"status": "ignored"})

    session_id = f"wa_{wa_phone}"
    history = list(
        Conversation.objects.filter(session_id=session_id, user_id=user.id)
        .order_by("-created_at")[:10]
        .values("role", "content")
    )
    history.reverse()

    associations = list(Association.objects.order_by("name").values("id", "name", "municipality"))
    assoc_by_id = {a["id"]: a for a in associations}
    system_prompt = build_system_prompt(associations, user.name)

    raw_reply = call_gemini(
        api_key=api_key, system_prompt=system_prompt, history=history, user_message=text
    )
    logbook_data, reply_text = parse_logbook_tag(raw_reply)

    required_keys = ("titulo", "descripcion", "fecha_actividad", "association_id")
    if logbook_data and all(k in logbook_data for k in required_keys):
        try:
            activity_date = date_cls.fromisoformat(logbook_data["fecha_actividad"])
            association_id = int(logbook_data["association_id"])
            assoc_info = assoc_by_id.get(association_id)
            Logbook.objects.create(
                user_id=user.id,
                association_id=association_id if assoc_info else None,
                title=logbook_data["titulo"],
                description=logbook_data["descripcion"],
                activity_date=activity_date,
            )
        except (ValueError, TypeError):
            reply_text = (
                "Tuve un problema al registrar la bitácora. "
                "¿Puedes verificar que la fecha esté en formato correcto (YYYY-MM-DD)?"
            )

    Conversation.objects.create(session_id=session_id, user_id=user.id, role="user", content=text)
    Conversation.objects.create(session_id=session_id, user_id=user.id, role="model", content=reply_text)

    send_whatsapp_message(phone_number_id, wa_token, wa_phone, reply_text)
    return Response({"status": "ok"})
