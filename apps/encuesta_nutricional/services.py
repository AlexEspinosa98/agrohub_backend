import uuid
from datetime import datetime

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.encuesta_nutricional.models import EncuestaNutricional, Miembro, PersonaNutricional

_PERSONA_FIELDS = ["nombre", "edad_anios", "sexo", "area_residencia", "nivel_educativo"]
_MIEMBRO_MEDICION_FIELDS = [
    "percepcion_estado_nutricional",
    "cambio_peso_no_intencional",
    "nino_en_control_crecimiento",
    "peso_kg",
    "talla_cm",
    "circunferencia_cintura_cm",
    "perimetro_brazo_cm",
    "grupo_perimetro_brazo",
    "imc_calculado",
]
_RANGOS_EDAD = ["0-5", "6-12", "13-17", "18-29", "30-44", "45-59", "60+"]


def _upsert_persona(cedula, nombre, edad_anios, sexo, area_residencia, nivel_educativo) -> PersonaNutricional:
    """Inserta o actualiza una persona por cédula. Si no llega cédula (persona
    sin documento, ej. menor), se genera un identificador único en vez de
    dejar que distintas personas anónimas choquen bajo un mismo valor de
    relleno escrito a mano."""
    if not cedula:
        cedula = f"SIN-CEDULA-{uuid.uuid4().hex[:12].upper()}"

    incoming = {
        "nombre": nombre,
        "edad_anios": edad_anios,
        "sexo": sexo,
        "area_residencia": area_residencia,
        "nivel_educativo": nivel_educativo,
    }
    persona, created = PersonaNutricional.objects.get_or_create(cedula=cedula, defaults=incoming)
    if not created:
        changed_fields = []
        for field, value in incoming.items():
            if value is not None:
                setattr(persona, field, value)
                changed_fields.append(field)
        if changed_fields:
            persona.save(update_fields=changed_fields)
    return persona


def _insert_miembro(encuesta: EncuestaNutricional, miembro_data: dict) -> Miembro:
    persona = _upsert_persona(
        cedula=miembro_data.get("cedula_participante"),
        nombre=miembro_data.get("nombre_participante"),
        edad_anios=miembro_data.get("edad_anios"),
        sexo=miembro_data.get("sexo"),
        area_residencia=miembro_data.get("area_residencia"),
        nivel_educativo=miembro_data.get("nivel_educativo"),
    )
    return Miembro.objects.create(
        encuesta=encuesta,
        persona=persona,
        **{f: miembro_data.get(f) for f in _MIEMBRO_MEDICION_FIELDS},
    )


@transaction.atomic
def create_encuesta(data: dict) -> dict:
    miembros_data = data.pop("miembros")
    encuesta = EncuestaNutricional.objects.create(**data)
    numero = f"SAN-{timezone.now().strftime('%Y%m%d')}-{encuesta.id:06d}"
    encuesta.numero_encuesta = numero
    encuesta.save(update_fields=["numero_encuesta"])
    for miembro_data in miembros_data:
        _insert_miembro(encuesta, miembro_data)
    return {"id": encuesta.id, "numero_encuesta": numero, "miembros_creados": len(miembros_data)}


def get_by_numero(numero_encuesta: str):
    return EncuestaNutricional.objects.filter(numero_encuesta=numero_encuesta, is_active=True).first()


def _miembro_to_dict(m: Miembro) -> dict:
    return {
        "id": m.id,
        "encuesta_id": m.encuesta_id,
        "persona_id": m.persona_id,
        "is_active": m.is_active,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
        "deleted_at": m.deleted_at,
        "cedula_participante": m.persona.cedula,
        "nombre_participante": m.persona.nombre,
        "edad_anios": m.persona.edad_anios,
        "sexo": m.persona.sexo,
        "area_residencia": m.persona.area_residencia,
        "nivel_educativo": m.persona.nivel_educativo,
        "percepcion_estado_nutricional": m.percepcion_estado_nutricional,
        "cambio_peso_no_intencional": m.cambio_peso_no_intencional,
        "nino_en_control_crecimiento": m.nino_en_control_crecimiento,
        "peso_kg": m.peso_kg,
        "talla_cm": m.talla_cm,
        "circunferencia_cintura_cm": m.circunferencia_cintura_cm,
        "perimetro_brazo_cm": m.perimetro_brazo_cm,
        "grupo_perimetro_brazo": m.grupo_perimetro_brazo,
        "imc_calculado": m.imc_calculado,
    }


def list_miembros(encuesta_id: int) -> list:
    qs = Miembro.objects.select_related("persona").filter(encuesta_id=encuesta_id, is_active=True)
    return [_miembro_to_dict(m) for m in qs]


def get_miembro(encuesta_id: int, miembro_id: int):
    m = (
        Miembro.objects.select_related("persona")
        .filter(id=miembro_id, encuesta_id=encuesta_id, is_active=True)
        .first()
    )
    return _miembro_to_dict(m) if m else None


def get_detail(numero_encuesta: str):
    encuesta = get_by_numero(numero_encuesta)
    if not encuesta:
        return None
    data = _encuesta_to_dict(encuesta)
    data["miembros"] = list_miembros(encuesta.id)
    return data


def _encuesta_to_dict(e: EncuestaNutricional) -> dict:
    data = {"id": e.id}
    for field in e._meta.fields:
        if field.name == "id":
            continue
        data[field.name] = getattr(e, field.name)
    return data


def list_surveys(
    nombre_encuestador=None,
    municipio=None,
    vereda_comunidad=None,
    numero_encuesta=None,
    cedula_encuestador=None,
    page=1,
    page_size=50,
) -> list:
    qs = EncuestaNutricional.objects.filter(is_active=True)
    if nombre_encuestador:
        qs = qs.filter(nombre_encuestador__icontains=nombre_encuestador)
    if municipio:
        qs = qs.filter(municipio=municipio)
    if vereda_comunidad:
        qs = qs.filter(vereda_comunidad__icontains=vereda_comunidad)
    if numero_encuesta:
        qs = qs.filter(numero_encuesta=numero_encuesta)
    if cedula_encuestador:
        qs = qs.filter(cedula_encuestador=cedula_encuestador)

    qs = qs.annotate(
        total_miembros=Count("miembros", filter=Q(miembros__is_active=True))
    ).order_by("-created_at")

    offset = (page - 1) * page_size
    qs = qs[offset : offset + page_size]
    return [
        {
            "numero_encuesta": e.numero_encuesta,
            "nombre_encuestador": e.nombre_encuestador,
            "cedula_encuestador": e.cedula_encuestador,
            "fecha_aplicacion": e.fecha_aplicacion,
            "municipio": e.municipio,
            "vereda_comunidad": e.vereda_comunidad,
            "total_miembros": e.total_miembros,
        }
        for e in qs
    ]


def get_resumen_por_municipio() -> list:
    qs = (
        EncuestaNutricional.objects.filter(is_active=True)
        .values("municipio")
        .annotate(
            total_encuestas=Count("id", distinct=True),
            total_miembros=Count("miembros", filter=Q(miembros__is_active=True)),
        )
        .order_by("-total_encuestas")
    )
    return list(qs)


def get_resumen_por_vereda(municipio=None) -> list:
    qs = EncuestaNutricional.objects.filter(is_active=True)
    if municipio:
        qs = qs.filter(municipio=municipio)
    qs = (
        qs.values("municipio", "vereda_comunidad")
        .annotate(
            total_encuestas=Count("id", distinct=True),
            total_miembros=Count("miembros", filter=Q(miembros__is_active=True)),
        )
        .order_by("municipio", "-total_encuestas")
    )
    return list(qs)


def _round(value):
    return round(float(value), 2) if value is not None else None


def get_detalle_municipio(municipio: str):
    hogar = EncuestaNutricional.objects.filter(municipio=municipio, is_active=True).aggregate(
        total_encuestas=Count("id"),
        promedio_diversidad_dietetica=Avg("puntaje_diversidad_dietetica"),
        promedio_inseguridad_alimentaria=Avg("puntaje_inseguridad_alimentaria"),
    )
    if not hogar["total_encuestas"]:
        return None

    distribucion_seguridad = dict(
        EncuestaNutricional.objects.filter(municipio=municipio, is_active=True)
        .exclude(clasificacion_seguridad_alimentaria__isnull=True)
        .values_list("clasificacion_seguridad_alimentaria")
        .annotate(total=Count("id"))
    )

    miembros_qs = Miembro.objects.filter(
        encuesta__municipio=municipio, encuesta__is_active=True, is_active=True
    )
    miembros_stats = miembros_qs.aggregate(
        total_miembros=Count("id"),
        promedio_edad_anios=Avg("persona__edad_anios"),
        promedio_peso_kg=Avg("peso_kg"),
        promedio_talla_cm=Avg("talla_cm"),
        promedio_circunferencia_cintura_cm=Avg("circunferencia_cintura_cm"),
        promedio_imc=Avg("imc_calculado"),
    )

    distribucion_sexo = dict(
        miembros_qs.exclude(persona__sexo__isnull=True)
        .values_list("persona__sexo")
        .annotate(total=Count("id"))
    )

    conteo_por_rango = {r: 0 for r in _RANGOS_EDAD}
    edades = miembros_qs.exclude(persona__edad_anios__isnull=True).values_list(
        "persona__edad_anios", flat=True
    )
    for edad in edades:
        if edad <= 5:
            rango = "0-5"
        elif edad <= 12:
            rango = "6-12"
        elif edad <= 17:
            rango = "13-17"
        elif edad <= 29:
            rango = "18-29"
        elif edad <= 44:
            rango = "30-44"
        elif edad <= 59:
            rango = "45-59"
        else:
            rango = "60+"
        conteo_por_rango[rango] += 1

    return {
        "municipio": municipio,
        "total_encuestas": hogar["total_encuestas"],
        "total_miembros": miembros_stats["total_miembros"] or 0,
        "promedio_edad_anios": _round(miembros_stats["promedio_edad_anios"]),
        "promedio_peso_kg": _round(miembros_stats["promedio_peso_kg"]),
        "promedio_talla_cm": _round(miembros_stats["promedio_talla_cm"]),
        "promedio_circunferencia_cintura_cm": _round(miembros_stats["promedio_circunferencia_cintura_cm"]),
        "promedio_imc": _round(miembros_stats["promedio_imc"]),
        "promedio_diversidad_dietetica": _round(hogar["promedio_diversidad_dietetica"]),
        "promedio_inseguridad_alimentaria": _round(hogar["promedio_inseguridad_alimentaria"]),
        "distribucion_seguridad_alimentaria": distribucion_seguridad,
        "distribucion_sexo": distribucion_sexo,
        "distribucion_edad": conteo_por_rango,
    }


_ENCUESTA_UPDATABLE = [
    "nombre_encuestador", "cedula_encuestador", "fecha_aplicacion",
    "codigo_cuestionario", "municipio", "vereda_comunidad",
    "num_personas_hogar", "num_mujeres_hogar", "hay_menores_18",
    "num_ninos_menores_5", "fuente_ingreso_principal", "tiene_huerta_o_animales",
    "jefatura_hogar", "estabilidad_ingreso",
    "dias_cereales_tuberculos", "dias_leguminosas", "dias_carnes_pescado_huevo",
    "dias_lacteos", "dias_frutas", "dias_verduras", "dias_grasas",
    "dias_azucares_ultraprocesados", "puntaje_diversidad_dietetica",
    "frecuencia_frutas_semana", "frecuencia_verduras_semana",
    "frecuencia_bebidas_azucaradas", "comidas_por_dia",
    "frecuencia_comida_fuera_hogar", "proporcion_autoconsumo",
    "alimentos_preferidos", "preocupacion_alimentos_acabaran",
    "alimentos_se_acabaron", "adulto_omitio_comida_principal",
    "sintio_hambre_sin_comer", "puntaje_inseguridad_alimentaria",
    "clasificacion_seguridad_alimentaria", "consentimiento_informado",
    "observaciones_encuestador",
]

_PERSONA_UPDATABLE = ["nombre", "edad_anios", "sexo", "area_residencia", "nivel_educativo"]

_MIEMBRO_UPDATABLE = _MIEMBRO_MEDICION_FIELDS

_PERSONA_MAP = {
    "nombre_participante": "nombre",
    "edad_anios": "edad_anios",
    "sexo": "sexo",
    "area_residencia": "area_residencia",
    "nivel_educativo": "nivel_educativo",
}


def update_encuesta(numero_encuesta: str, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in _ENCUESTA_UPDATABLE and v is not None}
    if not fields:
        return False
    updated = EncuestaNutricional.objects.filter(
        numero_encuesta=numero_encuesta, is_active=True
    ).update(**fields)
    return updated > 0


def update_persona(persona_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in _PERSONA_UPDATABLE and v is not None}
    if not fields:
        return False
    updated = PersonaNutricional.objects.filter(id=persona_id, is_active=True).update(**fields)
    return updated > 0


def soft_delete_encuesta(numero_encuesta: str) -> bool:
    now = timezone.now()
    updated = EncuestaNutricional.objects.filter(
        numero_encuesta=numero_encuesta, is_active=True
    ).update(is_active=False, deleted_at=now)
    if not updated:
        return False
    Miembro.objects.filter(encuesta__numero_encuesta=numero_encuesta).update(
        is_active=False, deleted_at=now
    )
    return True


def add_miembro(numero_encuesta: str, data: dict):
    encuesta = get_by_numero(numero_encuesta)
    if not encuesta:
        return None
    miembro = _insert_miembro(encuesta, data)
    return {"id": miembro.id, "encuesta_id": encuesta.id}


@transaction.atomic
def update_miembro(encuesta_id: int, miembro_id: int, data: dict) -> bool:
    persona_cambios = {
        col: data[field] for field, col in _PERSONA_MAP.items() if data.get(field) is not None
    }
    cedula_nueva = data.get("cedula_participante")
    tocando_identidad = bool(persona_cambios) or "cedula_participante" in data
    miembro_cols = {f: data[f] for f in _MIEMBRO_UPDATABLE if data.get(f) is not None}

    if not tocando_identidad and not miembro_cols:
        return False

    miembro = Miembro.objects.select_related("persona").filter(
        id=miembro_id, encuesta_id=encuesta_id, is_active=True
    ).first()
    if not miembro:
        return False

    if tocando_identidad:
        persona_actual = miembro.persona
        compartida = Miembro.objects.filter(persona=persona_actual, is_active=True).count() > 1

        if compartida or "cedula_participante" in data:
            # La persona actual la usan otros miembros (o se está corrigiendo la
            # cédula explícitamente): NO se muta esa fila compartida. Se crea/
            # resuelve una identidad propia para ESTE miembro y solo se
            # repunta este registro — los demás que aún comparten la persona
            # anterior quedan intactos.
            nueva_persona = _upsert_persona(
                cedula=cedula_nueva,
                nombre=persona_cambios.get("nombre", persona_actual.nombre),
                edad_anios=persona_cambios.get("edad_anios", persona_actual.edad_anios),
                sexo=persona_cambios.get("sexo", persona_actual.sexo),
                area_residencia=persona_cambios.get("area_residencia", persona_actual.area_residencia),
                nivel_educativo=persona_cambios.get("nivel_educativo", persona_actual.nivel_educativo),
            )
            miembro.persona = nueva_persona
            miembro.save(update_fields=["persona"])
        else:
            for field, value in persona_cambios.items():
                setattr(persona_actual, field, value)
            persona_actual.save(update_fields=list(persona_cambios.keys()))

    if miembro_cols:
        for field, value in miembro_cols.items():
            setattr(miembro, field, value)
        miembro.save(update_fields=list(miembro_cols.keys()))

    return True


def soft_delete_miembro(encuesta_id: int, miembro_id: int) -> bool:
    updated = Miembro.objects.filter(id=miembro_id, encuesta_id=encuesta_id, is_active=True).update(
        is_active=False, deleted_at=timezone.now()
    )
    return updated > 0


def get_datos_completos_para_export() -> list:
    qs = (
        Miembro.objects.select_related("encuesta", "persona")
        .filter(encuesta__is_active=True, is_active=True)
        .order_by("encuesta__municipio", "encuesta__numero_encuesta")
    )
    rows = []
    for m in qs:
        e = m.encuesta
        p = m.persona
        rows.append(
            {
                "numero_encuesta": e.numero_encuesta,
                "nombre_encuestador": e.nombre_encuestador,
                "cedula_encuestador": e.cedula_encuestador,
                "fecha_aplicacion": e.fecha_aplicacion,
                "codigo_cuestionario": e.codigo_cuestionario,
                "municipio": e.municipio,
                "vereda_comunidad": e.vereda_comunidad,
                "num_personas_hogar": e.num_personas_hogar,
                "num_mujeres_hogar": e.num_mujeres_hogar,
                "hay_menores_18": e.hay_menores_18,
                "num_ninos_menores_5": e.num_ninos_menores_5,
                "fuente_ingreso_principal": e.fuente_ingreso_principal,
                "tiene_huerta_o_animales": e.tiene_huerta_o_animales,
                "jefatura_hogar": e.jefatura_hogar,
                "estabilidad_ingreso": e.estabilidad_ingreso,
                "dias_cereales_tuberculos": e.dias_cereales_tuberculos,
                "dias_leguminosas": e.dias_leguminosas,
                "dias_carnes_pescado_huevo": e.dias_carnes_pescado_huevo,
                "dias_lacteos": e.dias_lacteos,
                "dias_frutas": e.dias_frutas,
                "dias_verduras": e.dias_verduras,
                "dias_grasas": e.dias_grasas,
                "dias_azucares_ultraprocesados": e.dias_azucares_ultraprocesados,
                "puntaje_diversidad_dietetica": e.puntaje_diversidad_dietetica,
                "frecuencia_frutas_semana": e.frecuencia_frutas_semana,
                "frecuencia_verduras_semana": e.frecuencia_verduras_semana,
                "frecuencia_bebidas_azucaradas": e.frecuencia_bebidas_azucaradas,
                "comidas_por_dia": e.comidas_por_dia,
                "frecuencia_comida_fuera_hogar": e.frecuencia_comida_fuera_hogar,
                "proporcion_autoconsumo": e.proporcion_autoconsumo,
                "alimentos_preferidos": e.alimentos_preferidos,
                "preocupacion_alimentos_acabaran": e.preocupacion_alimentos_acabaran,
                "alimentos_se_acabaron": e.alimentos_se_acabaron,
                "adulto_omitio_comida_principal": e.adulto_omitio_comida_principal,
                "sintio_hambre_sin_comer": e.sintio_hambre_sin_comer,
                "puntaje_inseguridad_alimentaria": e.puntaje_inseguridad_alimentaria,
                "clasificacion_seguridad_alimentaria": e.clasificacion_seguridad_alimentaria,
                "consentimiento_informado": e.consentimiento_informado,
                "observaciones_encuestador": e.observaciones_encuestador,
                "cedula_participante": p.cedula,
                "nombre_participante": p.nombre,
                "edad_anios": p.edad_anios,
                "sexo": p.sexo,
                "area_residencia": p.area_residencia,
                "nivel_educativo": p.nivel_educativo,
                "percepcion_estado_nutricional": m.percepcion_estado_nutricional,
                "cambio_peso_no_intencional": m.cambio_peso_no_intencional,
                "nino_en_control_crecimiento": m.nino_en_control_crecimiento,
                "peso_kg": m.peso_kg,
                "talla_cm": m.talla_cm,
                "circunferencia_cintura_cm": m.circunferencia_cintura_cm,
                "perimetro_brazo_cm": m.perimetro_brazo_cm,
                "grupo_perimetro_brazo": m.grupo_perimetro_brazo,
                "imc_calculado": m.imc_calculado,
            }
        )
    return rows
