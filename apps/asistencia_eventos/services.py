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
def guardar_evento(
    data: dict,
    documento_escaneado: str | None,
    texto_crudo_ocr: str | None,
    registrado_por=None,
) -> Evento:
    evento = Evento.objects.create(
        tema=data["tema"],
        responsable=data.get("responsable"),
        lugar=data.get("lugar"),
        fecha=data.get("fecha"),
        hora_inicio=data.get("hora_inicio"),
        hora_final=data.get("hora_final"),
        documento_escaneado=documento_escaneado,
        texto_crudo_ocr=texto_crudo_ocr,
        registrado_por=registrado_por,
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


_CAMPOS_EVENTO_EDITABLES = ("tema", "responsable", "lugar", "fecha", "hora_inicio", "hora_final")


def actualizar_evento_header(evento: Evento, data: dict, editado_por=None) -> Evento:
    """Corrige los datos del encabezado del evento — solo toca los campos que
    vienen en `data` (edición parcial), sin tocar su lista de asistentes."""
    for campo in _CAMPOS_EVENTO_EDITABLES:
        if campo in data:
            setattr(evento, campo, data[campo])
    evento.editado_por = editado_por
    evento.save()
    return evento


def eliminar_evento(evento: Evento) -> None:
    """Borra el evento y en cascada sus registros de asistencia (RegistroAsistencia
    tiene on_delete=CASCADE). Las personas en PersonaAsistente NO se tocan — es la
    tabla maestra compartida entre eventos."""
    evento.delete()


_CAMPOS_PERSONA_EDITABLES = ("tipo_documento", "nombre", "genero", "pertenencia_etnica")


def actualizar_persona(persona: PersonaAsistente, data: dict) -> PersonaAsistente:
    """Corrige la ficha maestra de una persona (ej. el OCR leyó mal el nombre) —
    solo toca los campos que vienen en `data`. No afecta sus registros de
    asistencia en los eventos donde ya participó."""
    changed_fields = [campo for campo in _CAMPOS_PERSONA_EDITABLES if campo in data]
    for campo in changed_fields:
        setattr(persona, campo, data[campo])
    if changed_fields:
        persona.save(update_fields=changed_fields)
    return persona


def eliminar_persona(persona: PersonaAsistente) -> None:
    """Elimina a la persona por completo, en cascada con su participación en
    todos los eventos donde aparece (RegistroAsistencia.persona es CASCADE) —
    es la operación más amplia de las tres de edición/eliminación."""
    persona.delete()


def eventos_de_persona(persona: PersonaAsistente) -> list:
    qs = RegistroAsistencia.objects.select_related("evento").filter(persona=persona).order_by(
        "-evento__fecha", "-evento_id"
    )
    return [
        {
            "evento_id": r.evento_id,
            "tema": r.evento.tema,
            "fecha": r.evento.fecha,
            "municipio": r.municipio,
            "telefono": r.telefono,
            "edad": r.edad,
        }
        for r in qs
    ]


_CAMPOS_ASISTENCIA_EDITABLES = ("municipio", "telefono", "edad")


def actualizar_registro_asistencia(registro: RegistroAsistencia, data: dict) -> RegistroAsistencia:
    """Corrige la participación de una persona en un evento puntual (municipio/
    teléfono/edad de esa asistencia específica) sin tocar su ficha maestra ni el
    resto del evento — la operación más quirúrgica de las tres."""
    changed_fields = [campo for campo in _CAMPOS_ASISTENCIA_EDITABLES if campo in data]
    for campo in changed_fields:
        setattr(registro, campo, data[campo])
    if changed_fields:
        registro.save(update_fields=changed_fields)
    return registro


def eliminar_registro_asistencia(registro: RegistroAsistencia) -> None:
    """Retira a esa persona de ese evento puntual, sin tocar su ficha maestra
    (PersonaAsistente) ni su participación en otros eventos."""
    registro.delete()


def resumen_general(usuario=None) -> dict:
    """usuario=None (superadmin) -> totales de todo el sistema. Para cualquier otro rol, se pasa
    el usuario que consulta y todo se acota a los eventos que ÉL registró — total_personas cuenta
    personas DISTINTAS dentro de esos eventos (no el total de la tabla maestra compartida, que
    incluye gente registrada por otros usuarios)."""
    eventos = Evento.objects.all() if usuario is None else Evento.objects.filter(registrado_por=usuario)
    registros = RegistroAsistencia.objects.all() if usuario is None else RegistroAsistencia.objects.filter(
        evento__registrado_por=usuario
    )
    personas = (
        PersonaAsistente.objects.count()
        if usuario is None
        else PersonaAsistente.objects.filter(asistencias__evento__registrado_por=usuario).distinct().count()
    )
    return {
        "total_personas": personas,
        "total_eventos": eventos.count(),
        "total_asistencias": registros.count(),
    }


def _rango_edad(edad):
    if edad is None:
        return None
    for label, lo, hi in _RANGOS_EDAD:
        if edad >= lo and (hi is None or edad <= hi):
            return label
    return None


def estadisticas_por_municipio(evento_id=None, usuario=None) -> list:
    """Tabla dinámica Municipio x Género x rango de edad, igual al reporte
    de estadísticas del proyecto (columnas 0-14 / 15-19 / 20-59 / mayor de
    60 + Total, con fila Total al final). usuario=None (superadmin) -> todo el
    sistema; cualquier otro rol solo ve sus propios eventos."""
    qs = RegistroAsistencia.objects.select_related("persona").all()
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    if usuario is not None:
        qs = qs.filter(evento__registrado_por=usuario)

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


def eventos_para_export(evento_id=None, usuario=None) -> list:
    qs = Evento.objects.select_related("registrado_por", "editado_por").order_by("-fecha", "-id")
    if evento_id:
        qs = qs.filter(id=evento_id)
    if usuario is not None:
        qs = qs.filter(registrado_por=usuario)
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
            "registrado_por": e.registrado_por.name if e.registrado_por else None,
            "editado_por": e.editado_por.name if e.editado_por else None,
        }
        for e in qs
    ]


def asistentes_para_export(evento_id=None, usuario=None) -> list:
    qs = RegistroAsistencia.objects.select_related("persona", "evento").order_by(
        "-evento__fecha", "evento_id", "persona__nombre"
    )
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    if usuario is not None:
        qs = qs.filter(evento__registrado_por=usuario)
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
