import json
import tempfile
from io import StringIO

from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.user_activity.contrasenas import sha256, verify_password
from apps.user_activity.models import User

CLAVE = "clave-de-prueba"


@override_settings(IDENTIDAD_CLAVE=CLAVE)
class IdentidadTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        # Cuenta vieja del panel: contraseña SHA-256 sin sal, como estaban todas
        self.vieja = User.objects.create(
            name="Ana Panel", phone="3001112233", identification="1010", email="ana@ejemplo.co",
            password_hash=sha256("vieja-123"), role="user",
        )

    def post(self, ruta, datos, clave=CLAVE):
        return self.c.post(f"/user-activity/identidad/{ruta}", datos, format="json", HTTP_X_IDENTIDAD_CLAVE=clave)

    def test_sin_clave_no_entra(self):
        self.assertEqual(self.post("verificar", {"identificador": "1010", "password": "vieja-123"}, clave="otra").status_code, 403)
        with override_settings(IDENTIDAD_CLAVE=""):
            self.assertEqual(self.post("verificar", {"identificador": "1010", "password": "x"}).status_code, 404)

    def test_login_viejo_se_convierte_a_argon2(self):
        r = self.c.post("/user-activity/users/login", {"phone_or_identification": "ANA@ejemplo.co", "password": "vieja-123"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.vieja.refresh_from_db()
        self.assertTrue(self.vieja.password_hash.startswith("argon2"))
        # Y sigue entrando con la misma contraseña, ahora por teléfono
        r = self.c.post("/user-activity/users/login", {"phone_or_identification": "3001112233", "password": "vieja-123"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_verificar_por_telefono_cedula_o_correo(self):
        for ident in ("3001112233", "1010", "ana@ejemplo.co"):
            r = self.post("verificar", {"identificador": ident, "password": "vieja-123"})
            self.assertEqual(r.json()["data"]["id"], self.vieja.id)
        self.assertEqual(self.post("verificar", {"identificador": "1010", "password": "mala"}).status_code, 401)

    def test_registrar_desde_la_red_social(self):
        r = self.post("registrar", {"email": "Nuevo@Ejemplo.co", "password": "Segura-2026!", "name": "Nuevo"})
        self.assertEqual(r.status_code, 201)
        u = User.objects.get(email="nuevo@ejemplo.co")
        self.assertIsNone(u.phone)
        self.assertTrue(u.password_hash.startswith("argon2"))
        # Entra al panel con correo y la misma contraseña
        r = self.c.post("/user-activity/users/login", {"phone_or_identification": "nuevo@ejemplo.co", "password": "Segura-2026!"}, format="json")
        self.assertEqual(r.status_code, 200)
        # Mismo correo con otra contraseña: no se apropia la cuenta
        self.assertEqual(self.post("registrar", {"email": "nuevo@ejemplo.co", "password": "otra", "name": "X"}).status_code, 409)
        # Mismo correo y misma contraseña: se enlaza
        self.assertEqual(self.post("registrar", {"email": "nuevo@ejemplo.co", "password": "Segura-2026!", "name": "X"}).status_code, 200)

    def test_cambiar_contrasena(self):
        r = self.post(f"usuarios/{self.vieja.id}/contrasena", {"password": "nueva-456"})
        self.assertEqual(r.status_code, 200)
        self.vieja.refresh_from_db()
        self.assertTrue(verify_password("nueva-456", self.vieja.password_hash))
        self.assertFalse(verify_password("vieja-123", self.vieja.password_hash))

    def test_completar_en_el_panel_una_cuenta_de_la_red_social(self):
        self.post("registrar", {"email": "red@ejemplo.co", "password": "Segura-2026!", "name": "Red"})
        r = self.c.post("/user-activity/users/register", {
            "name": "Red", "phone": "3009998877", "identification": "2020", "email": "red@ejemplo.co", "password": "Segura-2026!",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(User.objects.filter(email="red@ejemplo.co").count(), 1)
        self.assertEqual(User.objects.get(email="red@ejemplo.co").phone, "3009998877")

    def test_importar_usuarios_de_la_red_social(self):
        social_hash = make_password("de-la-red")
        filas = [
            {"social_id": "u-1", "email": "ana@ejemplo.co", "nombre": "Ana", "password": social_hash, "estado": "active"},
            {"social_id": "u-2", "email": "solo.red@ejemplo.co", "nombre": "Solo Red", "password": social_hash, "estado": "active"},
            {"social_id": "u-3", "email": "borrado@ejemplo.co", "nombre": "B", "password": social_hash, "estado": "purged"},
            {"social_id": "u-4", "email": "en.borrado@ejemplo.co", "nombre": "C", "password": social_hash, "estado": "deleted"},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(filas, f)
        salida = f.name + ".mapa"
        call_command("identidad_importar", f.name, "--salida", salida, stdout=StringIO())  # vista previa
        self.assertFalse(User.objects.filter(email="solo.red@ejemplo.co").exists())
        call_command("identidad_importar", f.name, "--salida", salida, "--aplicar", stdout=StringIO())
        call_command("identidad_importar", f.name, "--salida", salida, "--aplicar", stdout=StringIO())  # idempotente
        mapa = {m["social_id"]: m for m in json.load(open(salida))}
        self.assertEqual(mapa["u-1"]["identity_id"], self.vieja.id)
        self.assertNotIn("u-3", mapa)
        self.assertNotIn("u-4", mapa)
        self.assertFalse(User.objects.filter(email="en.borrado@ejemplo.co").exists())
        self.assertEqual(User.objects.filter(email="solo.red@ejemplo.co").count(), 1)
        # Ana entra con cualquiera de las dos hasta el primer login; luego queda la que usó
        self.assertEqual(self.post("verificar", {"identificador": "ana@ejemplo.co", "password": "de-la-red"}).status_code, 200)
        self.assertEqual(self.post("verificar", {"identificador": "ana@ejemplo.co", "password": "vieja-123"}).status_code, 401)
        # La persona que solo estaba en la red social entra al panel con su contraseña de siempre
        r = self.c.post("/user-activity/users/login", {"phone_or_identification": "solo.red@ejemplo.co", "password": "de-la-red"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_persona_incluye_municipio_de_su_asociacion(self):
        from apps.user_activity.models import Association
        self.vieja.association = Association.objects.create(name="ASOCAD", municipality="Aracataca")
        self.vieja.save()
        r = self.post("verificar", {"identificador": "1010", "password": "vieja-123"})
        self.assertEqual(r.json()["data"]["municipio"], "Aracataca")
