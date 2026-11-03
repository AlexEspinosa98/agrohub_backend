"""Relación gateway (riego_iot, Postgres) <-> AgroHub (default, MySQL). No hay FK entre las dos
bases: el AgroHub guarda el `device_id` y esta capa lo resuelve en ambos sentidos."""
from apps.agrohubs.models import AgroHub


def _resumen(a: AgroHub) -> dict:
    return {"id": a.id, "numero": a.numero, "nombre": a.nombre, "municipio": a.municipio}


def agrohubs_por_dispositivo(device_ids=None) -> dict:
    """{device_id: {id, numero, nombre, municipio}} de los gateways montados en un AgroHub."""
    qs = AgroHub.objects.exclude(dispositivo__isnull=True).exclude(dispositivo="")
    if device_ids is not None:
        qs = qs.filter(dispositivo__in=list(device_ids))
    return {a.dispositivo: _resumen(a) for a in qs}
