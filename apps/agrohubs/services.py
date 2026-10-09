import os
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.agrohubs.catalogos import VIDEO_EXTENSIONES, VIDEO_MAX_BYTES
from apps.agrohubs.models import AgroHub
from apps.asistencia_eventos.catalogos import normalizar_comunidad

_CAMPOS_ESCRIBIBLES = (
    "numero", "familias", "departamento", "municipio", "es_cabecera_municipal", "vereda",
    "asociaciones", "grupo_etnico", "comunidad", "cultivos", "latitud", "longitud",
)


def _limpiar(data: dict) -> dict:
    data = {k: v for k, v in data.items() if k in _CAMPOS_ESCRIBIBLES}
    if "numero" in data:
        data["numero"] = data["numero"].strip()
    if "vereda" in data:
        data["vereda"] = (data["vereda"] or "").strip() or None
    if "comunidad" in data:
        data["comunidad"] = normalizar_comunidad(data["comunidad"])
    if data.get("grupo_etnico") == "":
        data["grupo_etnico"] = None
    for campo in ("familias", "asociaciones", "cultivos"):
        if campo in data:
            data[campo] = [t.strip() for t in data[campo] if t and t.strip()]
    return data


def numero_en_uso(numero: str, excluir_id=None) -> bool:
    qs = AgroHub.objects.filter(numero__iexact=numero.strip())
    if excluir_id:
        qs = qs.exclude(id=excluir_id)
    return qs.exists()


def validar_video(upload) -> None:
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in VIDEO_EXTENSIONES:
        raise ValidationError({"video": f"Formato no permitido. Usa: {', '.join(VIDEO_EXTENSIONES)}"})
    if upload.size > VIDEO_MAX_BYTES:
        raise ValidationError({"video": f"El video supera el máximo de {VIDEO_MAX_BYTES // (1024 * 1024)} MB"})


def guardar_video(agrohub: AgroHub, upload) -> None:
    """Un solo video por AgroHub: subir uno nuevo reemplaza (y borra del disco) el anterior."""
    validar_video(upload)
    anterior = agrohub.video
    nombre = f"{uuid.uuid4()}_{os.path.basename(upload.name)}"
    agrohub.video = default_storage.save(f"agrohubs/{nombre}", upload)
    agrohub.save(update_fields=["video", "updated_at"])
    if anterior:
        default_storage.delete(anterior)


def quitar_video(agrohub: AgroHub) -> None:
    anterior = agrohub.video
    agrohub.video = None
    agrohub.save(update_fields=["video", "updated_at"])
    if anterior:
        default_storage.delete(anterior)


@transaction.atomic
def crear(data: dict, creado_por=None, video=None) -> AgroHub:
    if video:
        validar_video(video)
    data = _limpiar(data)
    agrohub = AgroHub.objects.create(creado_por=creado_por, **data)
    if video:
        guardar_video(agrohub, video)
    return agrohub


def actualizar(agrohub: AgroHub, data: dict, editado_por=None) -> AgroHub:
    for campo, valor in _limpiar(data).items():
        setattr(agrohub, campo, valor)
    agrohub.editado_por = editado_por
    agrohub.save()
    return agrohub


def eliminar(agrohub: AgroHub) -> None:
    video = agrohub.video
    agrohub.delete()
    if video:
        default_storage.delete(video)


def filtrar_puntos(params):
    qs = AgroHub.objects.all()
    if params.get("departamento"):
        qs = qs.filter(departamento__iexact=params["departamento"])
    if params.get("municipio"):
        qs = qs.filter(municipio__iexact=params["municipio"])
    if params.get("grupo_etnico"):
        qs = qs.filter(grupo_etnico=params["grupo_etnico"])
    lista = list(qs.order_by("numero"))
    cultivo = (params.get("cultivo") or "").strip().lower()
    if cultivo:
        lista = [a for a in lista if any(c.lower() == cultivo for c in a.cultivos)]
    return lista


def valores_usados(campo: str) -> list:
    """Valores de texto libre ya usados en listas (autocompletar), sin repetir ni distinguir
    mayúsculas; conserva la primera escritura vista."""
    vistos = {}
    for lista in AgroHub.objects.values_list(campo, flat=True):
        for item in lista or []:
            vistos.setdefault(item.lower(), item)
    return sorted(vistos.values(), key=str.lower)
