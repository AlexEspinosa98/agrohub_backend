"""Recomendaciones por reglas fijas y explicables (porte de `recomendar()` en recomendaciones.ts).

No usan el modelo de lenguaje: cada una dice de dónde sale. El backend las necesita para:
- proponer calibraciones (HU-HB08), que nunca se aplican solas: las acepta quien cuida la huerta;
- dárselas al modelo como contexto del seguimiento (HU-HB06).

Las reglas que dependen del diagnóstico en vivo de los sensores (hábito de riego) se quedan en el
frontend; aquí van las que salen del plan, la biblioteca y los reportes.
"""
from datetime import timedelta

from django.utils import timezone

from apps.huertas import ciclo

VENTANA_DIAS = 21
PLAGA_TEXTO = {"hojas": "Hojas comidas", "manchas": "Hojas con manchas", "bichos": "Bichos en las matas"}


def _cap(texto):
    return texto[:1].upper() + texto[1:]


def recomendar(camas, reportes, ahora=None):
    """`camas`: lista de cama_dict() (plan.py) con la ficha en `_ficha`. `reportes`: Reporte
    visibles, del más reciente al más antiguo. Devuelve dicts con id, nivel, titulo, texto, porque
    y, si aplica, accion {tipo, zona, puntos}."""
    ahora = ahora or timezone.now()
    lista = []
    recientes = [r for r in reportes if ahora - r.creado_en < timedelta(days=VENTANA_DIAS)]

    def nombre_cama(c):
        return f"la cama de {c['_ficha']['nombre'].lower()}"

    for i, c in enumerate(camas):
        if c["libre"]:
            continue
        ficha, m = c["_ficha"], c["momento"]
        if m and m["terminado"]:
            lista.append({
                "id": f"fin-{c['zona']}", "nivel": "atencion",
                "titulo": f"{_cap(nombre_cama(c))} ya cumplió su ciclo",
                "texto": "Recoge lo que quede y deja libre la cama para rotar.",
                "porque": f"Lleva {ciclo.edad_texto(m['dias'])} de sembrada; el ciclo dura unos {ciclo.edad_texto(ciclo.fin_de_ciclo(ficha))}.",
                "accion": {"tipo": "liberar", "zona": c["zona"]},
            })
        elif m and m["etapa"]["tipo"] == "cosecha" and not c["cosechando_marcado"]:
            lista.append({
                "id": f"cosecha-{c['zona']}", "nivel": "bien",
                "titulo": f"{_cap(nombre_cama(c))} ya debería estar para cosecha",
                "texto": ficha["senal"], "porque": f"Lleva {ciclo.edad_texto(m['dias'])} de sembrada.",
                "accion": {"tipo": "cosechar", "zona": c["zona"]},
            })
        elif m and 0 < m["faltan"] <= 10:
            extra = " Desde ahora le conviene un poco menos de agua." if ficha["secar_al_final"] else ""
            lista.append({
                "id": f"casi-{c['zona']}", "nivel": "bien",
                "titulo": f"A {nombre_cama(c)} le falta poco",
                "texto": f"{ficha['senal']}{extra}", "porque": f"Faltan unos {m['faltan']} días para la primera cosecha.",
            })

        de_la_cama = [r for r in recientes if r.cama_id and r.cama.zona == c["zona"]]
        secas = sum(1 for r in de_la_cama if r.tierra == "seca" and r.sensor in ("bien", "regando"))
        mojadas = sum(1 for r in de_la_cama if r.tierra == "encharcada" and r.sensor == "bien")
        if secas >= 2 and c["ajuste"] <= 0:
            lista.append(_calibracion(c, nombre_cama(c), +ciclo.PASO_CALIBRACION, secas))
        elif mojadas >= 2 and c["ajuste"] >= 0:
            lista.append(_calibracion(c, nombre_cama(c), -ciclo.PASO_CALIBRACION, mojadas))

        vecina = camas[i + 1] if i + 1 < len(camas) else None
        if vecina and not vecina["libre"] and ciclo.vecindad(ficha, vecina["_ficha"]) == "evitar":
            lista.append({
                "id": f"vecinas-{c['zona']}", "nivel": "bien",
                "titulo": f"{ficha['nombre']} y {vecina['_ficha']['nombre'].lower()} no son buenas vecinas",
                "texto": "Se pasan plagas o se quitan fuerza. En la próxima siembra conviene separarlas con otra cama.",
                "porque": "Biblioteca de cultivos: vecinas que es mejor evitar.",
            })

    con_plaga = next((r for r in recientes if r.plaga != "no" and ahora - r.creado_en < timedelta(days=10)), None)
    if con_plaga:
        cama = next((c for c in camas if con_plaga.cama_id and c["zona"] == con_plaga.cama.zona and not c["libre"]), None)
        comunes = ""
        if cama and cama["_ficha"]["plagas"]:
            comunes = f"En {cama['_ficha']['nombre'].lower()} lo más común es: {', '.join(p.lower() for p in cama['_ficha']['plagas'])}. "
        lista.append({
            "id": f"plaga-{con_plaga.id}", "nivel": "atencion",
            "titulo": PLAGA_TEXTO.get(con_plaga.plaga, "Plaga") + (f" en {nombre_cama(cama)}" if cama else ""),
            "texto": f"{comunes}Revisa el envés de las hojas temprano, quita a mano lo que veas y saca las hojas enfermas. Si sigue, avísale al equipo técnico.",
            "porque": f"Lo reportaron hace {max(1, round((ahora - con_plaga.creado_en).days))} días.",
        })

    triste = next((r for r in recientes if r.matas == "tristes" and r.sensor == "bien"), None)
    if triste:
        lista.append({
            "id": f"tristes-{triste.id}", "nivel": "atencion",
            "titulo": "Matas tristes con la tierra a gusto",
            "texto": "Si agua no falta, casi siempre es el sol de mediodía, una plaga en la raíz o falta de abono.",
            "porque": "Un reporte dice «tristes» con el sensor en «a gusto».",
        })

    ultimo = reportes[0] if reportes else None
    dias = (ahora - ultimo.creado_en).days if ultimo else None
    if dias is None or dias >= 7:
        lista.append({
            "id": "constancia", "nivel": "atencion" if dias is not None and dias >= 14 else "bien",
            "titulo": "Nadie ha contado cómo va la huerta" if dias is None else f"Hace {dias} días nadie cuenta cómo va la huerta",
            "texto": "Un reporte por semana basta. Con eso el riego se va afinando y las recomendaciones salen mejor.",
            "porque": "Se sugiere un reporte cada 7 días.",
            "accion": {"tipo": "reportar"},
        })

    peso = {"urgente": 3, "atencion": 2, "sinDato": 1, "bien": 0}
    return sorted(lista, key=lambda r: -peso[r["nivel"]])[:6]


def _calibracion(cama, nombre, puntos, n):
    mas = puntos > 0
    nuevo = cama["ajuste"] + puntos
    propuesta = {
        "id": f"calibrar-{'mas' if mas else 'menos'}-{cama['zona']}", "nivel": "atencion",
        "titulo": f"{_cap(nombre)} necesita más agua de la que marca el sensor" if mas
        else f"A {nombre} le está llegando agua de más",
        "texto": (
            "La gente la encuentra seca cuando el sensor dice que está a gusto. Conviene que el riego abra un poco antes."
            if mas else
            "La gente la encuentra encharcada cuando el sensor dice que está a gusto. Conviene que el riego cierre un poco antes."
        ),
        "porque": f"{n} reportes en {VENTANA_DIAS} días dicen «{'seca' if mas else 'encharcada'}» con el sensor en «a gusto».",
        "accion": {"tipo": "calibrar", "zona": cama["zona"], "puntos": puntos, "ajuste_resultante": nuevo},
    }
    if abs(nuevo) > ciclo.AJUSTE_MAXIMO:
        # Más allá del tope no se propone: puede ser el sensor.
        propuesta.pop("accion")
        propuesta["texto"] += " Ya se calibró hasta el tope: puede ser el sensor. Avisa al equipo técnico."
        propuesta["avisar_equipo"] = True
    return propuesta
