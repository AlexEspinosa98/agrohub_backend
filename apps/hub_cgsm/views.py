import json
import uuid

from django.core.files.storage import default_storage
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.hub_cgsm.models import (
    EncuestaActor,
    EncuestaFaena,
    MonitoreoAmbiental,
    PuntoAcopioBiomasa,
)
from apps.hub_cgsm.serializers import (
    SERIALIZER_BY_TYPE,
    EncuestaActorSerializer,
    EncuestaFaenaSerializer,
    EncuestaPuntoAcopioSerializer,
)

MODEL_BY_TYPE = {
    "actores": EncuestaActor,
    "faena": EncuestaFaena,
    "acopio": PuntoAcopioBiomasa,
    "ambiental": MonitoreoAmbiental,
}

# The old FastAPI routes also accepted the Pydantic class names as an alias
# for survey_type (get_all's `type_map`) — kept for client compatibility.
TYPE_ALIASES = {
    "EncuestaActores": "actores",
    "EncuestaFaena": "faena",
    "EncuestaPuntoAcopio": "acopio",
    "EncuestaMonitoreoAmbiental": "ambiental",
}


def _resolve_type(survey_type):
    return TYPE_ALIASES.get(survey_type, survey_type)


def _instance_to_dict(instance) -> dict:
    data = {"id": instance.id}
    for field in instance._meta.fields:
        if field.name == "id":
            continue
        data[field.name] = getattr(instance, field.name)
    return data


def _save_upload(upload_file, subfolder: str) -> str:
    filename = f"{uuid.uuid4()}_{upload_file.name}"
    path = f"hub_cgsm/{subfolder}/{filename}"
    return default_storage.save(path, upload_file)


@extend_schema(
    methods=["GET"],
    tags=["hub-cgsm"],
    summary="Listar encuestas HUB CGSM de un tipo (actores/faena/acopio), con filtros y paginación",
    description="A diferencia de data-characterization, aquí `surveyType` es obligatorio — sin él devuelve `[]`.",
    parameters=[
        OpenApiParameter(
            "surveyType", str, OpenApiParameter.QUERY, required=True,
            description="También acepta los nombres Pydantic viejos como alias (EncuestaActores, EncuestaFaena, EncuestaPuntoAcopio, EncuestaMonitoreoAmbiental).",
            enum=["actores", "faena", "acopio", "ambiental"],
        ),
        OpenApiParameter("page", int, OpenApiParameter.QUERY, default=1),
        OpenApiParameter("page_size", int, OpenApiParameter.QUERY, default=10),
        OpenApiParameter("email", str, OpenApiParameter.QUERY, description="Filtra por email exacto."),
        OpenApiParameter("startDate", str, OpenApiParameter.QUERY, description="fecha_registro >= este valor (YYYY-MM-DD)."),
        OpenApiParameter("endDate", str, OpenApiParameter.QUERY, description="fecha_registro <= este valor (YYYY-MM-DD)."),
        OpenApiParameter("id", int, OpenApiParameter.QUERY, description="Filtra por id exacto."),
    ],
    responses={200: OpenApiResponse(description="Lista de encuestas del tipo pedido — campos según el serializer de ese tipo.")},
)
@extend_schema(
    methods=["POST"],
    tags=["hub-cgsm"],
    summary="[Legacy] valida y devuelve el body tal cual — no persiste nada",
    description=(
        "Port directo del endpoint FastAPI original: solo valida que estén los 9 campos "
        "requeridos y hace eco del body. Las 3 encuestas reales de HUB CGSM se guardan con los "
        "endpoints multipart de abajo (survey/actors, survey/faena, survey/punto-acopio)."
    ),
    request=inline_serializer("SurveyParametersCreate", {
        "email": serializers.CharField(),
        "date_aplication": serializers.CharField(),
        "ph": serializers.FloatField(),
        "salinity": serializers.FloatField(),
        "dissolved_oxygen": serializers.FloatField(),
        "conductivity": serializers.FloatField(),
        "temperature": serializers.FloatField(),
        "latitude": serializers.FloatField(),
        "longitude": serializers.FloatField(),
    }),
    responses={
        200: OpenApiResponse(description="Devuelve exactamente el body recibido."),
        400: OpenApiResponse(description="Falta alguno de los 9 campos requeridos."),
    },
)
@api_view(["GET", "POST"])
def surveys_list_create(request):
    if request.method == "POST":
        return _save_surveys_stub(request)
    return _get_all_surveys(request)


def _save_surveys_stub(request):
    """Port of the old `/hub-cgsm/surveys/` POST endpoint, which in the
    FastAPI backend just validated a (unrelated-looking) SurveyParametersCreate
    payload and echoed it back — it never persisted anything. Kept as-is for
    contract compatibility; the real survey-creation endpoints are the three
    multipart ones below."""
    required_fields = [
        "email",
        "date_aplication",
        "ph",
        "salinity",
        "dissolved_oxygen",
        "conductivity",
        "temperature",
        "latitude",
        "longitude",
    ]
    missing = [f for f in required_fields if f not in request.data]
    if missing:
        raise ValidationError({f: ["Este campo es obligatorio."] for f in missing})
    return Response(request.data)


def _get_all_surveys(request):
    params = request.query_params
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 10))
    email = params.get("email")
    survey_type = _resolve_type(params.get("surveyType"))
    start_date = params.get("startDate")
    end_date = params.get("endDate")
    survey_id = params.get("id")

    if not survey_type or survey_type not in MODEL_BY_TYPE:
        return Response([])

    model = MODEL_BY_TYPE[survey_type]
    qs = model.objects.all()
    if email:
        qs = qs.filter(email=email)
    if start_date:
        qs = qs.filter(fecha_registro__gte=start_date)
    if end_date:
        qs = qs.filter(fecha_registro__lte=end_date)
    if survey_id:
        qs = qs.filter(id=survey_id)
    offset = (page - 1) * page_size
    qs = qs.order_by("-fecha_registro")[offset : offset + page_size]
    return Response([_instance_to_dict(obj) for obj in qs])


@extend_schema(
    tags=["hub-cgsm"],
    summary="Actualizar (parcial) una encuesta HUB CGSM existente",
    description="`type` en el body decide el esquema (acepta los alias Pydantic viejos también). Campos no incluidos no se tocan.",
    request=EncuestaActorSerializer,  # forma base — el tipo real puede ser cualquiera de los 4, mismos campos que el serializer correspondiente
    responses={
        200: OpenApiResponse(description="Encuesta actualizada — devuelve el objeto completo."),
        404: OpenApiResponse(description="No existe una encuesta con ese id, o el body no trajo ningún campo actualizable."),
    },
)
@api_view(["PUT"])
def update_survey(request, id: int):
    survey_type = _resolve_type(request.data.get("type"))
    serializer_cls = SERIALIZER_BY_TYPE.get(survey_type)
    if not serializer_cls:
        raise ParseError(f"Tipo de encuesta inválido: {survey_type!r}")

    model = MODEL_BY_TYPE[survey_type]
    instance = model.objects.filter(id=id).first()
    if not instance:
        raise NotFound("Survey not found or update failed")

    serializer = serializer_cls(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    for excluded in ("id", "email", "fecha_registro", "type"):
        data.pop(excluded, None)
    if not data:
        raise NotFound("Survey not found or update failed")

    for key, value in data.items():
        setattr(instance, key, value)
    instance.save(update_fields=list(data.keys()))
    return Response(_instance_to_dict(instance))


@extend_schema(
    tags=["hub-cgsm"],
    summary="Guardar encuesta de Actor (multipart/form-data, con 2 fotos)",
    description=(
        "`survey_json` es un string con el JSON serializado de EncuestaActorSerializer (no un "
        "objeto anidado — el form-data solo transporta strings/archivos). Las 2 fotos son "
        "obligatorias. `id_actor`/`id_activo` se autogeneran (UUID) si no vienen en el JSON."
    ),
    request={
        "multipart/form-data": inline_serializer("ActorSurveyUpload", {
            "survey_json": serializers.CharField(
                help_text='JSON de EncuestaActorSerializer, ej: {"numero_identificacion":"123","nombre_codigo_activo":"Bote 1","autorizo_datos":true,"activos_bioseguridad":true, ...}',
            ),
            "fotografia_actor": serializers.FileField(),
            "fotografia_activo": serializers.FileField(),
        }),
    },
    responses={
        201: OpenApiResponse(
            response=inline_serializer("SavedMessage", {"message": serializers.CharField()}),
            examples=[OpenApiExample("OK", value={"message": "Actor survey saved successfully"})],
        ),
        400: OpenApiResponse(description="survey_json inválido/faltante, fotos faltantes, o error de validación de EncuestaActorSerializer."),
    },
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def save_actor_survey(request):
    try:
        survey_json = json.loads(request.data["survey_json"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ParseError("survey_json inválido o faltante") from exc

    serializer = EncuestaActorSerializer(data=survey_json)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    data.setdefault("id_actor", str(uuid.uuid4()))
    data.setdefault("id_activo", str(uuid.uuid4()))

    fotografia_actor = request.FILES.get("fotografia_actor")
    fotografia_activo = request.FILES.get("fotografia_activo")
    if not fotografia_actor or not fotografia_activo:
        raise ParseError("fotografia_actor y fotografia_activo son obligatorias")

    data["fotografia_actor"] = _save_upload(fotografia_actor, "actores")
    data["fotografia_activo"] = _save_upload(fotografia_activo, "actores")

    EncuestaActor.objects.update_or_create(id_actor=data["id_actor"], defaults=data)
    return Response({"message": "Actor survey saved successfully"}, status=201)


@extend_schema(
    tags=["hub-cgsm"],
    summary="Guardar encuesta de Faena (multipart/form-data, con 2 fotos)",
    description=(
        "`survey_json` es un string con el JSON serializado de EncuestaFaenaSerializer. Las 2 "
        "fotos (antes/después) son obligatorias. `id_faena` se autogenera (UUID) si no viene."
    ),
    request={
        "multipart/form-data": inline_serializer("FaenaSurveyUpload", {
            "survey_json": serializers.CharField(
                help_text='JSON de EncuestaFaenaSerializer, ej: {"superficie_intervenida":1.5,"numero_personas":6,"horas_trabajadas":4,"biomasa_humeda_kg":120,"numero_sacos":8,"punto_acopio_asociado":"PA-01","oxigeno_disuelto_mgL":5.2,"turbidez_NTU":3.1,"salinidad_prom":12.4, ...}',
            ),
            "fotografia_antes": serializers.FileField(),
            "fotografia_despues": serializers.FileField(),
        }),
    },
    responses={
        201: OpenApiResponse(
            response=inline_serializer("SavedMessage2", {"message": serializers.CharField()}),
            examples=[OpenApiExample("OK", value={"message": "Faena survey saved successfully"})],
        ),
        400: OpenApiResponse(description="survey_json inválido/faltante, fotos faltantes, o error de validación de EncuestaFaenaSerializer."),
    },
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def save_faena_survey(request):
    try:
        survey_json = json.loads(request.data["survey_json"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ParseError("survey_json inválido o faltante") from exc

    serializer = EncuestaFaenaSerializer(data=survey_json)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    data.setdefault("id_faena", str(uuid.uuid4()))

    fotografia_antes = request.FILES.get("fotografia_antes")
    fotografia_despues = request.FILES.get("fotografia_despues")
    if not fotografia_antes or not fotografia_despues:
        raise ParseError("fotografia_antes y fotografia_despues son obligatorias")

    data["fotografia_antes"] = _save_upload(fotografia_antes, "faenas")
    data["fotografia_despues"] = _save_upload(fotografia_despues, "faenas")

    EncuestaFaena.objects.update_or_create(id_faena=data["id_faena"], defaults=data)
    return Response({"message": "Faena survey saved successfully"}, status=201)


@extend_schema(
    tags=["hub-cgsm"],
    summary="Guardar Punto de Acopio de biomasa (multipart/form-data, con 1 foto)",
    description=(
        "`survey_json` es un string con el JSON serializado de EncuestaPuntoAcopioSerializer. "
        "La foto georreferenciada es obligatoria. Si `id_punto` viene en el JSON hace upsert "
        "(update_or_create); si no viene, siempre crea uno nuevo."
    ),
    request={
        "multipart/form-data": inline_serializer("PuntoAcopioSurveyUpload", {
            "survey_json": serializers.CharField(
                help_text='JSON de EncuestaPuntoAcopioSerializer, ej: {"nombre_referencia":"Muelle 2","tipo_punto":"fijo","ubicacion":"...", ...}',
            ),
            "fotografia_georreferenciada": serializers.FileField(),
        }),
    },
    responses={
        201: OpenApiResponse(
            response=inline_serializer("SavedMessage3", {"message": serializers.CharField()}),
            examples=[OpenApiExample("OK", value={"message": "Punto de Acopio survey saved successfully"})],
        ),
        400: OpenApiResponse(description="survey_json inválido/faltante, foto faltante, o error de validación de EncuestaPuntoAcopioSerializer."),
    },
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def save_punto_acopio_survey(request):
    try:
        survey_json = json.loads(request.data["survey_json"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ParseError("survey_json inválido o faltante") from exc

    serializer = EncuestaPuntoAcopioSerializer(data=survey_json)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)

    fotografia = request.FILES.get("fotografia_georreferenciada")
    if not fotografia:
        raise ParseError("fotografia_georreferenciada es obligatoria")
    data["fotografia_georreferenciada"] = _save_upload(fotografia, "puntos_acopio")

    if data.get("id_punto"):
        PuntoAcopioBiomasa.objects.update_or_create(id_punto=data["id_punto"], defaults=data)
    else:
        PuntoAcopioBiomasa.objects.create(**data)
    return Response({"message": "Punto de Acopio survey saved successfully"}, status=201)
