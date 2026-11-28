"""Importa a la identidad única los usuarios de la red social (AgroHub Social).

Entrada: JSON exportado de la red social, una lista de
    {"social_id": "<uuid>", "email": "...", "nombre": "...", "password": "<hash Django>", "estado": "active"}
Salida (stdout o --salida): la lista {"social_id", "identity_id", "accion"} para enlazar cada
cuenta de la red social con su persona aquí.

Reglas:
- mismo correo que alguien de aquí → es la misma persona: se enlaza; si su contraseña de aquí es
  la vieja (SHA-256) o distinta, la de la red social queda como alterna (se aceptan las dos hasta
  su primer inicio de sesión);
- correo nuevo → se crea la persona con la contraseña de la red social tal cual (mismo formato
  Argon2 de Django), rol user, sin teléfono ni cédula;
- solo se importan cuentas activas: las borradas, suspendidas o purgadas en la red social se
  saltan (no deben ganar acceso al panel por la importación).
Es idempotente: correrlo dos veces no duplica a nadie.

    python manage.py identidad_importar export.json [--salida mapa.json] [--aplicar]
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.user_activity.models import User


class Command(BaseCommand):
    help = "Importa a la identidad única los usuarios exportados de la red social."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument("--salida")
        parser.add_argument("--aplicar", action="store_true", help="Sin esto solo muestra qué haría")

    def handle(self, archivo, salida=None, aplicar=False, **_):
        try:
            filas = json.load(open(archivo, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"No se pudo leer {archivo}: {exc}") from exc
        mapa, cuenta = [], {"enlazada": 0, "creada": 0, "saltada": 0}
        with transaction.atomic():
            for f in filas:
                email = (f.get("email") or "").strip().lower()
                if not email or (f.get("estado") or "active") != "active" or not f.get("password"):
                    cuenta["saltada"] += 1
                    continue
                u = User.objects.filter(email__iexact=email).first()
                if u:
                    accion = "enlazada"
                    if f["password"] != u.password_hash and not u.password_hash_alt:
                        u.password_hash_alt = f["password"]
                        if aplicar:
                            u.save(update_fields=["password_hash_alt"])
                else:
                    accion = "creada"
                    u = User(name=(f.get("nombre") or email.split("@")[0])[:255], email=email,
                             password_hash=f["password"], role="user")
                    if aplicar:
                        u.save()
                cuenta[accion] += 1
                mapa.append({"social_id": f["social_id"], "identity_id": u.id, "accion": accion, "email": email})
            if not aplicar:
                transaction.set_rollback(True)
        texto = json.dumps(mapa, ensure_ascii=False, indent=1)
        if salida:
            open(salida, "w", encoding="utf-8").write(texto)
        self.stdout.write(f"{'Aplicado' if aplicar else 'Vista previa'}: {cuenta}")
