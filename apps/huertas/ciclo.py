"""Reglas del ciclo del cultivo y del estado de la tierra.

Es un PORTE LITERAL de las funciones del frontend (rama feature/huertas-abiertas):
`momento`, `ajusteDeEtapa`, `sedDeEtapa`, `finDeCiclo` (biblioteca.ts), `cultivoEnEra` (plan.ts) y
`estadoTierra` (lectura.ts). El backend y la web tienen que llegar al mismo umbral y al mismo
estado con los mismos datos: si se cambia una regla aquí, se cambia allá (y al revés).

Trabaja sobre diccionarios con la forma de la ficha (`ficha_dict()` en models.py), no sobre
modelos, para poder probarse sin base de datos.
"""
import math
from dataclasses import dataclass
from datetime import date

# lectura.ts
MARGEN_SECA = 6
MARGEN_ENCHARCADA = 10

# Calibración (HU-HB08): tope de puntos que se pueden sumar o restar al umbral de una cama.
AJUSTE_MAXIMO = 6
PASO_CALIBRACION = 3


@dataclass
class Momento:
    dias: int
    etapa: dict
    indice: int
    avance: float
    crecimiento: float
    faltan: int
    terminado: bool

    def como_dict(self):
        return {
            "dias": self.dias,
            "etapa": self.etapa,
            "indice": self.indice,
            "avance": round(self.avance, 3),
            "crecimiento": round(self.crecimiento, 3),
            "faltan": self.faltan,
            "terminado": self.terminado,
        }


def dias_a_cosecha(ficha):
    return ficha["etapas"][-1]["desde"]


def fin_de_ciclo(ficha):
    return dias_a_cosecha(ficha) + max(ficha["cosecha_dias"], 7)


def momento(ficha, dias):
    """En qué va un cultivo a los `dias` de sembrado (momento() de biblioteca.ts)."""
    d = max(0, dias)
    etapas = ficha["etapas"]
    indice = 0
    for k, etapa in enumerate(etapas):
        if d >= etapa["desde"]:
            indice = k
    etapa = etapas[indice]
    hasta = etapas[indice + 1]["desde"] if indice + 1 < len(etapas) else fin_de_ciclo(ficha)
    cosecha = dias_a_cosecha(ficha)
    adulta = next((e["desde"] for e in etapas if e["tipo"] in ("flor", "fruto")), cosecha)
    return Momento(
        dias=d,
        etapa=etapa,
        indice=indice,
        avance=min(1, (d - etapa["desde"]) / max(1, hasta - etapa["desde"])),
        crecimiento=min(1, 0.25 + (0.75 * d) / max(1, adulta)),
        faltan=max(0, cosecha - d),
        terminado=(not ficha["perenne"]) and d > fin_de_ciclo(ficha),
    )


def ajuste_de_etapa(ficha, tipo):
    """Puntos que se suman al umbral según la etapa (+4 recién sembrado, −4 al final si seca)."""
    if tipo == "inicio":
        return 4
    if tipo == "cosecha" and ficha["secar_al_final"]:
        return -4
    return 0


def sed_de_etapa(ficha, tipo):
    inicio, pleno, fin = ficha["kc"]
    if tipo == "inicio":
        kc = inicio
    elif tipo == "crecimiento":
        kc = (inicio + pleno) / 2
    elif tipo == "cosecha":
        kc = fin
    else:
        kc = pleno
    return ficha["sed"] * max(0.45, kc / pleno)


def dias_desde(sembrado_el, hoy=None):
    """Días cumplidos desde la siembra (en hora de Colombia), o None si no se sabe."""
    if sembrado_el is None:
        return None
    hoy = hoy or date.today()
    return max(0, (hoy - sembrado_el).days)


def umbral_de_cama(ficha, dias, ajuste):
    """Umbral con el que el riego abre y cierra en una cama (cultivoEnEra() de plan.ts):
    ficha + ajuste de la etapa + calibración. Sin fecha de siembra se asume plena carga."""
    tipo = "fruto" if dias is None else momento(ficha, dias).etapa["tipo"]
    puntos = ajuste_de_etapa(ficha, tipo) + ajuste
    return {
        "abrir": ficha["abrir"] + puntos,
        "cerrar": ficha["cerrar"] + puntos,
        "sed": round(sed_de_etapa(ficha, tipo), 3),
        "etapa": tipo,
    }


def estado_tierra(humedad, abrir, cerrar, riego=False, descanso=False):
    """Estado con nombre de la tierra (estadoTierra() de lectura.ts)."""
    if humedad is None:
        return None
    if descanso:
        return "bien"
    if humedad > cerrar + MARGEN_ENCHARCADA:
        return "encharcada"
    if humedad < abrir - MARGEN_SECA:
        return "seca"
    if riego and humedad < cerrar:
        return "regando"
    if humedad < abrir:
        return "pidiendo"
    return "bien"


TIERRA_TITULO = {
    "seca": "Tierra seca",
    "pidiendo": "Pide agua",
    "regando": "Regándose",
    "bien": "A gusto",
    "encharcada": "Encharcada",
    "sinEfecto": "El agua no llega",
}


def edad_texto(dias):
    """edadTexto() de biblioteca.ts: "hoy", "1 día", "9 días", "7 semanas", "8 meses"."""
    d = max(0, _redondear(dias))
    if d == 0:
        return "hoy"
    if d == 1:
        return "1 día"
    if d < 14:
        return f"{d} días"
    if d < 90:
        return f"{_redondear(d / 7)} semanas"
    meses = _redondear(d / 30)
    return "1 mes" if meses == 1 else f"{meses} meses"


def _redondear(x):
    """Math.round de JavaScript (los .5 suben); round() de Python redondea al par."""
    return math.floor(x + 0.5)


def vecindad(a, b):
    """vecindad() de biblioteca.ts: cómo se llevan dos cultivos en camas vecinas."""
    if a["id"] == b["id"]:
        return "neutral"
    if b["id"] in a["evitar"] or a["id"] in b["evitar"]:
        return "evitar"
    if b["id"] in a["amigas"] or a["id"] in b["amigas"]:
        return "amigas"
    if a["familia"] == b["familia"]:
        return "familia"
    return "neutral"
