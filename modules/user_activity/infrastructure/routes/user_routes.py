import json
import os
import re
import uuid
from datetime import date
from typing import Optional, Any, List

import requests as http_requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from modules.user_activity.infrastructure.auth import (
    ensure_admin,
    ensure_superadmin,
    ensure_superadmin_token,
    get_current_user,
)

from modules.user_activity.domain.entities import (
    Association,
    AssociationListItem,
    AssociationCreate,
    AssociationUpdate,
    ChatRequest,
    ChatResponse,
    Logbook,
    LogbookCreate,
    LogbookUpdate,
    Role,
    RoleAssign,
    RoleCreate,
    RoleUpdate,
    SuperadminCreate,
    User,
    UserLogin,
    UserPublic,
    UserRegister,
    UserUpdate,
    AdminUserCreate,
)
from modules.user_activity.infrastructure.repositories.postgres_repository import (
    UserActivityRepository,
)

_GEMINI_SYSTEM_PROMPT = """
Eres el asistente virtual de AgroHub Magdalena, una plataforma para agricultores y comunidades rurales del Caribe colombiano.

Puedes ayudar con dos cosas:
1. Responder preguntas generales sobre AgroHub, asociaciones, cómo usar la app y actividades agrícolas o rurales.
2. Registrar bitácoras de actividad del usuario.

Una bitácora tiene CUATRO campos obligatorios:
- Título: nombre corto de la actividad (ej: "Siembra de maíz", "Reunión de la asociación")
- Descripción: detalle de lo que se realizó
- Fecha de la actividad: en formato YYYY-MM-DD
- Asociación: a cuál de las asociaciones registradas pertenece esta actividad

FLUJO PARA REGISTRAR UNA BITÁCORA:
1. Recoge el título, descripción y fecha de la actividad.
2. Si el usuario no ha indicado la asociación, muéstrale la lista numerada que se te proporcionará y pídele que responda con el NÚMERO o el NOMBRE de su asociación.
3. Una vez tengas los cuatro datos, emite EXACTAMENTE el bloque <BITACORA> con el JSON, seguido del mensaje de confirmación.

Cuando tengas todos los datos, responde EXACTAMENTE así (sustituye los valores entre corchetes por los datos reales, incluyendo el nombre completo de la asociación tal como aparece en la lista):

<BITACORA>
{"titulo": "...", "descripcion": "...", "fecha_actividad": "YYYY-MM-DD", "association_id": <ID_NUMERICO>}
</BITACORA>

✅ Bitácora registrada exitosamente.

📋 Resumen de tu actividad:
• Título: [escribe el título real de la actividad]
• Fecha: [escribe la fecha en formato DD/MM/YYYY]
• Asociación: [escribe el NOMBRE COMPLETO de la asociación, exactamente como aparece en la lista de arriba]
• Descripción: [escribe la descripción real]

¿Deseas registrar otra actividad o tienes alguna pregunta?

REGLAS IMPORTANTES:
- Nunca emitas el bloque <BITACORA> sin el campo association_id.
- Si el usuario escribe un número, mapéalo al ID correspondiente de la lista. Si escribe un nombre, búscalo en la lista y usa su ID.
- Si el nombre no coincide exactamente, elige el más parecido y confírmalo.
- Si al usuario le falta algún dato, pregunta amablemente por el que falta.
- Si el usuario saluda, salúdalo y pregúntale si desea registrar una actividad o tiene alguna duda.
- Responde siempre en español con un tono amigable y cercano para comunidades rurales.
"""


def _parse_logbook_tag(text: str) -> tuple:
    """Extrae datos de bitácora del tag <BITACORA>...</BITACORA>. Retorna (datos_dict, mensaje_limpio)."""
    match = re.search(r"<BITACORA>(.*?)</BITACORA>", text, re.DOTALL)
    if not match:
        return None, text
    try:
        data = json.loads(match.group(1).strip())
        clean_message = text[match.end():].strip()
        return data, clean_message
    except (json.JSONDecodeError, KeyError):
        return None, text


def _call_gemini(api_key: str, system_prompt: str, history: list, user_message: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="google-generativeai no está instalado en este entorno",
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )
    gemini_history = [
        {"role": msg["role"], "parts": [msg["content"]]} for msg in history
    ]
    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(user_message)
    return response.text

router = APIRouter(prefix="/user-activity", tags=["User Activity"])


def get_repo():
    return UserActivityRepository()


class LoginResponse(BaseModel):
    message: str
    user_id: int
    token: str
    role: str


class StandardResponse(BaseModel):
    status: int
    message: str
    data: Optional[Any] = None


class AssociationsResponse(BaseModel):
    status: int
    message: str
    data: List[AssociationListItem]


class UsersResponse(BaseModel):
    status: int
    message: str
    data: List[UserPublic]


class RolesResponse(BaseModel):
    status: int
    message: str
    data: List[Role]


def _sanitize_logbook(entry: dict) -> dict:
    """Remove user_id from logbook payloads before returning to clients."""
    if not entry:
        return entry
    entry = dict(entry)
    entry.pop("user_id", None)
    entry.pop("association_id", None)
    return entry


@router.post(
    "/associations",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear asociación",
    description="Registra una nueva asociación (solo admin).",
)
async def create_association(
    association: AssociationCreate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_admin(current_user)
    repo.create_association(association)
    return StandardResponse(status=status.HTTP_201_CREATED, message="asociación creada")


@router.get(
    "/associations",
    response_model=AssociationsResponse,
    summary="Listar asociaciones",
    description="Devuelve id, nombre y municipio (ciudad) de todas las asociaciones.",
)
async def list_associations(repo: UserActivityRepository = Depends(get_repo)):
    items = repo.list_associations()
    return AssociationsResponse(status=status.HTTP_200_OK, message="asociaciones", data=items)


@router.get(
    "/associations/{association_id}",
    response_model=StandardResponse,
    summary="Consultar asociación",
    description="Obtiene datos de la asociación por su `id`.",
)
async def get_association(association_id: int, repo: UserActivityRepository = Depends(get_repo)):
    assoc = repo.get_association(association_id)
    if not assoc:
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    return StandardResponse(status=status.HTTP_200_OK, message="asociación encontrada", data=assoc)


@router.put(
    "/associations/{association_id}",
    response_model=StandardResponse,
    summary="Editar asociación",
    description="Actualiza datos de la asociación (solo admin).",
)
async def update_association(
    association_id: int,
    payload: AssociationUpdate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_admin(current_user)
    if not repo.get_association(association_id):
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    updated = repo.update_association(association_id, payload)
    if not updated:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return StandardResponse(status=status.HTTP_200_OK, message="asociación actualizada")


@router.post(
    "/users/register",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Registrar usuario (público)",
    description="Crea un usuario sin rol asignado. Un superadmin deberá asignarle un rol luego. `association_id` es opcional; si se envía, debe corresponder a una asociación existente.",
)
async def register_user(user: UserRegister, repo: UserActivityRepository = Depends(get_repo)):
    if user.association_id and not repo.get_association(user.association_id):
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    try:
        user_data = user.dict()
        user_data["role"] = None
        repo.create_user(User(**user_data))
        return StandardResponse(status=status.HTTP_201_CREATED, message="usuario creado", data=None)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Teléfono o identificación ya registrados") from exc


@router.post(
    "/users/superadmin",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear superadmin",
    description=(
        "Crea un usuario con rol **superadmin**. Requiere el header `X-Superadmin-Token` "
        "con el valor configurado en la variable de entorno `SUPERADMIN_TOKEN`."
    ),
)
async def create_superadmin(
    payload: SuperadminCreate,
    x_superadmin_token: Optional[str] = Header(None, alias="X-Superadmin-Token"),
    repo: UserActivityRepository = Depends(get_repo),
):
    ensure_superadmin_token(x_superadmin_token)
    if payload.association_id and not repo.get_association(payload.association_id):
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    try:
        user_data = payload.dict()
        user_data["role"] = "superadmin"
        repo.create_user(User(**user_data))
        return StandardResponse(status=status.HTTP_201_CREATED, message="superadmin creado", data=None)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Teléfono o identificación ya registrados") from exc


@router.get(
    "/users",
    response_model=UsersResponse,
    summary="Listar usuarios",
    description="Lista todos los usuarios registrados (solo superadmin).",
)
async def list_users(
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    return UsersResponse(status=status.HTTP_200_OK, message="usuarios", data=repo.list_users())


@router.put(
    "/users/{user_id}/role",
    response_model=StandardResponse,
    summary="Asignar rol a usuario",
    description="Asigna a un usuario un rol existente en la tabla de roles (solo superadmin).",
)
async def assign_user_role(
    user_id: int,
    payload: RoleAssign,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    if not repo.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not repo.get_role_by_name(payload.role):
        raise HTTPException(status_code=404, detail="El rol especificado no existe")
    repo.assign_role(user_id, payload.role)
    return StandardResponse(status=status.HTTP_200_OK, message="rol asignado", data=None)


@router.get(
    "/roles",
    response_model=RolesResponse,
    summary="Listar roles",
    description="Lista todos los roles disponibles (solo superadmin).",
)
async def list_roles(
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    return RolesResponse(status=status.HTTP_200_OK, message="roles", data=repo.list_roles())


@router.post(
    "/roles",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear rol",
    description="Crea un nuevo rol (solo superadmin).",
)
async def create_role(
    payload: RoleCreate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    if repo.get_role_by_name(payload.name):
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
    repo.create_role(payload)
    return StandardResponse(status=status.HTTP_201_CREATED, message="rol creado", data=None)


@router.put(
    "/roles/{role_id}",
    response_model=StandardResponse,
    summary="Editar rol",
    description="Actualiza nombre y/o descripción de un rol existente (solo superadmin).",
)
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    if not repo.get_role_by_id(role_id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if payload.name:
        existing = repo.get_role_by_name(payload.name)
        if existing and existing["id"] != role_id:
            raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
    updated = repo.update_role(role_id, payload)
    if not updated:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return StandardResponse(status=status.HTTP_200_OK, message="rol actualizado", data=None)


@router.delete(
    "/roles/{role_id}",
    response_model=StandardResponse,
    summary="Eliminar rol",
    description="Elimina un rol (solo superadmin). No se puede eliminar si hay usuarios con ese rol asignado.",
)
async def delete_role(
    role_id: int,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_superadmin(current_user)
    role = repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if repo.count_users_with_role(role["name"]) > 0:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: hay usuarios con este rol asignado",
        )
    repo.delete_role(role_id)
    return StandardResponse(status=status.HTTP_200_OK, message="rol eliminado", data=None)


@router.get(
    "/users/{user_id}",
    response_model=StandardResponse,
    summary="Obtener usuario",
    description="Devuelve datos públicos del usuario por `id`.",
)
async def get_user(user_id: int, repo: UserActivityRepository = Depends(get_repo)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return StandardResponse(status=status.HTTP_200_OK, message="usuario encontrado", data=user)


@router.post(
    "/users/admin-create",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear usuario (admin)",
    description="Permite a un admin crear usuarios y asignar rol.",
)
async def admin_create_user(
    payload: AdminUserCreate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_admin(current_user)
    if payload.association_id and not repo.get_association(payload.association_id):
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    try:
        repo.create_user(User(**payload.dict()))
        return StandardResponse(status=status.HTTP_201_CREATED, message="usuario creado", data=None)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Teléfono o identificación ya registrados") from exc


@router.put(
    "/users/{user_id}",
    response_model=StandardResponse,
    summary="Actualizar usuario (admin)",
    description="Permite a un admin editar datos y rol del usuario.",
)
async def admin_update_user(
    user_id: int,
    payload: UserUpdate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    ensure_admin(current_user)
    if payload.association_id and not repo.get_association(payload.association_id):
        raise HTTPException(status_code=404, detail="Asociación no encontrada")
    if not repo.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        updated = repo.update_user(user_id, payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Datos no válidos o duplicados") from exc
    if not updated:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return StandardResponse(status=status.HTTP_200_OK, message="usuario actualizado", data=None)


@router.post(
    "/users/login",
    response_model=StandardResponse,
    summary="Login de usuario",
    description="Autentica por teléfono, identificación o correo. Retorna token y rol asignado.",
)
async def login(payload: UserLogin, repo: UserActivityRepository = Depends(get_repo)):
    user = repo.get_user_by_phone_or_identification(payload.phone_or_identification)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not repo.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = repo.set_token(user["id"])
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="login ok",
        data={
            "token": token,
            "role": user.get("role", "user"),
            "name": user.get("name"),
            "email": user.get("email"),
        },
    )


@router.post(
    "/logbooks",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear bitácora",
    description="Crea una bitácora para un usuario autenticado. Devuelve el `id` generado.",
)
async def create_logbook(
    logbook: LogbookCreate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    # El user_id se obtiene del token
    logbook_entity = Logbook(
        user_id=current_user["id"],
        association_id=None,
        title=logbook.title,
        description=logbook.description,
        activity_date=logbook.activity_date,
    )
    repo.create_logbook(logbook_entity)
    return StandardResponse(status=status.HTTP_201_CREATED, message="bitácora creada")


@router.put(
    "/logbooks/{logbook_id}",
    response_model=StandardResponse,
    summary="Actualizar bitácora",
    description="Actualiza campos editables de una bitácora existente.",
)
async def update_logbook(
    logbook_id: int,
    payload: LogbookUpdate,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    existing = repo.get_logbook(logbook_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bitácora no encontrada")
    if existing["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para esta bitácora")
    updated = repo.update_logbook(logbook_id, payload)
    if not updated:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return StandardResponse(status=status.HTTP_200_OK, message="bitácora actualizada")


@router.delete(
    "/logbooks/{logbook_id}",
    response_model=StandardResponse,
    summary="Eliminar bitácora",
    description="Elimina una bitácora del usuario autenticado.",
)
async def delete_logbook(
    logbook_id: int,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    existing = repo.get_logbook(logbook_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bitácora no encontrada")
    if existing["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para esta bitácora")
    deleted = repo.delete_logbook(logbook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bitácora no encontrada")
    return StandardResponse(status=status.HTTP_200_OK, message="bitácora eliminada")


@router.get(
    "/logbooks/me",
    response_model=StandardResponse,
    summary="Listar bitácoras",
    description="Lista bitácoras del usuario autenticado. Permite filtrar por fechas, usuario (opcional, pero debe coincidir con el token) y asociación. Incluye paginación.",
)
async def list_my_logbooks(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    association_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    # Seguridad: si se pasa user_id, debe ser el mismo del token
    effective_user_id = user_id if user_id is not None else current_user["id"]
    if effective_user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para este usuario")

    items = repo.list_logbooks(
        user_id=effective_user_id,
        association_id=association_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    sanitized = [_sanitize_logbook(item) for item in items]
    return StandardResponse(status=status.HTTP_200_OK, message="bitácoras del usuario", data=sanitized)


@router.get(
    "/logbooks/{logbook_id}",
    response_model=StandardResponse,
    summary="Consultar bitácora",
    description="Obtiene detalles de una bitácora por `id` (requiere token).",
)
async def get_logbook(
    logbook_id: int,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    logbook = repo.get_logbook(logbook_id)
    if not logbook:
        raise HTTPException(status_code=404, detail="Bitácora no encontrada")
    if logbook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para esta bitácora")
    return StandardResponse(status=status.HTTP_200_OK, message="bitácora encontrada", data=_sanitize_logbook(logbook))


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat asistente AgroHub (IA)",
    description=(
        "Conversación con el asistente de AgroHub impulsado por Gemini. "
        "Mantén el `session_id` entre mensajes para continuar la misma conversación. "
        "El asistente puede responder preguntas generales y guiar al usuario para registrar bitácoras."
    ),
)
async def chat_with_assistant(
    payload: ChatRequest,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY no configurada en el servidor")

    session_id = payload.session_id or str(uuid.uuid4())

    history = repo.get_chat_history(session_id=session_id, user_id=current_user["id"], limit=10)

    associations = repo.list_associations()
    assoc_by_id = {a["id"]: a for a in associations}

    if associations:
        assoc_lines = "\n".join(
            f"{i + 1}. {a['name']}"
            + (f" — {a['municipality']}" if a.get("municipality") else "")
            + f" (ID interno: {a['id']})"
            for i, a in enumerate(associations)
        )
        assoc_context = f"\n\nAsociaciones registradas en AgroHub (usa el ID interno en el JSON):\n{assoc_lines}"
    else:
        assoc_context = "\n\n(No hay asociaciones registradas aún.)"

    system_prompt = (
        f"{_GEMINI_SYSTEM_PROMPT}"
        f"{assoc_context}\n\n"
        f"El usuario se llama {current_user['name']}."
    )

    raw_reply = _call_gemini(
        api_key=api_key,
        system_prompt=system_prompt,
        history=history,
        user_message=payload.message,
    )

    logbook_data, reply_text = _parse_logbook_tag(raw_reply)

    created_logbook = None
    required_keys = ("titulo", "descripcion", "fecha_actividad", "association_id")
    if logbook_data and all(k in logbook_data for k in required_keys):
        try:
            activity_date = date.fromisoformat(logbook_data["fecha_actividad"])
            association_id = int(logbook_data["association_id"])
            assoc_info = assoc_by_id.get(association_id)
            logbook_entity = Logbook(
                user_id=current_user["id"],
                association_id=association_id if assoc_info else None,
                title=logbook_data["titulo"],
                description=logbook_data["descripcion"],
                activity_date=activity_date,
            )
            logbook_id = repo.create_logbook(logbook_entity)
            created_logbook = {
                "id": logbook_id,
                "title": logbook_data["titulo"],
                "description": logbook_data["descripcion"],
                "activity_date": logbook_data["fecha_actividad"],
                "association_id": association_id if assoc_info else None,
                "association_name": assoc_info["name"] if assoc_info else None,
            }
        except (ValueError, Exception):
            reply_text = (
                "Tuve un problema al registrar la bitácora. "
                "¿Puedes verificar que la fecha esté en formato correcto (YYYY-MM-DD)?"
            )

    repo.add_chat_message(session_id=session_id, user_id=current_user["id"], role="user", content=payload.message)
    repo.add_chat_message(session_id=session_id, user_id=current_user["id"], role="model", content=reply_text)

    return ChatResponse(reply=reply_text, session_id=session_id, logbook_created=created_logbook)


# ── WhatsApp webhook (Meta Business API) ─────────────────────────────────────

_WA_API_URL = "https://graph.facebook.com/v19.0"
_WA_NO_USER_MSG = (
    "No encontré tu número registrado en AgroHub. "
    "Por favor regístrate primero en la aplicación para poder usar el asistente."
)
_WA_NO_TEXT_MSG = (
    "Solo puedo procesar mensajes de texto por ahora. "
    "Escríbeme qué actividad deseas registrar."
)


def _send_whatsapp_message(phone_number_id: str, token: str, to: str, text: str) -> None:
    url = f"{_WA_API_URL}/{phone_number_id}/messages"
    http_requests.post(
        url,
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )


def _find_user_by_wa_phone(repo: UserActivityRepository, wa_phone: str) -> Optional[dict]:
    """WhatsApp envía el número con código de país (ej: 573001234567).
    Intenta coincidencia exacta y luego sin el prefijo 57 de Colombia."""
    user = repo.get_user_by_phone_or_identification(wa_phone)
    if user:
        return user
    if wa_phone.startswith("57") and len(wa_phone) > 10:
        return repo.get_user_by_phone_or_identification(wa_phone[2:])
    return None


def _extract_wa_payload(body: dict) -> tuple:
    """Extrae (wa_phone, text, phone_number_id) del payload de Meta. Retorna Nones si no aplica."""
    try:
        change_value = body["entry"][0]["changes"][0]["value"]
        phone_number_id = change_value["metadata"]["phone_number_id"]
        messages = change_value.get("messages")
        if not messages:
            return None, None, None
        msg = messages[0]
        wa_phone = msg["from"]
        text = msg["text"]["body"] if msg.get("type") == "text" else None
        return wa_phone, text, phone_number_id
    except (KeyError, IndexError):
        return None, None, None


@router.get(
    "/whatsapp",
    include_in_schema=False,
)
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Challenge de verificación que Meta llama una sola vez al configurar el webhook."""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verificación fallida")


@router.post(
    "/whatsapp",
    include_in_schema=False,
)
async def whatsapp_webhook(request: Request, repo: UserActivityRepository = Depends(get_repo)):
    """Recibe mensajes entrantes de WhatsApp (Meta Business API)."""
    body = await request.json()

    wa_phone, text, phone_number_id = _extract_wa_payload(body)

    # Si no hay mensaje de texto procesable, retornamos 200 igual (Meta lo exige)
    if not wa_phone or not phone_number_id:
        return {"status": "ignored"}

    wa_token = os.getenv("WHATSAPP_TOKEN")
    if not wa_token:
        return {"status": "ignored"}

    if not text:
        _send_whatsapp_message(phone_number_id, wa_token, wa_phone, _WA_NO_TEXT_MSG)
        return {"status": "ok"}

    user = _find_user_by_wa_phone(repo, wa_phone)
    if not user:
        _send_whatsapp_message(phone_number_id, wa_token, wa_phone, _WA_NO_USER_MSG)
        return {"status": "ok"}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"status": "ignored"}

    # El session_id de WhatsApp es el teléfono del usuario (conversación persistente por contacto)
    session_id = f"wa_{wa_phone}"

    history = repo.get_chat_history(session_id=session_id, user_id=user["id"], limit=10)

    associations = repo.list_associations()
    assoc_by_id = {a["id"]: a for a in associations}
    if associations:
        assoc_lines = "\n".join(
            f"{i + 1}. {a['name']}"
            + (f" — {a['municipality']}" if a.get("municipality") else "")
            + f" (ID interno: {a['id']})"
            for i, a in enumerate(associations)
        )
        assoc_context = f"\n\nAsociaciones registradas en AgroHub (usa el ID interno en el JSON):\n{assoc_lines}"
    else:
        assoc_context = "\n\n(No hay asociaciones registradas aún.)"

    system_prompt = (
        f"{_GEMINI_SYSTEM_PROMPT}"
        f"{assoc_context}\n\n"
        f"El usuario se llama {user['name']}."
    )

    raw_reply = _call_gemini(
        api_key=api_key,
        system_prompt=system_prompt,
        history=history,
        user_message=text,
    )

    logbook_data, reply_text = _parse_logbook_tag(raw_reply)

    required_keys = ("titulo", "descripcion", "fecha_actividad", "association_id")
    if logbook_data and all(k in logbook_data for k in required_keys):
        try:
            activity_date = date.fromisoformat(logbook_data["fecha_actividad"])
            association_id = int(logbook_data["association_id"])
            assoc_info = assoc_by_id.get(association_id)
            logbook_entity = Logbook(
                user_id=user["id"],
                association_id=association_id if assoc_info else None,
                title=logbook_data["titulo"],
                description=logbook_data["descripcion"],
                activity_date=activity_date,
            )
            repo.create_logbook(logbook_entity)
        except (ValueError, Exception):
            reply_text = (
                "Tuve un problema al registrar la bitácora. "
                "¿Puedes verificar que la fecha esté en formato correcto (YYYY-MM-DD)?"
            )

    repo.add_chat_message(session_id=session_id, user_id=user["id"], role="user", content=text)
    repo.add_chat_message(session_id=session_id, user_id=user["id"], role="model", content=reply_text)

    _send_whatsapp_message(phone_number_id, wa_token, wa_phone, reply_text)
    return {"status": "ok"}
