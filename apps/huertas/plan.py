"""Plan de siembra por cama y su automatización (HU-HB02, HU-HB08).

Cada cambio del plan:
1. se guarda (con historial de lo que hubo antes en la cama),
2. deja un Movimiento («Lo que ha pasado»),
3. recalcula el umbral de la cama con la misma regla del frontend (ciclo.umbral_de_cama), y
4. si está activado `HUERTAS_ENVIAR_UMBRALES` y la cama está conectada a una válvula del gateway,
   lo envía por el flujo de configuración remota (control_mqtt.aplicar_config) y guarda el
   resultado tal cual: `sin_respuesta` NO es «aplicada».

Una cama en descanso no recibe umbral; si todas las camas de una zona del gateway quedan en
descanso, se apaga el riego automático de esa zona.
"""
import logging
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.huertas import ciclo
from apps.huertas.models import Cama, CamaHistorial, Cultivo, Movimiento

logger = logging.getLogger(__name__)

UMBRAL_MIN, UMBRAL_MAX = 0, 100


def hoy():
    return timezone.localdate()


def fichas_por_id(ids=None):
    qs = Cultivo.objects.prefetch_related("etapas")
    if ids is not None:
        qs = qs.filter(id__in=[i for i in ids if i])
    return {c.id: c.ficha_dict() for c in qs}


def _umbral(cama, ficha, dia=None):
    if not ficha:
        return None
    dias = ciclo.dias_desde(cama.sembrado_el, dia or hoy())
    u = ciclo.umbral_de_cama(ficha, dias, cama.ajuste)
    abrir = max(UMBRAL_MIN, min(UMBRAL_MAX - 3, u["abrir"]))
    cerrar = max(abrir + 3, min(UMBRAL_MAX, u["cerrar"]))
    return {**u, "abrir": abrir, "cerrar": cerrar}


def cama_dict(cama, fichas, historial=None, equipo=False, dia=None):
    """Una cama tal como la necesita la web (equivale a `Era` + `EraPlan` del frontend)."""
    ficha = fichas.get(cama.cultivo_id) if cama.cultivo_id else None
    dias = ciclo.dias_desde(cama.sembrado_el, dia or hoy()) if ficha else None
    m = ciclo.momento(ficha, dias) if ficha and dias is not None else None
    u = _umbral(cama, ficha, dia)
    data = {
        "zona": cama.zona,
        "orden": cama.orden,
        "libre": ficha is None,
        "cultivo_id": cama.cultivo_id,
        "cultivo_nombre": ficha["nombre"] if ficha else None,
        "sembrado_el": cama.sembrado_el,
        "dias": dias,
        "edad": ciclo.edad_texto(dias) if dias is not None else None,
        "momento": m.como_dict() if m else None,
        "cosechando": bool(cama.cosechando or (m and m.etapa["tipo"] == "cosecha")),
        "cosechando_marcado": cama.cosechando,
        "ajuste": cama.ajuste,
        "umbral": {"abrir": u["abrir"], "cerrar": u["cerrar"], "sed": u["sed"], "etapa": u["etapa"]} if u else None,
        "anteriores": [
            {"cultivo_id": h.cultivo_id, "sembrado_el": h.sembrado_el, "hasta": h.hasta}
            for h in (historial if historial is not None else cama.historial.all()[:4])
        ],
        "riego": {
            "conectada": cama.conectada,
            "con_sensor": bool(cama.sensor),
            "ultimo_envio": {
                "resultado": cama.envio_resultado,
                "en": cama.envio_en,
                "detalle": cama.envio_detalle or [],
            } if cama.envio_resultado else None,
        },
    }
    if equipo:
        data["tecnico"] = {
            "gateway_zona": cama.gateway_zona,
            "valvula": cama.valvula,
            "sensor": cama.sensor,
            "umbral_enviado": {"abrir": cama.umbral_abrir, "cerrar": cama.umbral_cerrar, "rev": cama.envio_rev},
        }
    return data


def plan_dict(agrohub, equipo=False):
    camas = list(agrohub.camas.select_related("cultivo").prefetch_related("historial"))
    fichas = fichas_por_id([c.cultivo_id for c in camas])
    return {
        "agrohub": {"id": agrohub.id, "numero": agrohub.numero, "nombre": agrohub.nombre},
        "envio_automatico": bool(getattr(settings, "HUERTAS_ENVIAR_UMBRALES", False)),
        "camas": [cama_dict(c, fichas, list(c.historial.all()[:4]), equipo) for c in camas],
    }


# ---------------------------------------------------------------------------------- cambios


def _nombre(ficha_o_cultivo):
    if not ficha_o_cultivo:
        return "nada"
    nombre = ficha_o_cultivo["nombre"] if isinstance(ficha_o_cultivo, dict) else ficha_o_cultivo.nombre
    return nombre.lower()


def _mover_al_historial(cama, hasta):
    if cama.cultivo_id:
        CamaHistorial.objects.create(cama=cama, cultivo_id=cama.cultivo_id, sembrado_el=cama.sembrado_el, hasta=hasta)


def _movimiento(agrohub, cama, tipo, texto, usuario, **datos):
    return Movimiento.objects.create(agrohub=agrohub, cama=cama, tipo=tipo, texto=texto[:300], usuario=usuario, datos=datos)


def validar_ajuste(valor):
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ValidationError({"ajuste": "Debe ser un número entero de puntos."})
    if abs(valor) > ciclo.AJUSTE_MAXIMO:
        raise ValidationError({
            "ajuste": (
                f"La calibración llega hasta ±{ciclo.AJUSTE_MAXIMO} puntos. Si hace falta más, puede ser el "
                "sensor: avisa al equipo técnico."
            )
        })


@transaction.atomic
def cambiar_cama(agrohub, cama, cambios, usuario):
    """Aplica un cambio parcial a la cama. `cambios` admite:
    - cultivo_id: id de la biblioteca para sembrar, o null para dejarla en descanso
    - sembrado_el: fecha de siembra (date) — al sembrar, por defecto hoy
    - cosechando: bool
    - ajuste: calibración en puntos (±6)
    Devuelve la lista de movimientos creados."""
    cama = Cama.objects.select_for_update().get(pk=cama.pk)
    movimientos = []
    hoy_ = hoy()

    if "cultivo_id" in cambios:
        nuevo_id = cambios["cultivo_id"]
        if nuevo_id:
            nuevo = Cultivo.objects.filter(id=nuevo_id, activo=True).first()
            if not nuevo:
                raise ValidationError({"cultivo_id": f"No hay un cultivo «{nuevo_id}» en la biblioteca."})
            sembrado = cambios.get("sembrado_el") or hoy_
            if sembrado > hoy_:
                raise ValidationError({"sembrado_el": "La fecha de siembra no puede ser futura."})
            anterior = cama.cultivo
            if nuevo.id != cama.cultivo_id or sembrado != cama.sembrado_el:
                _mover_al_historial(cama, sembrado)
                cama.cultivo, cama.sembrado_el, cama.cosechando = nuevo, sembrado, False
                if anterior:
                    texto = f"Cama {cama.zona}: se cambió {_nombre(anterior)} por {_nombre(nuevo)}"
                    tipo = "cambio"
                else:
                    texto = f"Se sembró {_nombre(nuevo)} en la cama {cama.zona}"
                    tipo = "siembra"
                movimientos.append(_movimiento(agrohub, cama, tipo, texto, usuario, cultivo_id=nuevo.id, sembrado_el=str(sembrado)))
        elif cama.cultivo_id:
            anterior = cama.cultivo
            _mover_al_historial(cama, hoy_)
            cama.cultivo, cama.sembrado_el, cama.cosechando = None, None, False
            movimientos.append(_movimiento(
                agrohub, cama, "descanso", f"La cama {cama.zona} quedó en descanso (había {_nombre(anterior)})", usuario,
                cultivo_anterior=anterior.id,
            ))

    if "sembrado_el" in cambios and "cultivo_id" not in cambios:
        fecha = cambios["sembrado_el"]
        if not cama.cultivo_id:
            raise ValidationError({"sembrado_el": "La cama está en descanso: primero siembra un cultivo."})
        if fecha and fecha > hoy_:
            raise ValidationError({"sembrado_el": "La fecha de siembra no puede ser futura."})
        if fecha != cama.sembrado_el:
            cama.sembrado_el = fecha
            movimientos.append(_movimiento(
                agrohub, cama, "cambio",
                f"Cama {cama.zona}: la siembra de {_nombre(cama.cultivo)} pasó al {fecha:%d/%m/%Y}" if fecha
                else f"Cama {cama.zona}: no se sabe cuándo se sembró {_nombre(cama.cultivo)}",
                usuario, sembrado_el=str(fecha) if fecha else None,
            ))

    if "cosechando" in cambios:
        valor = bool(cambios["cosechando"])
        if valor and not cama.cultivo_id:
            raise ValidationError({"cosechando": "Una cama en descanso no da cosecha."})
        if valor != cama.cosechando:
            cama.cosechando = valor
            if valor:
                movimientos.append(_movimiento(
                    agrohub, cama, "cosecha", f"La cama de {_nombre(cama.cultivo)} ya está dando cosecha", usuario,
                ))

    if "ajuste" in cambios:
        valor = cambios["ajuste"]
        validar_ajuste(valor)
        if valor != cama.ajuste:
            antes = cama.ajuste
            cama.ajuste = valor
            sentido = "antes" if valor > antes else "después"
            movimientos.append(_movimiento(
                agrohub, cama, "calibracion",
                f"Cama {cama.zona}: el riego abre {abs(valor - antes)} puntos {sentido} (calibración {valor:+d})",
                usuario, antes=antes, ahora=valor,
            ))

    cama.save()
    return cama, movimientos


@transaction.atomic
def intercambiar(agrohub, zona_a, zona_b, usuario):
    """Cambia de cama dos cultivos; cada zona conserva su calibración (intercambiar() de plan.ts)."""
    if zona_a == zona_b:
        raise ValidationError({"zonas": "Elige dos camas distintas."})
    camas = {c.zona: c for c in Cama.objects.select_for_update().filter(agrohub=agrohub, zona__in=[zona_a, zona_b])}
    if len(camas) != 2:
        raise ValidationError({"zonas": "Alguna de las camas no existe en esta huerta."})
    a, b = camas[zona_a], camas[zona_b]
    a.cultivo_id, b.cultivo_id = b.cultivo_id, a.cultivo_id
    a.sembrado_el, b.sembrado_el = b.sembrado_el, a.sembrado_el
    a.cosechando, b.cosechando = b.cosechando, a.cosechando
    a.save()
    b.save()
    texto = (
        f"Se cambiaron de cama: {_nombre(a.cultivo) if a.cultivo_id else 'descanso'} quedó en la {a.zona} y "
        f"{_nombre(b.cultivo) if b.cultivo_id else 'descanso'} en la {b.zona}"
    )
    mov = _movimiento(agrohub, None, "cambio", texto, usuario, zonas=[zona_a, zona_b])
    return [a, b], [mov]


# ------------------------------------------------------------------------------ automatización


def _resultado_global(resultados):
    orden = ["error", "rechazada", "invalida", "sin_respuesta", "aplicada"]
    vistos = {r for r in resultados if r}
    for r in orden:
        if r in vistos:
            return r
    return next(iter(vistos), None)


def recalcular_y_enviar(agrohub, camas=None, forzar=False, dia=None):
    """Recalcula el umbral de las camas y, si cambió (o `forzar`), lo envía al gateway.

    Devuelve {"resultado": ..., "camas": {zona: {...}}}. Resultados posibles por cama:
    aplicada | rechazada | sin_respuesta | invalida | error | sin_gateway | desactivado | sin_cambios | descanso
    """
    todas = list(agrohub.camas.select_related("cultivo"))
    objetivo = {c.zona for c in (camas or todas)}
    fichas = fichas_por_id([c.cultivo_id for c in todas])
    enviar_activo = bool(getattr(settings, "HUERTAS_ENVIAR_UMBRALES", False))
    ahora = timezone.now()

    por_cama, zonas_payload, camas_payload = {}, {}, {}
    # Zonas del gateway donde todas las camas quedan en descanso → riego automático apagado.
    zonas_libres = {}
    for c in todas:
        if c.gateway_zona:
            zonas_libres.setdefault(c.gateway_zona, True)
            if c.cultivo_id:
                zonas_libres[c.gateway_zona] = False

    for c in todas:
        if c.zona not in objetivo:
            continue
        ficha = fichas.get(c.cultivo_id)
        u = _umbral(c, ficha, dia)
        nueva_etapa = u["etapa"] if u else None
        if u:
            cambio = forzar or (c.umbral_abrir, c.umbral_cerrar, c.etapa_tipo) != (u["abrir"], u["cerrar"], nueva_etapa)
        else:
            # En descanso solo hay algo que mandar si antes tenía umbral (hay que apagar el automático).
            cambio = forzar or c.umbral_abrir is not None or c.envio_resultado not in (None, "descanso")
        c.etapa_tipo = nueva_etapa
        if not u:
            c.umbral_abrir = c.umbral_cerrar = None
        if not c.conectada or not agrohub.dispositivo:
            por_cama[c.zona] = {"resultado": "sin_gateway", "umbral": u}
            c.save(update_fields=["etapa_tipo", "umbral_abrir", "umbral_cerrar", "updated_at"])
            continue
        if not enviar_activo:
            por_cama[c.zona] = {"resultado": "desactivado", "umbral": u}
            c.save(update_fields=["etapa_tipo", "umbral_abrir", "umbral_cerrar", "updated_at"])
            continue
        if not cambio:
            por_cama[c.zona] = {"resultado": "sin_cambios", "umbral": u}
            continue
        if not u and not zonas_libres.get(c.gateway_zona, False):
            # Cama en descanso en una zona que sigue regando otras camas: no hay nada que mandar
            # (el automático de la zona lo necesitan las demás).
            c.umbral_abrir = c.umbral_cerrar = None
            c.envio_resultado, c.envio_en, c.envio_detalle = "descanso", ahora, []
            c.save()
            por_cama[c.zona] = {"resultado": "descanso", "umbral": None}
            continue
        zona = zonas_payload.setdefault(c.gateway_zona, {})
        if u:
            zona.setdefault("riego", {})[c.valvula] = {"abrir": u["abrir"], "cerrar": u["cerrar"]}
        if zonas_libres.get(c.gateway_zona, False):
            zona["auto"] = False
        elif u and c.envio_resultado == "descanso":
            zona["auto"] = True  # la cama estaba en descanso y vuelve a tener cultivo: se reenciende
        camas_payload.setdefault(c.gateway_zona, []).append((c, u))

    if zonas_payload:
        from apps.riego_iot import control_mqtt

        try:
            resp = control_mqtt.aplicar_config(agrohub.dispositivo, zonas_payload)
        except Exception as exc:  # noqa: BLE001 — broker caído, credenciales, etc.
            logger.warning("huertas: no se pudo enviar el umbral de %s: %s", agrohub.numero, exc)
            resp = {"resultado": "error", "rev": None, "errores": [str(exc)]}
        for lista in camas_payload.values():
            for c, u in lista:
                c.envio_resultado = resp["resultado"]
                c.envio_rev = resp.get("rev")
                c.envio_detalle = resp.get("errores") or []
                c.envio_en = ahora
                if resp["resultado"] == "aplicada" and u:
                    c.umbral_abrir, c.umbral_cerrar = u["abrir"], u["cerrar"]
                elif not u:
                    c.umbral_abrir = c.umbral_cerrar = None
                    if resp["resultado"] == "aplicada":
                        c.envio_resultado = "descanso"  # ya quedó apagado: no se vuelve a mandar
                c.save()
                por_cama[c.zona] = {"resultado": resp["resultado"] if u else "descanso", "umbral": u, "rev": resp.get("rev"), "errores": c.envio_detalle}

    return {"resultado": _resultado_global(r["resultado"] for r in por_cama.values()), "camas": por_cama}
