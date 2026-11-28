"""Contraseñas de la identidad única de AgroHub (panel, bitácora, huertas y red social).

Historia: este backend guardaba SHA-256 sin sal (64 caracteres hex). Desde la unificación:
- toda contraseña nueva se guarda con los hashers de Django (Argon2id primero, ver
  PASSWORD_HASHERS en settings), el mismo formato que usa la red social;
- una contraseña vieja (SHA-256) se sigue aceptando y se convierte sola a Argon2 la próxima vez
  que esa persona inicia sesión: nadie tiene que cambiarla;
- `password_hash_alt` guarda la contraseña de la red social de quien tenía cuenta en los dos
  lados: se aceptan ambas hasta su primer inicio de sesión, y la que use queda como la única.
"""
import hashlib
import hmac
import re

from django.contrib.auth.hashers import check_password, identify_hasher, make_password

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def sha256(texto: str) -> str:
    """Solo para comparar valores heredados y códigos OTP de un solo uso, nunca para contraseñas nuevas."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def es_heredada(hash_guardado: str | None) -> bool:
    return bool(hash_guardado and _SHA256_HEX.match(hash_guardado))


def hash_password(raw: str) -> str:
    return make_password(raw)


def verify_password(raw: str, hash_guardado: str | None) -> bool:
    if not hash_guardado or raw is None:
        return False
    if es_heredada(hash_guardado):
        return hmac.compare_digest(sha256(raw), hash_guardado)
    try:
        return check_password(raw, hash_guardado)
    except ValueError:  # formato desconocido
        return False


def _hay_que_actualizar(hash_guardado: str) -> bool:
    if es_heredada(hash_guardado):
        return True
    try:
        return identify_hasher(hash_guardado).must_update(hash_guardado) or not hash_guardado.startswith("argon2")
    except ValueError:
        return True


def verificar_usuario(user, raw: str) -> bool:
    """¿Es la contraseña de esta persona? Prueba la principal y la de la red social; si la que
    entró es vieja, de la red social o con parámetros viejos, la deja guardada en Argon2."""
    principal_ok = verify_password(raw, user.password_hash)
    alterna_ok = not principal_ok and verify_password(raw, getattr(user, "password_hash_alt", None))
    if not (principal_ok or alterna_ok):
        return False
    campos = []
    if alterna_ok or _hay_que_actualizar(user.password_hash):
        user.password_hash = make_password(raw)
        campos.append("password_hash")
    if getattr(user, "password_hash_alt", None):
        user.password_hash_alt = None  # ya eligió su contraseña: queda una sola
        campos.append("password_hash_alt")
    if campos:
        user.save(update_fields=campos)
    return True
