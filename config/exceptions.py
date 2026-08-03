import logging

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _lookup_value(data, path):
    current = data
    for part in path:
        try:
            current = current[part] if isinstance(part, int) else current.get(part)
        except (KeyError, IndexError, TypeError, AttributeError):
            return None
    return current


def _miembro_context(path, body):
    """If the error belongs to miembros[i].<campo>, attach which household
    member it refers to — mirrors main.py's validation_exception_handler so
    a client can identify the exact row without counting list indexes."""
    if len(path) < 2 or path[0] != "miembros" or not isinstance(path[1], int):
        return {}
    miembros = body.get("miembros") if isinstance(body, dict) else None
    miembro = miembros[path[1]] if isinstance(miembros, list) and path[1] < len(miembros) else None
    if not isinstance(miembro, dict):
        return {}
    return {
        "miembro_index": path[1],
        "miembro_cedula": miembro.get("cedula_participante"),
        "miembro_nombre": miembro.get("nombre_participante"),
    }


def _flatten(detail, body, path=()):
    errors = []
    if isinstance(detail, dict):
        for key, value in detail.items():
            errors.extend(_flatten(value, body, path + (key,)))
    elif isinstance(detail, list):
        if detail and isinstance(detail[0], (dict, list)):
            for index, item in enumerate(detail):
                errors.extend(_flatten(item, body, path + (index,)))
        else:
            for item in detail:
                errors.append(_build_entry(path, item, body))
    else:
        errors.append(_build_entry(path, detail, body))
    return errors


def _build_entry(path, error_detail, body):
    entry = {
        "campo": ".".join(str(p) for p in path),
        "mensaje": str(error_detail),
        "tipo_error": getattr(error_detail, "code", None) or "invalid",
        "valor_recibido": _lookup_value(body, path),
    }
    entry.update(_miembro_context(path, body))
    return entry


def agrohub_exception_handler(exc, context):
    """Project-wide DRF exception handler.

    Reproduces main.py's two FastAPI handlers from the old backend:
    - RequestValidationError -> detailed per-field 422 JSON.
    - Anything else unhandled -> generic JSON 500 (never an HTML/plaintext
      error page, never an unhandled 500 with no body).
    Everything DRF already turns into {"detail": "..."} (auth/permission/404/
    etc.) is left as-is — that already matches FastAPI's HTTPException shape.
    """
    if isinstance(exc, ValidationError):
        request = context.get("request")
        body = getattr(request, "data", None) if request is not None else None
        if not isinstance(body, dict):
            body = {}
        errores = _flatten(exc.detail, body)
        return Response(
            {
                "status": 422,
                "message": "Datos inválidos en la solicitud",
                "total_errores": len(errores),
                "errores": errores,
            },
            status=422,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    logger.error("Error no controlado en %s: %s", getattr(request, "path", "?"), exc, exc_info=True)
    return Response(
        {"status": 500, "message": "Error interno del servidor. Intente nuevamente."},
        status=500,
    )
