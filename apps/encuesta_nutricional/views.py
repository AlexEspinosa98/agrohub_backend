import io

import pandas as pd
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.response import Response

from apps.encuesta_nutricional import services
from apps.encuesta_nutricional.models import PersonaNutricional
from apps.encuesta_nutricional.serializers import (
    EncuestaNutricionalCreateSerializer,
    EncuestaNutricionalUpdateSerializer,
    MiembroCreateSerializer,
    MiembroUpdateSerializer,
    PersonaNutricionalUpdateSerializer,
)
from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.permissions import IsAuthenticatedWithRole


def _persona_to_dict(p: PersonaNutricional) -> dict:
    return {
        "id": p.id,
        "cedula": p.cedula,
        "nombre": p.nombre,
        "edad_anios": p.edad_anios,
        "sexo": p.sexo,
        "area_residencia": p.area_residencia,
        "nivel_educativo": p.nivel_educativo,
        "is_active": p.is_active,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


# ---------------------------------------------------------------------------
# Personas nutricionales
# ---------------------------------------------------------------------------

@api_view(["GET", "PUT"])
def persona_detail(request, value):
    if request.method == "GET":
        persona = PersonaNutricional.objects.filter(cedula=value, is_active=True).first()
        if not persona:
            raise NotFound("Participante no encontrado")
        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": "participante encontrado",
                "data": _persona_to_dict(persona),
            }
        )

    try:
        persona_id = int(value)
    except ValueError as exc:
        raise NotFound("Participante no encontrado o sin cambios") from exc
    serializer = PersonaNutricionalUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updated = services.update_persona(persona_id, serializer.validated_data)
    if not updated:
        raise NotFound("Participante no encontrado o sin cambios")
    return Response({"status": status.HTTP_200_OK, "message": "participante actualizado"})


# ---------------------------------------------------------------------------
# Encuesta (hogar)
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def encuestas_list_create(request):
    if request.method == "POST":
        serializer = EncuestaNutricionalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.create_encuesta(dict(serializer.validated_data))
        return Response(
            {"status": status.HTTP_201_CREATED, "message": "encuesta registrada", "data": result},
            status=status.HTTP_201_CREATED,
        )

    params = request.query_params
    items = services.list_surveys(
        nombre_encuestador=params.get("nombre_encuestador"),
        municipio=params.get("municipio"),
        vereda_comunidad=params.get("vereda_comunidad"),
        numero_encuesta=params.get("numero_encuesta"),
        cedula_encuestador=params.get("cedula_encuestador"),
        page=int(params.get("page", 1)),
        page_size=int(params.get("page_size", 50)),
    )
    return Response({"status": status.HTTP_200_OK, "message": "encuestas encontradas", "data": items})


# ---------------------------------------------------------------------------
# Dashboard / estadísticas
# ---------------------------------------------------------------------------

@api_view(["GET"])
def dashboard_municipios(request):
    items = services.get_resumen_por_municipio()
    return Response({"status": status.HTTP_200_OK, "message": "resumen generado", "data": items})


@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def dashboard_veredas(request):
    items = services.get_resumen_por_vereda(municipio=request.query_params.get("municipio"))
    return Response({"status": status.HTTP_200_OK, "message": "resumen generado", "data": items})


@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def dashboard_detalle_municipio(request, municipio: str):
    detalle = services.get_detalle_municipio(municipio)
    if not detalle:
        raise NotFound("No hay encuestas activas para ese municipio")
    return Response({"status": status.HTTP_200_OK, "message": "detalle generado", "data": detalle})


@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def export_encuestas_excel(request):
    rows = services.get_datos_completos_para_export()
    if not rows:
        raise NotFound("No hay encuestas activas para exportar")

    for row in rows:
        if isinstance(row.get("alimentos_preferidos"), list):
            row["alimentos_preferidos"] = "; ".join(row["alimentos_preferidos"])

    df = pd.DataFrame(rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for municipio, group in df.groupby("municipio"):
            group.to_excel(writer, index=False, sheet_name=str(municipio)[:31])
        if writer.sheets:
            writer.book.active = 0
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = "attachment; filename=encuestas_nutricionales.xlsx"
    return response


# ---------------------------------------------------------------------------
# Encuesta detail / update / delete
# ---------------------------------------------------------------------------

@api_view(["GET", "PUT", "DELETE"])
def encuesta_detail(request, numero_encuesta: str):
    if request.method == "GET":
        encuesta = services.get_detail(numero_encuesta)
        if not encuesta:
            raise NotFound("Encuesta no encontrada")
        return Response(
            {"status": status.HTTP_200_OK, "message": "encuesta encontrada", "data": encuesta}
        )

    if request.method == "DELETE":
        deleted = services.soft_delete_encuesta(numero_encuesta)
        if not deleted:
            raise NotFound("Encuesta no encontrada")
        return Response({"status": status.HTTP_200_OK, "message": "encuesta eliminada"})

    if not services.get_by_numero(numero_encuesta):
        raise NotFound("Encuesta no encontrada")
    serializer = EncuestaNutricionalUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updated = services.update_encuesta(numero_encuesta, serializer.validated_data)
    if not updated:
        raise ParseError("Nada para actualizar")
    return Response({"status": status.HTTP_200_OK, "message": "encuesta actualizada"})


# ---------------------------------------------------------------------------
# Miembros
# ---------------------------------------------------------------------------

@api_view(["POST"])
def add_miembro(request, numero_encuesta: str):
    serializer = MiembroCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = services.add_miembro(numero_encuesta, serializer.validated_data)
    if not result:
        raise NotFound("Encuesta no encontrada")
    return Response(
        {"status": status.HTTP_201_CREATED, "message": "miembro registrado", "data": result},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "DELETE"])
def miembro_detail(request, numero_encuesta: str, miembro_id: int):
    encuesta = services.get_by_numero(numero_encuesta)
    if not encuesta:
        raise NotFound("Encuesta no encontrada")

    if request.method == "GET":
        miembro = services.get_miembro(encuesta.id, miembro_id)
        if not miembro:
            raise NotFound("Miembro no encontrado")
        return Response(
            {"status": status.HTTP_200_OK, "message": "miembro encontrado", "data": miembro}
        )

    if request.method == "DELETE":
        deleted = services.soft_delete_miembro(encuesta.id, miembro_id)
        if not deleted:
            raise NotFound("Miembro no encontrado")
        return Response({"status": status.HTTP_200_OK, "message": "miembro eliminado"})

    serializer = MiembroUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updated = services.update_miembro(encuesta.id, miembro_id, serializer.validated_data)
    if not updated:
        raise NotFound("Miembro no encontrado o sin cambios")
    return Response({"status": status.HTTP_200_OK, "message": "miembro actualizado"})
