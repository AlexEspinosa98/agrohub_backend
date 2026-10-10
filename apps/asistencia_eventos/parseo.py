"""Conversión de fecha/hora tal como las escribe la hoja a date/time."""
from dateutil import parser as dateutil_parser


def parse_fecha_ocr(texto):
    """El OCR devuelve la fecha/hora tal como aparecen escritas en la hoja (ej. "28/08/2026",
    "8:30 am") — el flujo normal (/scan → revisión humana → /eventos) confía en que el frontend
    las convierta a los formatos que esperan DateField/TimeField (ISO) al armar el payload de
    confirmación. /scan-bulk no tiene ese paso humano, así que hace esa conversión aquí mismo;
    si el texto no es un formato de fecha/hora reconocible, devuelve None en vez de fallar —
    EventoConfirmSerializer ya acepta fecha/hora_inicio/hora_final en null."""
    if not texto:
        return None
    try:
        return dateutil_parser.parse(texto, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def parse_hora_ocr(texto):
    if not texto:
        return None
    try:
        return dateutil_parser.parse(texto).time()
    except (ValueError, OverflowError):
        return None
