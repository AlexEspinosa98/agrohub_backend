"""Administra credenciales y ACLs de Mosquitto — mismo mecanismo que ya usa
mosquitto/agregar_gateway.sh y la API FastAPI del repo mqtt_agrohub (portado aquí porque las
APIs de administración se incorporaron a este backend, ver apps.riego_iot). Cada gateway solo
puede tocar su propio namespace — ver mqtt_agrohub/docs/TOPICS.md para el porqué de cada tópico.

Requiere que el proceso de Django pueda:
  1. Escribir en RIEGO_IOT_MOSQUITTO_PASSWD_FILE y RIEGO_IOT_MOSQUITTO_ACL_FILE (permisos de
     grupo — ver el README de mqtt_agrohub, sección "Permisos que necesita").
  2. Ejecutar `sudo systemctl reload mosquitto` sin contraseña — una regla de sudoers acotada a
     ESE comando exacto. Sin esto, los cambios quedan escritos en disco pero Mosquitto no los
     toma hasta el próximo reinicio manual.
"""
import logging
import re
import subprocess

from django.conf import settings

logger = logging.getLogger(__name__)


class MosquittoAdminError(Exception):
    pass


def _bloque_acl(client_id, device_id):
    return (
        f"\n# --- {client_id} ({device_id}) ---\n"
        f"user {client_id}\n"
        f"topic write ahub/{device_id}/data\n"
        f"topic write ahub/{device_id}/valvulas/state\n"
        f"topic write ahub/{device_id}/health\n"
        f"topic write ahub/{device_id}/status\n"
        f"topic read  ahub/{device_id}/control/valvulas\n"
        f"topic read  iotunimagdalena/cloud/health\n"
    )


def _recargar_mosquitto():
    resultado = subprocess.run(
        ["sudo", "-n", "systemctl", "reload", "mosquitto"],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise MosquittoAdminError(
            f"No se pudo recargar Mosquitto (código {resultado.returncode}): "
            f"{resultado.stderr.strip()}. Verifica la regla de sudoers — ver README de mqtt_agrohub."
        )


def _existe_en_acl(client_id):
    try:
        with open(settings.RIEGO_IOT_MOSQUITTO_ACL_FILE) as f:
            contenido = f.read()
    except FileNotFoundError:
        return False
    return re.search(rf"^user {re.escape(client_id)}$", contenido, re.MULTILINE) is not None


def crear_credencial(client_id, device_id, password):
    if _existe_en_acl(client_id):
        raise MosquittoAdminError(f"Ya existe una credencial para '{client_id}'.")

    resultado = subprocess.run(
        ["mosquitto_passwd", "-b", settings.RIEGO_IOT_MOSQUITTO_PASSWD_FILE, client_id, password],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise MosquittoAdminError(f"mosquitto_passwd falló: {resultado.stderr.strip()}")

    with open(settings.RIEGO_IOT_MOSQUITTO_ACL_FILE, "a") as f:
        f.write(_bloque_acl(client_id, device_id))

    _recargar_mosquitto()
    logger.info("credencial creada: client_id=%s device_id=%s", client_id, device_id)


def eliminar_credencial(client_id):
    resultado = subprocess.run(
        ["mosquitto_passwd", "-D", settings.RIEGO_IOT_MOSQUITTO_PASSWD_FILE, client_id],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise MosquittoAdminError(f"mosquitto_passwd -D falló: {resultado.stderr.strip()}")

    with open(settings.RIEGO_IOT_MOSQUITTO_ACL_FILE) as f:
        contenido = f.read()
    nuevo_contenido = re.sub(
        rf"\n# --- {re.escape(client_id)} \([^)]*\) ---\nuser {re.escape(client_id)}\n"
        rf"(?:topic .+\n)+",
        "",
        contenido,
    )
    with open(settings.RIEGO_IOT_MOSQUITTO_ACL_FILE, "w") as f:
        f.write(nuevo_contenido)

    _recargar_mosquitto()
    logger.info("credencial eliminada: client_id=%s", client_id)


def rotar_password(client_id, password_nuevo):
    resultado = subprocess.run(
        ["mosquitto_passwd", "-b", settings.RIEGO_IOT_MOSQUITTO_PASSWD_FILE, client_id, password_nuevo],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise MosquittoAdminError(f"mosquitto_passwd falló: {resultado.stderr.strip()}")
    _recargar_mosquitto()
    logger.info("password rotado: client_id=%s", client_id)
