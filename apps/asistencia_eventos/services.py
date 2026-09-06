from django.db import transaction

from apps.asistencia_eventos.models import Evento, PersonaAsistente, RegistroAsistencia

_RANGOS_EDAD = [("0-14", 0, 14), ("15-19", 15, 19), ("20-59", 20, 59), ("mayor de 60", 60, None)]


def _upsert_persona(numero_documento, tipo_documento, nombre, genero, pertenencia_etnica) -> PersonaAsistente:
    """Inserta o actualiza una persona por número de documento — mismo
    patrón que PersonaNutricional en encuesta_nutricional: un documento,
    un único registro de persona, sin importar en cuántos eventos aparezca."""
    incoming = {
        "tipo_documento": tipo_documento,
        "nombre": nombre,
        "genero": genero,
        "pertenencia_etnica": pertenencia_etnica,
    }
    persona, created = PersonaAsistente.objects.get_or_create(
        numero_documento=numero_documento, defaults=incoming
    )
    if not created:
        changed_fields = []
        for field, value in incoming.items():
            if value is not None:
                setattr(persona, field, value)
                changed_fields.append(field)
        if changed_fields:
            persona.save(update_fields=changed_fields)
    return persona


@transaction.atomic
def guardar_evento(data: dict, documento_escaneado: str | None, texto_crudo_ocr: str | None) -> Evento:
    evento = Evento.objects.create(
        tema=data["tema"],
        responsable=data.get("responsable"),
        lugar=data.get("lugar"),
        fecha=data.get("fecha"),
        hora_inicio=data.get("hora_inicio"),
        hora_final=data.get("hora_final"),
        documento_escaneado=documento_escaneado,
        texto_crudo_ocr=texto_crudo_ocr,
    )
    for row in data["asistentes"]:
        persona = _upsert_persona(
            numero_documento=row["numero_documento"],
            tipo_documento=row.get("tipo_documento"),
            nombre=row.get("nombre"),
            genero=row.get("genero"),
            pertenencia_etnica=row.get("pertenencia_etnica"),
        )
        RegistroAsistencia.objects.update_or_create(
            evento=evento,
            persona=persona,
            defaults={
                "municipio": row.get("municipio"),
                "telefono": row.get("telefono"),
                "edad": row.get("edad"),
            },
        )
    return evento


def resumen_general() -> dict:
    return {
        "total_personas": PersonaAsistente.objects.count(),
        "total_eventos": Evento.objects.count(),
        "total_asistencias": RegistroAsistencia.objects.count(),
    }


def _rango_edad(edad):
    if edad is None:
        return None
    for label, lo, hi in _RANGOS_EDAD:
        if edad >= lo and (hi is None or edad <= hi):
            return label
    return None


def estadisticas_por_municipio(evento_id=None) -> list:
    """Tabla dinámica Municipio x Género x rango de edad, igual al reporte
    de estadísticas del proyecto (columnas 0-14 / 15-19 / 20-59 / mayor de
    60 + Total, con fila Total al final)."""
    qs = RegistroAsistencia.objects.select_related("persona").all()
    if evento_id:
        qs = qs.filter(evento_id=evento_id)

    labels = [r[0] for r in _RANGOS_EDAD]
    buckets = {}
    for reg in qs:
        genero = reg.persona.genero
        if genero not in ("M", "F"):
            continue
        rango = _rango_edad(reg.edad)
        if not rango:
            continue
        municipio = reg.municipio or "Sin municipio"
        key = (municipio, "Masculino" if genero == "M" else "Femenino")
        buckets.setdefault(key, {label: 0 for label in labels})
        buckets[key][rango] += 1

    municipios = sorted({k[0] for k in buckets})
    filas = []
    totales_columna = {label: 0 for label in labels}
    total_general = 0
    for municipio in municipios:
        for genero_label in ("Masculino", "Femenino"):
            conteos = buckets.get((municipio, genero_label), {label: 0 for label in labels})
            total_fila = sum(conteos.values())
            filas.append({"municipio": municipio, "genero": genero_label, **conteos, "total": total_fila})
            for label in labels:
                totales_columna[label] += conteos[label]
            total_general += total_fila

    filas.append({"municipio": "Total", "genero": None, **totales_columna, "total": total_general})
    return filas


def eventos_para_export(evento_id=None) -> list:
    qs = Evento.objects.order_by("-fecha", "-id")
    if evento_id:
        qs = qs.filter(id=evento_id)
    return [
        {
            "id": e.id,
            "tema": e.tema,
            "responsable": e.responsable,
            "lugar": e.lugar,
            "fecha": e.fecha,
            "hora_inicio": e.hora_inicio,
            "hora_final": e.hora_final,
            "total_asistentes": e.asistentes.count(),
        }
        for e in qs
    ]


def asistentes_para_export(evento_id=None) -> list:
    qs = RegistroAsistencia.objects.select_related("persona", "evento").order_by(
        "-evento__fecha", "evento_id", "persona__nombre"
    )
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    return [
        {
            "evento_id": r.evento_id,
            "evento_tema": r.evento.tema,
            "evento_fecha": r.evento.fecha,
            "nombre": r.persona.nombre,
            "tipo_documento": r.persona.tipo_documento,
            "numero_documento": r.persona.numero_documento,
            "genero": r.persona.genero,
            "pertenencia_etnica": r.persona.pertenencia_etnica,
            "municipio": r.municipio,
            "telefono": r.telefono,
            "edad": r.edad,
        }
        for r in qs
    ]
