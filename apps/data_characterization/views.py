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
