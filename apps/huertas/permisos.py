"""Quién puede hacer qué en una huerta (HU-HB07).

- Equipo (admin, superadmin, investigador): todo en todas las huertas, incluida la configuración
  técnica de las camas (zona del gateway, válvula, sensor) y la asignación de cuidadores.
- Cuidador de ESE AgroHub: plan de siembra, regar sus camas, calibrar y escribir bitácora.
  Nunca: credenciales, alta/baja de gateways, umbrales crudos ni otros AgroHubs.
- Cualquiera (sin sesión): mirar y mandar reportes.
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from apps.huertas.models import Cuidador

ROLES_EQUIPO = ("admin", "superadmin", "investigador")


def autenticado(usuario):
    return bool(getattr(usuario, "is_authenticated", False))


def es_equipo(usuario):
    return autenticado(usuario) and getattr(usuario, "role", None) in ROLES_EQUIPO


def es_cuidador(usuario, agrohub):
    return autenticado(usuario) and Cuidador.objects.filter(agrohub=agrohub, usuario_id=usuario.id).exists()


def puede_cuidar(usuario, agrohub):
    return es_equipo(usuario) or es_cuidador(usuario, agrohub)


def permisos(usuario, agrohub):
    """Lo que la sesión actual puede ver y hacer en esta huerta: el frontend decide qué mostrar."""
    equipo = es_equipo(usuario)
    cuidador = es_cuidador(usuario, agrohub)
    cuida = equipo or cuidador
    return {
        "sesion": autenticado(usuario),
        "rol": getattr(usuario, "role", None) if autenticado(usuario) else None,
        "es_cuidador": cuidador,
        "es_equipo": equipo,
        "ver": True,
        "reportar": True,
        "cambiar_plan": cuida,
        "regar": cuida,
        "calibrar": cuida,
        "escribir_bitacora": cuida,
        "ver_bitacora_del_equipo": cuida,
        "configurar_camas": equipo,
        "asignar_cuidadores": equipo,
        "moderar_reportes": cuida,
        "editar_biblioteca": equipo,
    }


def exigir_cuidar(usuario, agrohub):
    if not autenticado(usuario):
        raise NotAuthenticated("Inicia sesión para cuidar esta huerta (header Authorization: Token <token>).")
    if not puede_cuidar(usuario, agrohub):
        raise PermissionDenied("Solo quien cuida esta huerta o el equipo AgroHub puede hacer esto.")


def exigir_equipo(usuario):
    if not autenticado(usuario):
        raise NotAuthenticated("Falta header Authorization: Token <token>")
    if not es_equipo(usuario):
        raise PermissionDenied("Requiere rol admin, superadmin o investigador.")
