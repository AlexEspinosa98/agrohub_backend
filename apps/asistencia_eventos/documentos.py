"""Tipo de documento de los asistentes: lo escrito en la hoja si viene, y si no, se infiere por edad.

La hoja trae "Tipo y número de documento" en una sola celda, y al LLM no se le pide el tipo
por separado (pedírselo corría los demás campos una columna, ver ocr_service). Acá se resuelve
después, en código:
  1. si junto al número viene un prefijo reconocible ("CC 1081...", "T.I. 1004...") se separa
     y se respeta, porque es lo que escribió la persona;
  2. si no hay tipo escrito pero hay edad: 18 o más -> CC, menos de 18 -> TI;
  3. sin tipo ni edad se asigna CC por defecto (siempre debe quedar un tipo; la revisión lo corrige).
La inferencia por edad es una aproximación (un menor de 7 tendría registro civil, un extranjero
CE/PEP), por eso un tipo escrito en la hoja siempre gana y el paso de revisión humana lo puede
corregir."""
import re

MAYORIA_DE_EDAD = 18

_PREFIJO_RE = re.compile(
    r"^\s*(c\.?\s?c\.?|t\.?\s?i\.?|c\.?\s?e\.?|r\.?\s?c\.?|p\.?\s?e\.?\s?p\.?|p\.?\s?p\.?\s?t\.?|p\.?\s?a\.?)"
    r"\s*[:.\-]?\s*(\d[\d.\s]*)$",
    re.IGNORECASE,
)
_VALIDOS = {"CC", "TI", "CE", "RC", "PEP", "PPT", "PA"}


def normalizar_tipo(valor):
    """'c.c.' / 'cc ' / 'T.I' -> 'CC' / 'TI'. Devuelve None si no es un tipo reconocible."""
    if not valor:
        return None
    limpio = re.sub(r"[\s.]", "", str(valor)).upper()
    return limpio if limpio in _VALIDOS else None


def separar_tipo_y_numero(valor):
    """('CC 1.081.806.419') -> ('CC', '1081806419'). Sin prefijo devuelve (None, valor tal cual)."""
    if not valor:
        return None, valor
    coincide = _PREFIJO_RE.match(str(valor))
    if not coincide:
        return None, valor
    return normalizar_tipo(coincide.group(1)), re.sub(r"\D", "", coincide.group(2))


def inferir_tipo(edad, tipo_actual=None):
    """El tipo ya conocido (normalizado) gana; si no hay, se infiere por edad; si tampoco, CC."""
    tipo = normalizar_tipo(tipo_actual)
    if tipo:
        return tipo
    if isinstance(edad, int) and not isinstance(edad, bool):
        return "CC" if edad >= MAYORIA_DE_EDAD else "TI"
    return "CC"


def completar_tipo_documento(asistente):
    """Muta un dict de asistente (forma del OCR / del payload de guardado): separa un prefijo de
    tipo pegado al número y completa `tipo_documento` por edad si hace falta."""
    tipo_escrito, numero = separar_tipo_y_numero(asistente.get("numero_documento"))
    if numero is not None:
        asistente["numero_documento"] = numero
    asistente["tipo_documento"] = inferir_tipo(
        asistente.get("edad"), asistente.get("tipo_documento") or tipo_escrito
    )
    return asistente
