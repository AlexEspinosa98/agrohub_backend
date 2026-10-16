"""Reportes y herramientas para admin/superadmin de asistencia_eventos.

A diferencia de los dashboards de services.py (acotados por dueño: cada usuario ve lo que él
registró), esto mira TODO el sistema — es el seguimiento de la meta del proyecto:

- reporte_meta(): municipio x género x rango de edad contra la población objetivo (DANE), contando
  cada persona UNA sola vez por cédula.
- resumen_por_usuario() / eventos_de_usuario(): quién ha subido cuántos eventos.
- municipios_registrados() / corregir_municipios(): ver cómo está escrito el municipio en todos los
  registros y corregirlo en bloque (en vez de evento por evento).
- reporte_excel(): todo lo anterior en un libro de Excel.
"""

import io
from collections import Counter, defaultdict

import pandas as pd
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.asistencia_eventos.catalogos import MUNICIPIOS_OBJETIVO, clasificar_municipio, clave_texto
from apps.asistencia_eventos.models import Evento, RegistroAsistencia
from apps.asistencia_eventos.services import _GENERO_LABELS, _RANGOS_EDAD, _rango_edad

FUENTE_META = (
    "DANE - Censo Nacional de Población y Vivienda 2023: población objetivo de los cuatro "
    "municipios priorizados del Magdalena"
)

RANGOS = [r[0] for r in _RANGOS_EDAD]
GENEROS_META = ("Masculino", "Femenino")

# Meta por municipio y rango de edad. La tabla del DANE trae el mismo número para Masculino y
# Femenino, así que se define una vez y se copia a cada género — si algún día difieren, se separa
# aquí (cada género tiene su propio dict). Total: 3100 personas.
_META_POR_GENERO = {
    "Algarrobo": {"0-14": 73, "15-19": 87, "20-59": 350, "mayor de 60": 65},
    "Aracataca": {"0-14": 39, "15-19": 46, "20-59": 203, "mayor de 60": 37},
    "Fundación": {"0-14": 49, "15-19": 56, "20-59": 273, "mayor de 60": 47},
    "El Retén": {"0-14": 24, "15-19": 31, "20-59": 148, "mayor de 60": 22},
}
META_POBLACION_OBJETIVO = {
    municipio: {genero: dict(rangos) for genero in GENEROS_META}
    for municipio, rangos in _META_POR_GENERO.items()
}

CRITERIOS = [
    "Cada persona cuenta una sola vez (por número de documento), sin importar en cuántos eventos aparezca.",
    "Municipio: el del registro más reciente que se pueda llevar a uno de los 4 municipios objetivo "
    "(ver clasificacion_municipio para saber cuántos salieron de una coincidencia exacta, aproximada "
    "o de un texto que solo contiene el nombre).",
    "Edad: la del registro más reciente que la tenga. Sin edad no se puede ubicar en un rango.",
    "Género: Masculino/Femenino de la ficha de la persona. 'Otro' o sin dato queda fuera de la meta.",
    "'logrado' puede superar la meta de una celda; 'faltante' nunca baja de 0 y 'avance_efectivo' "
    "no cuenta el exceso (cada celda aporta como máximo su meta).",
]


# --------------------------------------------------------------------------- meta


def _personas_unicas():
    """Una entrada por persona con el municipio objetivo, texto de municipio y edad que le toca.

    Recorre sus participaciones de la más reciente a la más antigua: toma el primer municipio que
    se pueda clasificar (si ninguno, queda el texto más reciente) y la primera edad que exista.
    """
    registros = RegistroAsistencia.objects.select_related("persona", "evento").order_by(
        "-evento__fecha", "-evento_id", "-id"
    )
    por_persona = {}
    for r in registros:
        d = por_persona.get(r.persona_id)
        if d is None:
            d = por_persona[r.persona_id] = {
                "persona": r.persona,
                "municipio_texto": None,
                "municipio": None,
                "metodo": None,
                "edad": None,
                "eventos": 0,
            }
        d["eventos"] += 1
        if d["municipio_texto"] is None and r.municipio:
            d["municipio_texto"] = r.municipio
        if d["municipio"] is None:
            municipio, metodo = clasificar_municipio(r.municipio)
            if municipio:
                d["municipio"], d["metodo"] = municipio, metodo
        if d["edad"] is None and r.edad is not None:
            d["edad"] = r.edad
    return list(por_persona.values())


def _estado_persona(p):
    """(estado, rango, genero_label): por qué una persona cuenta o no en la meta."""
    genero = _GENERO_LABELS.get(p["persona"].genero)
    rango = _rango_edad(p["edad"])
    if not p["municipio"]:
        return "otro_municipio", rango, genero
    if genero not in GENEROS_META:
        return "genero_no_clasificable", rango, genero
    if rango is None:
        return "sin_edad", rango, genero
    return "en_meta", rango, genero


def _celda(meta, logrado):
    return {
        "meta": meta,
        "logrado": logrado,
        "faltante": max(meta - logrado, 0),
        "porcentaje": round(100 * logrado / meta, 1) if meta else None,
    }


def reporte_meta(personas=None):
    personas = _personas_unicas() if personas is None else personas
    logrado = defaultdict(int)
    fuera = {"otro_municipio": 0, "genero_no_clasificable": 0, "sin_edad": 0}
    metodos = {"exacto": 0, "aproximado": 0, "contiene": 0}
    for p in personas:
        estado, rango, genero = _estado_persona(p)
        if estado == "en_meta":
            logrado[(p["municipio"], genero, rango)] += 1
            metodos[p["metodo"]] += 1
        else:
            fuera[estado] += 1

    filas = []
    total_rango = {r: [0, 0] for r in RANGOS}  # [meta, logrado]
    total_meta = total_logrado = efectivo = 0
    for municipio in MUNICIPIOS_OBJETIVO:
        for genero in GENEROS_META:
            rangos, fila_meta, fila_logrado = {}, 0, 0
            for r in RANGOS:
                meta = META_POBLACION_OBJETIVO[municipio][genero][r]
                log = logrado[(municipio, genero, r)]
                rangos[r] = _celda(meta, log)
                fila_meta += meta
                fila_logrado += log
                total_rango[r][0] += meta
                total_rango[r][1] += log
                efectivo += min(log, meta)
            total_meta += fila_meta
            total_logrado += fila_logrado
            filas.append(
                {
                    "municipio": municipio,
                    "genero": genero,
                    "rangos": rangos,
                    "total": _celda(fila_meta, fila_logrado),
                }
            )

    return {
        "fuente": FUENTE_META,
        "rangos": RANGOS,
        "filas": filas,
        "total_general": {
            "rangos": {r: _celda(m, l) for r, (m, l) in total_rango.items()},
            "total": _celda(total_meta, total_logrado),
        },
        "avance_efectivo": round(100 * efectivo / total_meta, 1) if total_meta else None,
        "personas_unicas": len(personas),
        "en_meta": sum(logrado.values()),
        "fuera_de_meta": fuera,
        "clasificacion_municipio": metodos,
        "criterios": CRITERIOS,
    }


# --------------------------------------------------------------------------- usuarios


def _sin_tz(valor):
    return valor.replace(tzinfo=None) if valor else None


def resumen_por_usuario():
    """Eventos, asistencias y personas distintas por quien los registró (+ totales del sistema)."""
    grupos = {}
    for e in Evento.objects.select_related("registrado_por").annotate(n=Count("asistentes")):
        u = e.registrado_por
        g = grupos.setdefault(
            u.id if u else None,
            {
                "usuario_id": u.id if u else None,
                "nombre": u.name if u else "(sin dueño)",
                "email": u.email if u else None,
                "rol": u.role if u else None,
                "eventos": 0,
                "asistencias": 0,
                "primer_evento": None,
                "ultimo_evento": None,
            },
        )
        g["eventos"] += 1
        g["asistencias"] += e.n
        if g["primer_evento"] is None or e.created_at < g["primer_evento"]:
            g["primer_evento"] = e.created_at
        if g["ultimo_evento"] is None or e.created_at > g["ultimo_evento"]:
            g["ultimo_evento"] = e.created_at

    personas = defaultdict(set)
    for uid, pid in RegistroAsistencia.objects.values_list("evento__registrado_por_id", "persona_id"):
        personas[uid].add(pid)
    for uid, g in grupos.items():
        g["personas_unicas"] = len(personas[uid])

    usuarios = sorted(grupos.values(), key=lambda g: g["eventos"], reverse=True)
    totales = {
        "eventos": sum(g["eventos"] for g in usuarios),
        "asistencias": sum(g["asistencias"] for g in usuarios),
        # La suma de personas por usuario repite a quien aparece en eventos de varios; este es el
        # número real de personas distintas que están en algún evento.
        "personas_unicas": RegistroAsistencia.objects.values("persona_id").distinct().count(),
    }
    return usuarios, totales


def eventos_de_usuario(usuario_id):
    eventos = (
        Evento.objects.filter(registrado_por_id=usuario_id)
        .annotate(n=Count("asistentes"))
        .order_by("-created_at")
    )
    return [
        {
            "id": e.id,
            "tema": e.tema,
            "fecha": e.fecha,
            "lugar": e.lugar,
            "responsable": e.responsable,
            "asistentes": e.n,
            "subido_el": e.created_at,
            "editado_por_id": e.editado_por_id,
            "con_documento": bool(e.documento_escaneado),
        }
        for e in eventos
    ]


# --------------------------------------------------------------------------- municipios


def municipios_registrados():
    """Cada forma en que está escrito el municipio en los registros, con cuántos registros/personas
    la usan y a qué municipio objetivo parece corresponder (para decidir qué corregir)."""
    registros, personas = Counter(), defaultdict(set)
    for municipio, persona_id in RegistroAsistencia.objects.values_list("municipio", "persona_id"):
        registros[municipio] += 1
        personas[municipio].add(persona_id)

    filas = []
    for valor, n in registros.most_common():
        municipio, metodo = clasificar_municipio(valor)
        filas.append(
            {
                "valor": valor,
                "registros": n,
                "personas": len(personas[valor]),
                "sugerido": municipio,
                "metodo": metodo,
            }
        )
    en_objetivo = sum(f["registros"] for f in filas if f["sugerido"])
    return {
        "municipios_objetivo": MUNICIPIOS_OBJETIVO,
        "valores_distintos": len(filas),
        "registros_total": sum(registros.values()),
        "registros_con_municipio_objetivo": en_objetivo,
        "valores": filas,
    }


# Con estos métodos, "incluir_sugeridas" corrige solo (son typos y variantes de escritura). "contiene"
# no se aplica solo: "Biblioteca Algarrobo" o "Seno Fundacion" traen información que se perdería.
_METODOS_AUTOMATICOS = ("exacto", "aproximado")


def corregir_municipios(correcciones, confirmar, usuario, incluir_sugeridas=False):
    """Cambia el municipio de TODOS los registros que lo tengan escrito de cierta forma.

    `correcciones`: [{"desde": [textos...], "hasta": "Fundación"}, ...]. Un texto de `desde` coincide
    con cualquier forma que se escriba igual sin importar mayúsculas, tildes ni espacios
    ("fondacion" corrige también "Fondacion " y "FONDACIÓN"). Con `incluir_sugeridas` se agregan
    las correcciones obvias a los municipios objetivo (typos y variantes, no frases).

    Sin `confirmar` no toca nada: devuelve qué cambiaría. Con `confirmar` aplica todo en una sola
    transacción y deja a `usuario` como editor de los eventos afectados.
    """
    # Foto de los registros: id, evento y texto exacto del municipio.
    por_clave = defaultdict(lambda: defaultdict(list))  # clave -> valor exacto -> [(id, evento_id)]
    for rid, evento_id, valor in RegistroAsistencia.objects.exclude(municipio__isnull=True).values_list(
        "id", "evento_id", "municipio"
    ):
        if valor and valor.strip():
            por_clave[clave_texto(valor)][valor].append((rid, evento_id))

    pedidas = [
        {"desde": list(c["desde"]), "hasta": " ".join(c["hasta"].split())} for c in correcciones
    ]
    if incluir_sugeridas:
        auto = defaultdict(list)
        for clave, valores in por_clave.items():
            for valor in valores:
                municipio, metodo = clasificar_municipio(valor)
                if municipio and metodo in _METODOS_AUTOMATICOS and valor != municipio:
                    auto[municipio].append(valor)
        pedidas += [{"desde": v, "hasta": m} for m, v in auto.items()]

    plan, ya_usados, sin_coincidencia = [], set(), []
    for c in pedidas:
        encontrados = {}
        for texto in c["desde"]:
            candidatos = por_clave.get(clave_texto(texto), {})
            if not candidatos:
                sin_coincidencia.append(texto)  # ningún registro lo tiene escrito así
            for valor, filas in candidatos.items():
                if valor != c["hasta"] and valor not in ya_usados:
                    encontrados[valor] = filas
        ya_usados.update(encontrados)
        ids = [rid for filas in encontrados.values() for rid, _ in filas]
        eventos = {eid for filas in encontrados.values() for _, eid in filas}
        plan.append(
            {
                "hasta": c["hasta"],
                "valores": [{"valor": v, "registros": len(f)} for v, f in encontrados.items()],
                "registros": len(ids),
                "eventos": len(eventos),
                "_ids": ids,
                "_eventos": eventos,
            }
        )

    eventos_total = set().union(*(p["_eventos"] for p in plan)) if plan else set()
    registros_total = sum(p["registros"] for p in plan)

    if confirmar and registros_total:
        with transaction.atomic():
            for p in plan:
                for i in range(0, len(p["_ids"]), 500):
                    RegistroAsistencia.objects.filter(id__in=p["_ids"][i : i + 500]).update(
                        municipio=p["hasta"]
                    )
            # update() no dispara auto_now: se marca a mano quién y cuándo tocó cada evento.
            Evento.objects.filter(id__in=eventos_total).update(editado_por=usuario, updated_at=timezone.now())

    return {
        "aplicado": bool(confirmar and registros_total),
        "registros_total": registros_total,
        "eventos_total": len(eventos_total),
        "correcciones": [{k: v for k, v in p.items() if not k.startswith("_")} for p in plan],
        "sin_coincidencia": sorted(set(sin_coincidencia)),
    }


# --------------------------------------------------------------------------- excel


def _formatear_libro(workbook):
    relleno = PatternFill(start_color="1F6F43", end_color="1F6F43", fill_type="solid")
    for hoja in workbook.worksheets:
        if hoja.max_row == 0:
            continue
        for celda in hoja[1]:
            celda.font = Font(color="FFFFFF", bold=True)
            celda.fill = relleno
        hoja.freeze_panes = "A2"
        for columna in hoja.columns:
            largo = max((len(str(c.value)) if c.value is not None else 0) for c in columna)
            hoja.column_dimensions[get_column_letter(columna[0].column)].width = min(max(largo + 2, 10), 45)


def reporte_excel():
    """Libro con la meta, lo que quedó fuera de ella, cada cédula única, y los eventos por usuario."""
    personas = _personas_unicas()
    meta = reporte_meta(personas)
    usuarios, totales = resumen_por_usuario()

    filas_meta = []
    for f in meta["filas"]:
        fila = {"Municipio": f["municipio"], "Género": f["genero"]}
        for r in RANGOS:
            c = f["rangos"][r]
            fila[f"{r} meta"], fila[f"{r} logrado"], fila[f"{r} %"] = c["meta"], c["logrado"], c["porcentaje"]
        t = f["total"]
        fila["Total meta"], fila["Total logrado"], fila["Total %"] = t["meta"], t["logrado"], t["porcentaje"]
        filas_meta.append(fila)
    tg = meta["total_general"]
    fila = {"Municipio": "TOTAL", "Género": ""}
    for r in RANGOS:
        c = tg["rangos"][r]
        fila[f"{r} meta"], fila[f"{r} logrado"], fila[f"{r} %"] = c["meta"], c["logrado"], c["porcentaje"]
    fila["Total meta"], fila["Total logrado"], fila["Total %"] = (
        tg["total"]["meta"],
        tg["total"]["logrado"],
        tg["total"]["porcentaje"],
    )
    filas_meta.append(fila)

    fuera = meta["fuera_de_meta"]
    resumen = [
        {"Indicador": "Personas únicas (por cédula)", "Valor": meta["personas_unicas"]},
        {"Indicador": "Cuentan en la meta", "Valor": meta["en_meta"]},
        {"Indicador": "Fuera de meta: municipio que no es de los 4 objetivo", "Valor": fuera["otro_municipio"]},
        {"Indicador": "Fuera de meta: género Otro o sin dato", "Valor": fuera["genero_no_clasificable"]},
        {"Indicador": "Fuera de meta: sin edad", "Valor": fuera["sin_edad"]},
        {"Indicador": "Avance efectivo de la meta (%)", "Valor": meta["avance_efectivo"]},
    ]
    for metodo, n in meta["clasificacion_municipio"].items():
        resumen.append({"Indicador": f"Municipio por coincidencia '{metodo}' (de los que cuentan)", "Valor": n})

    etiquetas = {
        "en_meta": "En meta",
        "otro_municipio": "Municipio fuera de los 4 objetivo",
        "genero_no_clasificable": "Género Otro o sin dato",
        "sin_edad": "Sin edad",
    }
    cedulas = []
    for p in sorted(personas, key=lambda p: p["persona"].numero_documento):
        estado, rango, genero = _estado_persona(p)
        cedulas.append(
            {
                "Cédula": p["persona"].numero_documento,
                "Tipo": p["persona"].tipo_documento,
                "Nombre": p["persona"].nombre,
                "Género": genero,
                "Municipio escrito": p["municipio_texto"],
                "Municipio objetivo": p["municipio"],
                "Coincidencia": p["metodo"],
                "Edad": p["edad"],
                "Rango de edad": rango,
                "Eventos en que aparece": p["eventos"],
                "Estado frente a la meta": etiquetas[estado],
            }
        )

    por_usuario = [
        {
            "Usuario": u["nombre"],
            "Email": u["email"],
            "Rol": u["rol"],
            "Eventos": u["eventos"],
            "Asistencias": u["asistencias"],
            "Personas distintas": u["personas_unicas"],
            "Primer evento subido": _sin_tz(u["primer_evento"]),
            "Último evento subido": _sin_tz(u["ultimo_evento"]),
        }
        for u in usuarios
    ]
    por_usuario.append(
        {
            "Usuario": "TOTAL",
            "Eventos": totales["eventos"],
            "Asistencias": totales["asistencias"],
            "Personas distintas": totales["personas_unicas"],
        }
    )

    eventos = []
    for e in Evento.objects.select_related("registrado_por").annotate(n=Count("asistentes")).order_by("-created_at"):
        eventos.append(
            {
                "ID evento": e.id,
                "Usuario": e.registrado_por.name if e.registrado_por else "(sin dueño)",
                "Tema": e.tema,
                "Fecha del evento": e.fecha,
                "Lugar": e.lugar,
                "Responsable": e.responsable,
                "Asistentes": e.n,
                "Subido el": _sin_tz(e.created_at),
                "Con documento escaneado": "Sí" if e.documento_escaneado else "No",
            }
        )

    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        pd.DataFrame(filas_meta).to_excel(writer, index=False, sheet_name="Meta vs logrado")
        pd.DataFrame(resumen).to_excel(writer, index=False, sheet_name="Resumen y fuera de meta")
        pd.DataFrame(cedulas).to_excel(writer, index=False, sheet_name="Cédulas únicas")
        pd.DataFrame(por_usuario).to_excel(writer, index=False, sheet_name="Resumen por usuario")
        pd.DataFrame(eventos).to_excel(writer, index=False, sheet_name="Eventos")
        _formatear_libro(writer.book)
    return salida.getvalue()
