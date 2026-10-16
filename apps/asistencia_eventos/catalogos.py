"""Catálogos de apoyo de asistencia_eventos."""

import difflib
import unicodedata

# Comunidades/pueblos indígenas SUGERIDOS para el desplegable cuando pertenencia_etnica="indigena".
# Es una lista de sugerencias, no una restricción: PersonaAsistente.comunidad acepta cualquier texto
# (un pueblo que no esté acá se puede escribir igual, o elegir "Otra"). Se ajusta editando esta lista.
COMUNIDADES_INDIGENAS_SUGERIDAS = [
    "Arhuaco",
    "Kogui",
    "Wiwa",
    "Kankuamo",
    "Zenú",
    "Wayuú",
    "Chimila (Ette Ennaka)",
    "Otra",
]

_POR_MINUSCULA = {c.lower(): c for c in COMUNIDADES_INDIGENAS_SUGERIDAS}


def normalizar_comunidad(valor):
    """Limpia espacios; si coincide (sin importar mayúsculas) con una sugerida, devuelve la forma
    canónica ("kogui" -> "Kogui"); si no, respeta lo escrito. Vacío -> None."""
    if valor is None:
        return None
    limpio = " ".join(str(valor).split())
    if not limpio:
        return None
    return _POR_MINUSCULA.get(limpio.lower(), limpio)


# Municipios de la población objetivo del proyecto (ver reportes.META_POBLACION_OBJETIVO).
MUNICIPIOS_OBJETIVO = ["Algarrobo", "Aracataca", "Fundación", "El Retén"]


def clave_texto(valor):
    """Forma comparable de un texto: sin tildes, en minúsculas y solo letras
    ("  Fundación, Mag. " -> "fundacionmag")."""
    s = unicodedata.normalize("NFKD", (valor or "").casefold())
    return "".join(c for c in s if c.isalpha() and not unicodedata.combining(c))


_CLAVE_A_MUNICIPIO = {clave_texto(m): m for m in MUNICIPIOS_OBJETIVO}
_CLAVE_A_MUNICIPIO["reten"] = "El Retén"  # así se escribe casi siempre en la hoja


def clasificar_municipio(valor):
    """Intenta llevar un municipio escrito a mano a uno de MUNICIPIOS_OBJETIVO.

    Devuelve (municipio_objetivo | None, metodo). Métodos, de más a menos confiable:
    - "exacto": igual sin importar tildes, mayúsculas ni espacios ("fundacion", "RETÉN").
    - "aproximado": error de ortografía/OCR ("Fondacion", "Algarobo", "Arauataca").
    - "contiene": el texto trae el nombre dentro de otra frase ("Biblioteca Algarrobo") — es el
      menos seguro porque puede ser el lugar del evento y no el municipio de la persona.
    - "vacio" / "ninguno": no había texto / no se pudo asociar a ningún municipio objetivo.
    """
    clave = clave_texto(valor)
    if not clave:
        return None, "vacio"
    if clave in _CLAVE_A_MUNICIPIO:
        return _CLAVE_A_MUNICIPIO[clave], "exacto"
    cercanos = difflib.get_close_matches(clave, list(_CLAVE_A_MUNICIPIO), n=1, cutoff=0.8)
    # Un error de ortografía cambia pocas letras; si el texto es bastante más largo que el municipio
    # ("Seno Fundacion") no es un typo sino otra cosa que lo contiene, y cae en "contiene".
    if cercanos and abs(len(clave) - len(cercanos[0])) <= 3:
        return _CLAVE_A_MUNICIPIO[cercanos[0]], "aproximado"
    for k, municipio in _CLAVE_A_MUNICIPIO.items():
        if len(k) >= 6 and k in clave:  # "reten" (5) queda fuera: aparece dentro de otras palabras
            return municipio, "contiene"
    return None, "ninguno"
