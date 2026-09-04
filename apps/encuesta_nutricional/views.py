import io

import pandas as pd
from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
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


def _envelope(data_field=None, message_example="ok"):
    """Forma común de todas las respuestas de esta app: {status, message, data?}."""
    fields = {
        "status": serializers.IntegerField(),
        "message": serializers.CharField(),
    }
    if data_field is not None:
        fields["data"] = data_field
    return inline_serializer(f"Envelope{message_example.title().replace(' ', '')}", fields)


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


_PERSONA_FIELDS = inline_serializer("PersonaNutricional", {
    "id": serializers.IntegerField(), "cedula": serializers.CharField(),
    "nombre": serializers.CharField(), "edad_anios": serializers.IntegerField(allow_null=True),
    "sexo": serializers.CharField(allow_null=True), "area_residencia": serializers.CharField(allow_null=True),
    "nivel_educativo": serializers.CharField(allow_null=True), "is_active": serializers.BooleanField(),
    "created_at": serializers.DateTimeField(), "updated_at": serializers.DateTimeField(),
})

_TOKEN_AUTH_NOTE = "Requiere `Authorization: Token <token>` (login vía POST /user-activity/users/login) y rol habilitado."


# ---------------------------------------------------------------------------
# Personas nutricionales
# ---------------------------------------------------------------------------

@extend_schema(
    methods=["GET"],
    tags=["encuesta-nutricional"],
    summary="Buscar participante por cédula",
    description="`value` aquí es la cédula (string) — distinto del PUT, que espera el id numérico interno.",
    responses={
        200: OpenApiResponse(response=_envelope(_PERSONA_FIELDS, "persona ok")),
        404: OpenApiResponse(description="No hay un participante activo con esa cédula."),
    },
)
@extend_schema(
    methods=["PUT"],
    tags=["encuesta-nutricional"],
    summary="Actualizar (parcial) un participante por id",
    description="Aquí `value` es el id numérico interno (no la cédula) — debe poder convertirse a int.",
    request=PersonaNutricionalUpdateSerializer,
    responses={
        200: OpenApiResponse(response=_envelope(message_example="update ok")),
        404: OpenApiResponse(description="`value` no es un id numérico válido, o no existe / no hubo cambios."),
    },
)
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

@extend_schema(
    methods=["GET"],
    tags=["encuesta-nutricional"],
    summary="Listar encuestas de hogar, con filtros y paginación",
    parameters=[
        OpenApiParameter("nombre_encuestador", str, OpenApiParameter.QUERY),
        OpenApiParameter("municipio", str, OpenApiParameter.QUERY),
        OpenApiParameter("vereda_comunidad", str, OpenApiParameter.QUERY),
        OpenApiParameter("numero_encuesta", str, OpenApiParameter.QUERY),
        OpenApiParameter("cedula_encuestador", str, OpenApiParameter.QUERY),
        OpenApiParameter("page", int, OpenApiParameter.QUERY, default=1),
        OpenApiParameter("page_size", int, OpenApiParameter.QUERY, default=50),
    ],
    responses={200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="array de encuestas — mismo shape que el detalle de una encuesta individual"), "list ok"), description="`data` es un array de encuestas — el detalle exacto de cada una está en el response de GET /encuesta-nutricional/{numero_encuesta}.")},
)
@extend_schema(
    methods=["POST"],
    tags=["encuesta-nutricional"],
    summary="Crear una encuesta de hogar (con sus miembros)",
    description="`miembros` es obligatorio y no puede venir vacío — cada elemento es un MiembroCreateSerializer completo.",
    request=EncuestaNutricionalCreateSerializer,
    examples=[OpenApiExample("Encuesta con 2 miembros", value={
        "nombre_encuestador": "Laura Torres", "cedula_encuestador": "1082912345",
        "fecha_aplicacion": "2026-03-15", "municipio": "Fundación", "vereda_comunidad": "El Reten",
        "num_personas_hogar": 4, "consentimiento_informado": True,
        "dias_cereales_tuberculos": 7, "dias_leguminosas": 3, "dias_carnes_pescado_huevo": 5,
        "dias_lacteos": 6, "dias_frutas": 4, "dias_verduras": 5, "dias_grasas": 7,
        "dias_azucares_ultraprocesados": 2,
        "miembros": [
            {"nombre_participante": "Juan Gómez", "edad_anios": 34, "sexo": "M", "peso_kg": 72.5, "talla_cm": 170},
            {"nombre_participante": "Ana Gómez", "edad_anios": 8, "sexo": "F", "peso_kg": 25.0, "talla_cm": 128},
        ],
    }, request_only=True)],
    responses={201: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="la encuesta creada, incluido numero_encuesta autogenerado"), "create ok"), description="`data` trae la encuesta creada, incluido `numero_encuesta` autogenerado.")},
)
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

@extend_schema(
    tags=["encuesta-nutricional"],
    summary="Resumen agregado por municipio (público, sin auth)",
    responses={200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="array de {municipio, total_encuestas, ...métricas agregadas}"), "resumen municipios"))},
)
@api_view(["GET"])
def dashboard_municipios(request):
    items = services.get_resumen_por_municipio()
    return Response({"status": status.HTTP_200_OK, "message": "resumen generado", "data": items})


@extend_schema(
    tags=["encuesta-nutricional"],
    summary="Resumen agregado por vereda de un municipio",
    description=_TOKEN_AUTH_NOTE,
    parameters=[OpenApiParameter("municipio", str, OpenApiParameter.QUERY)],
    responses={200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="array de {vereda_comunidad, total_encuestas, ...métricas agregadas}"), "resumen veredas")), 401: OpenApiResponse(description="Token ausente/inválido.")},
    auth=["TokenAuth"],
)
@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def dashboard_veredas(request):
    items = services.get_resumen_por_vereda(municipio=request.query_params.get("municipio"))
    return Response({"status": status.HTTP_200_OK, "message": "resumen generado", "data": items})


@extend_schema(
    tags=["encuesta-nutricional"],
    summary="Detalle estadístico de un municipio",
    description=_TOKEN_AUTH_NOTE,
    responses={
        200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="métricas y agregados detallados del municipio"), "detalle municipio")),
        401: OpenApiResponse(description="Token ausente/inválido."),
        404: OpenApiResponse(description="No hay encuestas activas para ese municipio."),
    },
    auth=["TokenAuth"],
)
@api_view(["GET"])
@authentication_classes([TokenHeaderAuthentication])
@permission_classes([IsAuthenticatedWithRole])
def dashboard_detalle_municipio(request, municipio: str):
    detalle = services.get_detalle_municipio(municipio)
    if not detalle:
        raise NotFound("No hay encuestas activas para ese municipio")
    return Response({"status": status.HTTP_200_OK, "message": "detalle generado", "data": detalle})


@extend_schema(
    tags=["encuesta-nutricional"],
    summary="Exportar todas las encuestas activas a Excel (un sheet por municipio)",
    description=_TOKEN_AUTH_NOTE,
    responses={
        200: OpenApiResponse(
            description="Archivo .xlsx (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet), descarga directa.",
        ),
        401: OpenApiResponse(description="Token ausente/inválido."),
        404: OpenApiResponse(description="No hay encuestas activas para exportar."),
    },
    auth=["TokenAuth"],
)
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

@extend_schema(
    methods=["GET"],
    tags=["encuesta-nutricional"],
    summary="Detalle completo de una encuesta (con sus miembros)",
    responses={200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="la encuesta completa, con su array de miembros"), "encuesta detalle")), 404: OpenApiResponse(description="No existe esa encuesta.")},
)
@extend_schema(
    methods=["DELETE"],
    tags=["encuesta-nutricional"],
    summary="Baja lógica de una encuesta (soft delete)",
    responses={200: OpenApiResponse(response=_envelope(message_example="encuesta eliminada")), 404: OpenApiResponse(description="No existe esa encuesta.")},
)
@extend_schema(
    methods=["PUT"],
    tags=["encuesta-nutricional"],
    summary="Actualizar (parcial) una encuesta",
    request=EncuestaNutricionalUpdateSerializer,
    responses={
        200: OpenApiResponse(response=_envelope(message_example="encuesta actualizada")),
        400: OpenApiResponse(description="El body no trajo ningún campo para actualizar."),
        404: OpenApiResponse(description="No existe esa encuesta."),
    },
)
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

@extend_schema(
    tags=["encuesta-nutricional"],
    summary="Agregar un miembro a una encuesta existente",
    request=MiembroCreateSerializer,
    responses={
        201: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="el miembro creado"), "miembro registrado")),
        404: OpenApiResponse(description="No existe esa encuesta."),
    },
)
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


@extend_schema(
    methods=["GET"],
    tags=["encuesta-nutricional"],
    summary="Detalle de un miembro de una encuesta",
    responses={200: OpenApiResponse(response=_envelope(serializers.JSONField(help_text="el miembro completo"), "miembro detalle")), 404: OpenApiResponse(description="No existe la encuesta, o no existe ese miembro dentro de ella.")},
)
@extend_schema(
    methods=["DELETE"],
    tags=["encuesta-nutricional"],
    summary="Baja lógica de un miembro (soft delete)",
    responses={200: OpenApiResponse(response=_envelope(message_example="miembro eliminado")), 404: OpenApiResponse(description="No existe la encuesta, o no existe ese miembro.")},
)
@extend_schema(
    methods=["PUT"],
    tags=["encuesta-nutricional"],
    summary="Actualizar (parcial) un miembro",
    request=MiembroUpdateSerializer,
    responses={
        200: OpenApiResponse(response=_envelope(message_example="miembro actualizado")),
        404: OpenApiResponse(description="No existe la encuesta/miembro, o el body no trajo cambios."),
    },
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
