from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ParseError, ValidationError
from rest_framework.response import Response

from apps.data_characterization.models import (
    EncuestaAgrohub,
    EncuestaDerechoHumanoAlimentario,
    EncuestaEducativa,
)
from apps.data_characterization.serializers import (
    SERIALIZER_BY_TYPE,
    AgrohubSurveySerializer,
    SurveyListRequestSerializer,
)

MODEL_BY_TYPE = {
    "agrohub": EncuestaAgrohub,
    "educativa": EncuestaEducativa,
    "derecho_humano_alimentario": EncuestaDerechoHumanoAlimentario,
}


def _instance_to_dict(instance) -> dict:
    data = {"id": instance.id, "type": instance.SURVEY_TYPE}
    for field in instance._meta.fields:
        if field.name == "id":
            continue
        data[field.name] = getattr(instance, field.name)
    return data


def _apply_filters(qs, email, start_date, end_date, survey_id):
    if email:
        qs = qs.filter(email=email)
    if start_date:
        qs = qs.filter(fecha_creacion__gte=start_date)
    if end_date:
        qs = qs.filter(fecha_creacion__lte=end_date)
    if survey_id:
        qs = qs.filter(id=survey_id)
    return qs


def _fetch_type(model, page, page_size, email, start_date, end_date, survey_id):
    qs = _apply_filters(model.objects.all(), email, start_date, end_date, survey_id)
    offset = (page - 1) * page_size
    qs = qs.order_by("-fecha_creacion")[offset : offset + page_size]
    return [_instance_to_dict(obj) for obj in qs]


# --- ejemplos reales de cada tipo de encuesta, reusados en POST y PUT ---
_EXAMPLE_AGROHUB = {
    "type": "agrohub",
    "email": "aplicador@unimagdalena.edu.co",
    "nombre_aplicador": "Ana Pérez",
    "fecha_aplicacion": "2026-03-10",
    "municipio": "Santa Marta",
    "vereda": "Bonda",
    "nombre_organizacion": "Asociación de Productores Bonda",
    "tipo_organizacion": "Asociación",
    "anio_conformacion": 2015,
    "numero_miembros": 24,
    "numero_nucleos_familiares": 18,
    "cultivan_hortalizas": "si",
    "area_hortalizas": 2,
    "latitud": "11.2408",
    "longitud": "-74.1990",
}
_EXAMPLE_EDUCATIVA = {
    "type": "educativa",
    "email": "aplicador@unimagdalena.edu.co",
    "nombre_aplicador": "Carlos Ruiz",
    "fecha_aplicacion": "2026-03-10",
    "municipio": "Ciénaga",
    "vereda": "Cordobita",
    "nombre_institucion": "IE Rural Cordobita",
    "codigo_dane": "247189000123",
    "numero_estudiantes": 340,
    "numero_docentes": 15,
    "tiene_prae": True,
    "tiene_huerta": True,
    "area_huerta": 1,
    "latitud": "10.9908",
    "longitud": "-74.2967",
}
_EXAMPLE_DHA = {
    "type": "derecho_humano_alimentario",
    "email": "aplicador@unimagdalena.edu.co",
    "fecha_aplicacion": "2026-03-10",
    "nombre_jefe_hogar": "María Gómez",
    "edad": 45,
    "genero": "femenino",
    "departamento": "Magdalena",
    "municipio": "Aracataca",
    "numero_miembros_hogar": 5,
    "dedicado_agricultura": True,
    "cultivos_principales": "yuca, plátano",
    "cobertura_necesidades": False,
    "meses_escasez": "junio-agosto",
}

_SURVEY_LIST_EXAMPLE = OpenApiExample(
    "Lote con los 3 tipos de encuesta",
    summary="POST /surveys/ — un email, varias encuestas de distinto tipo en un solo lote",
    description=(
        "`surveys[].type` decide contra cuál de los 3 esquemas se valida cada elemento: "
        "`agrohub` (AgrohubSurveySerializer), `educativa` (EducativaSurveySerializer) o "
        "`derecho_humano_alimentario` (DerechoHumanoAlimentarioSurveySerializer). Todos los "
        "campos salvo `type`/`email`/`fecha_aplicacion` son opcionales."
    ),
    value={
        "email": "aplicador@unimagdalena.edu.co",
        "surveys": [_EXAMPLE_AGROHUB, _EXAMPLE_EDUCATIVA, _EXAMPLE_DHA],
    },
    request_only=True,
)


@extend_schema(
    methods=["GET"],
    tags=["data-characterization"],
    summary="Listar encuestas de caracterización (los 3 tipos, con filtros y paginación)",
    parameters=[
        OpenApiParameter("page", int, OpenApiParameter.QUERY, description="Página, 1-indexada.", default=1),
        OpenApiParameter("page_size", int, OpenApiParameter.QUERY, description="Tamaño de página.", default=10),
        OpenApiParameter(
            "surveyType", str, OpenApiParameter.QUERY,
            description="Filtra a un solo tipo. Si se omite, junta los 3 tipos ordenados por fecha_creacion.",
            enum=["agrohub", "educativa", "derecho_humano_alimentario"],
        ),
        OpenApiParameter("email", str, OpenApiParameter.QUERY, description="Filtra por email exacto del aplicador."),
        OpenApiParameter("startDate", str, OpenApiParameter.QUERY, description="fecha_creacion >= este valor (YYYY-MM-DD)."),
        OpenApiParameter("endDate", str, OpenApiParameter.QUERY, description="fecha_creacion <= este valor (YYYY-MM-DD)."),
        OpenApiParameter("id", int, OpenApiParameter.QUERY, description="Filtra por id exacto de la encuesta."),
    ],
    responses={200: OpenApiResponse(
        response=inline_serializer("SurveyListItem", {
            "id": serializers.IntegerField(),
            "type": serializers.ChoiceField(choices=["agrohub", "educativa", "derecho_humano_alimentario"]),
        }),
        description="Lista de encuestas — cada objeto trae `id`, `type` y todos los campos propios de ese tipo (ver los 3 serializers).",
    )},
)
@extend_schema(
    methods=["POST"],
    tags=["data-characterization"],
    summary="Guardar un lote de encuestas (una o varias, de cualquiera de los 3 tipos)",
    description=(
        "Todo-o-nada: si cualquier elemento de `surveys` falla su validación, no se guarda "
        "ninguno y el 400 devuelve los errores por índice en `surveys.<i>.<campo>`."
    ),
    request=SurveyListRequestSerializer,
    examples=[_SURVEY_LIST_EXAMPLE],
    responses={
        201: OpenApiResponse(
            response=inline_serializer("SurveysSavedResponse", {"message": serializers.CharField()}),
            description="Todas las encuestas del lote se guardaron.",
            examples=[OpenApiExample("OK", value={"message": "Surveys saved successfully"})],
        ),
        400: OpenApiResponse(description="Errores de validación, uno por índice de `surveys`."),
    },
)
@api_view(["GET", "POST"])
def surveys_list_create(request):
    if request.method == "POST":
        return _save_surveys(request)
    return _get_all_surveys(request)


def _save_surveys(request):
    serializer = SurveyListRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    raw_surveys = serializer.validated_data["surveys"]

    # Validate every item first (collecting per-index errors so a 422 points
    # at "surveys.<i>.<campo>", same shape a nested many=True serializer
    # error would produce) before writing anything.
    to_create = []
    per_survey_errors = []
    has_errors = False
    for raw in raw_surveys:
        survey_type = raw.get("type")
        item_serializer_cls = SERIALIZER_BY_TYPE.get(survey_type)
        if not item_serializer_cls:
            per_survey_errors.append({"type": ["Tipo de encuesta inválido."]})
            has_errors = True
            continue
        item_serializer = item_serializer_cls(data={**raw, "email": email})
        if not item_serializer.is_valid():
            per_survey_errors.append(item_serializer.errors)
            has_errors = True
            continue
        per_survey_errors.append({})
        data = dict(item_serializer.validated_data)
        data.pop("type", None)
        to_create.append((MODEL_BY_TYPE[survey_type], data))

    if has_errors:
        raise ValidationError({"surveys": per_survey_errors})

    for model, data in to_create:
        model.objects.create(**data)

    return Response({"message": "Surveys saved successfully"}, status=201)


def _get_all_surveys(request):
    params = request.query_params
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 10))
    email = params.get("email")
    survey_type = params.get("surveyType")
    start_date = params.get("startDate")
    end_date = params.get("endDate")
    survey_id = params.get("id")

    if survey_type:
        model = MODEL_BY_TYPE.get(survey_type)
        if not model:
            return Response([])
        return Response(_fetch_type(model, page, page_size, email, start_date, end_date, survey_id))

    results = []
    for model in MODEL_BY_TYPE.values():
        results += _fetch_type(model, page, page_size, email, start_date, end_date, survey_id)
    results.sort(key=lambda r: r.get("fecha_creacion"), reverse=True)
    return Response(results)


@extend_schema(
    tags=["data-characterization"],
    summary="Actualizar (parcial) una encuesta existente",
    description=(
        "`type` en el body determina contra cuál de los 3 esquemas se valida — debe coincidir "
        "con el tipo real de la encuesta con ese `id`. Cualquier campo del tipo correspondiente "
        "es aceptado como actualización parcial; `id`/`type`/`fecha_creacion` se ignoran si vienen."
    ),
    request=AgrohubSurveySerializer,  # forma base — ver los 3 examples de abajo para educativa/derecho_humano_alimentario
    examples=[
        OpenApiExample("agrohub", value=_EXAMPLE_AGROHUB, request_only=True),
        OpenApiExample("educativa", value=_EXAMPLE_EDUCATIVA, request_only=True),
        OpenApiExample("derecho_humano_alimentario", value=_EXAMPLE_DHA, request_only=True),
    ],
    responses={
        200: OpenApiResponse(description="Encuesta actualizada — devuelve el objeto completo con los nuevos valores."),
        404: OpenApiResponse(description="No existe una encuesta con ese id (o el body no trajo ningún campo válido para actualizar)."),
    },
)
@api_view(["PUT"])
def update_survey(request, id: int):
    survey_type = request.data.get("type")
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
    data.pop("type", None)
    data.pop("id", None)
    data.pop("fecha_creacion", None)
    if not data:
        raise NotFound("Survey not found or update failed")

    for key, value in data.items():
        setattr(instance, key, value)
    instance.save(update_fields=list(data.keys()))
    return Response(_instance_to_dict(instance))


@extend_schema(
    tags=["data-characterization"],
    summary="Puntos geográficos de las 3 encuestas (para el mapa)",
    description="Sin filtros ni paginación — junta las 3 tablas, solo filas con latitud/longitud no vacías.",
    responses={200: OpenApiResponse(
        response=inline_serializer("SurveyLocation", {
            "type": serializers.ChoiceField(choices=["agrohub", "instituciones educativas", "caracterizacion agro-alimentaria"]),
            "latitud": serializers.CharField(),
            "longitud": serializers.CharField(),
            "municipio": serializers.CharField(allow_null=True),
            "fecha_aplicacion": serializers.DateField(allow_null=True),
        }),
    )},
)
@api_view(["GET"])
def get_all_locations(request):
    results = []
    type_labels = {
        EncuestaAgrohub: "agrohub",
        EncuestaEducativa: "instituciones educativas",
        EncuestaDerechoHumanoAlimentario: "caracterizacion agro-alimentaria",
    }
    for model, label in type_labels.items():
        qs = model.objects.exclude(latitud__isnull=True).exclude(latitud="").exclude(
            longitud__isnull=True
        ).exclude(longitud="")
        for obj in qs:
            results.append(
                {
                    "type": label,
                    "latitud": obj.latitud,
                    "longitud": obj.longitud,
                    "municipio": obj.municipio,
                    "fecha_aplicacion": obj.fecha_aplicacion,
                }
            )
    return Response(results)
