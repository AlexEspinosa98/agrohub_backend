from datetime import date
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from modules.user_activity.domain.entities import (
    Association,
    Logbook,
    LogbookCreate,
    LogbookUpdate,
    User,
    UserLogin,
    UserPublic,
)
from modules.user_activity.infrastructure.repositories.postgres_repository import (
    UserActivityRepository,
)

router = APIRouter(prefix="/user-activity", tags=["User Activity"])

auth_scheme = APIKeyHeader(
    name="Authorization",
    description="Usa el formato: `Token <tu_token>`",
    auto_error=False,
)

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


def get_current_user(
    authorization: str = Security(auth_scheme),
    repo: UserActivityRepository = Depends(get_repo),
):
    if not authorization or not authorization.lower().startswith("token "):
        raise HTTPException(status_code=401, detail="Falta header Authorization: Token <token>")
    token = authorization.split(" ", 1)[1]
    user = repo.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido")
    return user


@router.post(
    "/associations",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Crear asociación",
    description="Registra una nueva asociación. Devuelve el `id` generado.",
)
async def create_association(association: Association, repo: UserActivityRepository = Depends(get_repo)):
    repo.create_association(association)
    return StandardResponse(status=status.HTTP_201_CREATED, message="asociación creada")


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


@router.post(
    "/users/register",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Registrar usuario",
    description="Crea un usuario con rol por defecto **user**. Devuelve el `id` generado.",
)
async def register_user(user: User, repo: UserActivityRepository = Depends(get_repo)):
    try:
        # Forzamos rol por defecto en registro
        user.role = "user"
        repo.create_user(user)
        return StandardResponse(status=status.HTTP_201_CREATED, message="usuario creado")
    except Exception as exc:  # noqa: BLE001
        # Posible violación de unique
        raise HTTPException(status_code=400, detail="Teléfono o identificación ya registrados") from exc


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
    "/users/login",
    response_model=StandardResponse,
    summary="Login de usuario",
    description="Autentica por teléfono o identificación. Retorna token y rol asignado.",
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
    "/logbooks/by-user/{user_id}",
    response_model=StandardResponse,
    summary="Listar bitácoras por usuario",
    description="Lista bitácoras filtrando opcionalmente por rango de fechas.",
)
async def list_logbooks_by_user(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado para este usuario")
    items = repo.list_logbooks_by_user(user_id, start_date, end_date)
    return StandardResponse(status=status.HTTP_200_OK, message="bitácoras del usuario", data=items)


@router.get(
    "/logbooks/me",
    response_model=StandardResponse,
    summary="Listar mis bitácoras",
    description="Devuelve todas las bitácoras del usuario autenticado.",
)
async def list_my_logbooks(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    items = repo.list_logbooks_by_user(current_user["id"], start_date, end_date)
    return StandardResponse(status=status.HTTP_200_OK, message="bitácoras del usuario autenticado", data=items)


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
    return StandardResponse(status=status.HTTP_200_OK, message="bitácora encontrada", data=logbook)


@router.get(
    "/logbooks/by-association/{association_id}",
    response_model=StandardResponse,
    summary="Listar bitácoras por asociación",
    description="Lista bitácoras de una asociación, con filtros de fechas opcionales.",
)
async def list_logbooks_by_association(
    association_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    repo: UserActivityRepository = Depends(get_repo),
    current_user=Depends(get_current_user),
):
    items = repo.list_logbooks_by_association(association_id, start_date, end_date)
    return StandardResponse(status=status.HTTP_200_OK, message="bitácoras de la asociación", data=items)
