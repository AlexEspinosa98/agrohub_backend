"""Catálogos de apoyo de asistencia_eventos."""

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
