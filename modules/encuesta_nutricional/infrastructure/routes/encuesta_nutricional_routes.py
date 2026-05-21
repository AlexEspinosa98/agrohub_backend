from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from modules.encuesta_nutricional.domain.entities import (
    EncuestaNutricionalCreate,
    EncuestaNutricionalDetail,
    EncuestaNutricionalListItem,
    EncuestaNutricionalUpdate,
    MiembroCreate,
    MiembroDetail,
    MiembroUpdate,
    PersonaNutricionalDetail,
    PersonaNutricionalUpdate,
)
from modules.encuesta_nutricional.infrastructure.repositories.mysql_repository import (
    EncuestaNutricionalRepository,
)

router = APIRouter(prefix="/encuesta-nutricional", tags=["Encuesta Nutricional SAN"])


class StandardResponse(BaseModel):
    status: int
    message: str
    data: Optional[Any] = None


class ListResponse(BaseModel):
    status: int
    message: str
    data: List[EncuestaNutricionalListItem]


def get_repo():
    return EncuestaNutricionalRepository()


# ---------------------------------------------------------------------------
# Personas nutricionales — DEBEN ir ANTES de /{numero_encuesta} para evitar
# que FastAPI capture "personas" como valor del parámetro de ruta.
# ---------------------------------------------------------------------------

@router.get(
    "/personas/{cedula}",
    response_model=StandardResponse,
    summary="Buscar participante por cédula",
    description="Devuelve el perfil maestro de un participante registrado en el sistema.",
)
async def get_persona(
    cedula: str,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    persona = repo.get_persona_by_cedula(cedula)
    if not persona:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="participante encontrado",
        data=PersonaNutricionalDetail(**persona).model_dump(),
    )


@router.put(
    "/personas/{persona_id}",
    response_model=StandardResponse,
    summary="Actualizar perfil de participante",
    description="Actualiza nombre, edad, sexo, escolaridad o área de residencia de un participante.",
)
async def update_persona(
    persona_id: int,
    payload: PersonaNutricionalUpdate,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    updated = repo.update_persona(persona_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Participante no encontrado o sin cambios")
    return StandardResponse(status=status.HTTP_200_OK, message="participante actualizado")


# ---------------------------------------------------------------------------
# Encuesta (hogar)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Registrar encuesta con miembros del hogar",
    description=(
        "Crea una encuesta para el hogar y registra los datos individuales de cada miembro "
        "en una sola operación transaccional. "
        "Si un participante (por cédula) ya existe en el sistema, se actualiza su perfil; "
        "de lo contrario se crea uno nuevo. "
        "El número de encuesta se genera automáticamente: SAN-YYYYMMDD-NNNNNN."
    ),
)
async def create_encuesta(
    payload: EncuestaNutricionalCreate,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    result = repo.create(payload)
    return StandardResponse(
        status=status.HTTP_201_CREATED,
        message="encuesta registrada",
        data=result,
    )


@router.get(
    "/",
    response_model=ListResponse,
    summary="Listar encuestas",
    description=(
        "Devuelve el resumen de todas las encuestas activas con el total de miembros. "
        "Filtros: nombre_encuestador, municipio, vereda_comunidad, numero_encuesta, cedula_encuestador."
    ),
)
async def list_encuestas(
    nombre_encuestador: Optional[str] = None,
    municipio: Optional[str] = None,
    vereda_comunidad: Optional[str] = None,
    numero_encuesta: Optional[str] = None,
    cedula_encuestador: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    items = repo.list_surveys(
        nombre_encuestador=nombre_encuestador,
        municipio=municipio,
        vereda_comunidad=vereda_comunidad,
        numero_encuesta=numero_encuesta,
        cedula_encuestador=cedula_encuestador,
        page=page,
        page_size=page_size,
    )
    return ListResponse(
        status=status.HTTP_200_OK,
        message="encuestas encontradas",
        data=items,
    )


@router.get(
    "/{numero_encuesta}",
    response_model=StandardResponse,
    summary="Detalle de encuesta",
    description="Devuelve todos los campos del hogar y la lista completa de miembros con sus mediciones.",
)
async def get_encuesta(
    numero_encuesta: str,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    encuesta = repo.get_detail(numero_encuesta)
    if not encuesta:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="encuesta encontrada",
        data=EncuestaNutricionalDetail(**encuesta).model_dump(),
    )


@router.put(
    "/{numero_encuesta}",
    response_model=StandardResponse,
    summary="Actualizar datos del hogar",
    description="Actualiza campos del hogar (encabezado, sección C, sección D). Para miembros usa /miembros.",
)
async def update_encuesta(
    numero_encuesta: str,
    payload: EncuestaNutricionalUpdate,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    if not repo.get_by_numero(numero_encuesta):
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    updated = repo.update(numero_encuesta, payload)
    if not updated:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    return StandardResponse(status=status.HTTP_200_OK, message="encuesta actualizada")


@router.delete(
    "/{numero_encuesta}",
    response_model=StandardResponse,
    summary="Eliminar encuesta (soft delete)",
    description="Desactiva la encuesta y todos sus miembros sin borrarlos físicamente.",
)
async def delete_encuesta(
    numero_encuesta: str,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    deleted = repo.soft_delete(numero_encuesta)
    if not deleted:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    return StandardResponse(status=status.HTTP_200_OK, message="encuesta eliminada")


# ---------------------------------------------------------------------------
# Miembros
# ---------------------------------------------------------------------------

@router.post(
    "/{numero_encuesta}/miembros",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Agregar miembro a encuesta existente",
    description=(
        "Agrega un nuevo miembro a una encuesta ya creada. "
        "Si la cédula ya existe en personas_nutricionales se reutiliza el perfil."
    ),
)
async def add_miembro(
    numero_encuesta: str,
    payload: MiembroCreate,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    result = repo.add_miembro(numero_encuesta, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    return StandardResponse(
        status=status.HTTP_201_CREATED,
        message="miembro registrado",
        data=result,
    )


@router.get(
    "/{numero_encuesta}/miembros/{miembro_id}",
    response_model=StandardResponse,
    summary="Detalle de un miembro",
    description="Devuelve datos del perfil de la persona y sus mediciones en esta encuesta.",
)
async def get_miembro(
    numero_encuesta: str,
    miembro_id: int,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    encuesta = repo.get_by_numero(numero_encuesta)
    if not encuesta:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    miembro = repo.get_miembro(encuesta["id"], miembro_id)
    if not miembro:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="miembro encontrado",
        data=MiembroDetail(**miembro).model_dump(),
    )


@router.put(
    "/{numero_encuesta}/miembros/{miembro_id}",
    response_model=StandardResponse,
    summary="Actualizar datos de un miembro",
    description=(
        "Actualiza mediciones (sección B) y/o datos del perfil de la persona. "
        "Los cambios en nombre, edad, sexo, etc. se propagan a personas_nutricionales."
    ),
)
async def update_miembro(
    numero_encuesta: str,
    miembro_id: int,
    payload: MiembroUpdate,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    encuesta = repo.get_by_numero(numero_encuesta)
    if not encuesta:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    updated = repo.update_miembro(encuesta["id"], miembro_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Miembro no encontrado o sin cambios")
    return StandardResponse(status=status.HTTP_200_OK, message="miembro actualizado")


@router.delete(
    "/{numero_encuesta}/miembros/{miembro_id}",
    response_model=StandardResponse,
    summary="Eliminar miembro (soft delete)",
    description="Desactiva un miembro del hogar sin borrarlo físicamente.",
)
async def delete_miembro(
    numero_encuesta: str,
    miembro_id: int,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    encuesta = repo.get_by_numero(numero_encuesta)
    if not encuesta:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    deleted = repo.soft_delete_miembro(encuesta["id"], miembro_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    return StandardResponse(status=status.HTTP_200_OK, message="miembro eliminado")

