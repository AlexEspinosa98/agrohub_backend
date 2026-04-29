from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from modules.encuesta_nutricional.domain.entities import (
    EncuestaNutricionalCreate,
    EncuestaNutricionalDetail,
    EncuestaNutricionalListItem,
    EncuestaNutricionalUpdate,
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


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Registrar encuesta",
    description=(
        "Crea una nueva encuesta de seguridad alimentaria y nutricional. "
        "Campos obligatorios: encabezado (nombre_encuestador, cedula_encuestador, "
        "fecha_aplicacion, municipio, vereda_comunidad) y cierre "
        "(consentimiento_informado, cedula_participante). "
        "El número de encuesta se genera automáticamente con formato SAN-YYYYMMDD-NNNNNN."
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
        "Devuelve el resumen de todas las encuestas activas: número, encuestador, cédula encuestador, "
        "fecha, municipio, vereda, cédula y nombre del participante. "
        "Filtros disponibles: nombre_encuestador, municipio, vereda_comunidad, numero_encuesta, cedula_encuestador."
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
    description="Devuelve todos los campos de una encuesta identificada por su número de formulario.",
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
    summary="Actualizar encuesta",
    description="Actualiza uno o varios campos de la encuesta identificada por su número de formulario.",
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
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="encuesta actualizada",
    )


@router.delete(
    "/{numero_encuesta}",
    response_model=StandardResponse,
    summary="Eliminar encuesta (soft delete)",
    description="Desactiva la encuesta sin borrarla físicamente de la base de datos.",
)
async def delete_encuesta(
    numero_encuesta: str,
    repo: EncuestaNutricionalRepository = Depends(get_repo),
):
    deleted = repo.soft_delete(numero_encuesta)
    if not deleted:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    return StandardResponse(
        status=status.HTTP_200_OK,
        message="encuesta eliminada",
    )
