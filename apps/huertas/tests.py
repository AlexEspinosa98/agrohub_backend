import json
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.core.cache import cache
from django.db import connections
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.agrohubs.models import AgroHub
from apps.huertas import ciclo, lecturas, plan, seguimiento
from apps.huertas.models import Cama, Cuidador, Cultivo, Movimiento, Reporte, Seguimiento
from apps.user_activity.models import Logbook, Session, User

def _modelos_riego():
    from apps.riego_iot import models as m

    return [m.Dispositivo, m.LecturaAmbiente, m.LecturaSuelo, m.EstadoValvula, m.Healthcheck]


class BaseHuertas(TestCase):
    databases = {"default", "mqtt"}

    @classmethod
    def setUpClass(cls):
        # Las tablas de riego_iot son managed=False (las crea mqtt_agrohub): en pruebas se crean a
        # mano, antes de que TestCase abra su transacción.
        conexion = connections["mqtt"]
        existentes = conexion.introspection.table_names()
        faltan = [m for m in _modelos_riego() if m._meta.db_table not in existentes]
        if faltan:
            conexion.disable_constraint_checking()
            with conexion.schema_editor() as editor:
                for modelo in faltan:
                    editor.create_model(modelo)
        super().setUpClass()

    def setUp(self):
        cache.clear()
        self.cliente = APIClient()
        self.agrohub = AgroHub.objects.create(
            numero="AH-002", nombre="Algarrobo Los Abuelos", departamento="Magdalena", municipio="Algarrobo",
            es_cabecera_municipal=True, asociaciones=[], cultivos=[], latitud=10.2, longitud=-74.05,
            dispositivo="device0014",
        )
        self.otro = AgroHub.objects.create(
            numero="AH-003", departamento="Magdalena", municipio="Algarrobo", es_cabecera_municipal=True,
            asociaciones=[], cultivos=[], latitud=10.3, longitud=-74.03,
        )
        self.admin = self._usuario("admin", "1")
        self.cuidadora = self._usuario("user", "2")
        self.vecino = self._usuario("user", "3")
        Cuidador.objects.create(agrohub=self.agrohub, usuario=self.cuidadora)

    def _usuario(self, rol, n):
        u = User.objects.create(name=f"Persona {n}", phone=f"30000000{n}", identification=f"10{n}", password_hash="x", role=rol)
        Session.objects.create(user=u, token=f"tok{n}", platform="web")
        return u

    def como(self, usuario):
        self.cliente.credentials(HTTP_AUTHORIZATION=f"Token tok{usuario.identification[-1]}")
        return self.cliente

    def anonimo(self):
        self.cliente.credentials()
        return self.cliente

    def camas(self):
        for zona, gz, v, s in [("A", "z1", "RO1", "s1"), ("B", "z1", "RO2", "s2"), ("C", "z2", "RO1", None)]:
            r = self.como(self.admin).post(
                "/agrohubs/AH-002/camas", {"zona": zona, "gateway_zona": gz, "valvula": v, "sensor": s}, format="json"
            )
            self.assertEqual(r.status_code, 201, r.content)


class RellenoTests(TestCase):
    def _paso(self, temp=None, hum=None, en_linea=False):
        return {"t": 0, "temperatura": temp, "humedadAire": temp and 70, "temperaturaSuelo": None,
                "enLinea": en_linea, "eras": [{"zona": "A", "humedad": hum, "riego": None, "auto": None}]}

    def test_rellena_hasta_la_tolerancia_y_no_mas(self):
        serie = [self._paso(30, 20, True)] + [self._paso() for _ in range(8)]
        lecturas._rellenar(serie, tolerancia=6)  # 6 pasos = 3 horas
        self.assertEqual([p["enLinea"] for p in serie], [True] * 7 + [False] * 2)
        self.assertEqual([p["relleno"] for p in serie], [False] + [True] * 6 + [False] * 2)
        self.assertEqual(serie[6]["eras"][0]["humedad"], 20)
        self.assertEqual(serie[6]["minutosSinDato"], 180)
        self.assertIsNone(serie[7]["temperatura"])  # pasada la tolerancia no se inventa

    def test_completa_solo_lo_que_falta(self):
        serie = [self._paso(30, 20, True), self._paso(31, None, True)]  # llegó el clima, no la sonda
        lecturas._rellenar(serie, tolerancia=6)
        self.assertEqual((serie[1]["temperatura"], serie[1]["eras"][0]["humedad"]), (31, 20))
        self.assertTrue(serie[1]["relleno"])
        self.assertEqual(serie[1]["minutosSinDato"], 0)

    def test_sin_tolerancia_no_rellena(self):
        serie = [self._paso(30, 20, True), self._paso()]
        lecturas._rellenar(serie, tolerancia=0)
        self.assertFalse(serie[1]["enLinea"])


class CicloTests(TestCase):
    def setUp(self):
        self.tomate = Cultivo.objects.get(id="tomate").ficha_dict()

    def test_biblioteca_cargada(self):
        self.assertEqual(Cultivo.objects.count(), 18)
        self.assertEqual(self.tomate["etapas"][0], {"tipo": "inicio", "nombre": "Prende", "desde": 0})

    def test_umbral_por_etapa(self):
        self.assertEqual(ciclo.umbral_de_cama(self.tomate, 3, 0)["abrir"], self.tomate["abrir"] + 4)  # recién sembrado
        self.assertEqual(ciclo.umbral_de_cama(self.tomate, 60, 0)["abrir"], self.tomate["abrir"])
        self.assertEqual(ciclo.umbral_de_cama(self.tomate, None, 3)["abrir"], self.tomate["abrir"] + 3)

    def test_estado_tierra(self):
        self.assertEqual(ciclo.estado_tierra(10, 30, 42), "seca")
        self.assertEqual(ciclo.estado_tierra(27, 30, 42), "pidiendo")
        self.assertEqual(ciclo.estado_tierra(27, 30, 42, riego=True), "regando")
        self.assertEqual(ciclo.estado_tierra(60, 30, 42), "encharcada")
        self.assertIsNone(ciclo.estado_tierra(None, 30, 42))

    def test_edad_como_javascript(self):
        self.assertEqual(ciclo.edad_texto(135), "5 meses")  # Math.round(4.5) = 5
        self.assertEqual(ciclo.edad_texto(0), "hoy")


class BibliotecaTests(BaseHuertas):
    def test_lista_publica(self):
        r = self.anonimo().get("/cultivos/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["data"]), 18)
        self.assertEqual(self.anonimo().get("/cultivos").status_code, 200)
        self.assertEqual(self.anonimo().get("/cultivos/aji").json()["data"]["nombre"], "Ají")

    def test_edicion_solo_equipo_y_queda_registro(self):
        self.assertEqual(self.como(self.cuidadora).patch("/cultivos/tomate", {"abrir": 32}, format="json").status_code, 403)
        r = self.como(self.admin).patch("/cultivos/tomate", {"abrir": 32, "fuentes": {"abrir": "calibración local"}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["data"]["cambios"]["abrir"], [30, 32])
        cambios = self.como(self.admin).get("/cultivos/tomate/cambios").json()["data"]
        self.assertEqual(cambios[0]["usuario_id"], self.admin.id)

    def test_histeresis_minima(self):
        r = self.como(self.admin).patch("/cultivos/tomate", {"abrir": 41}, format="json")
        self.assertEqual(r.status_code, 422)


class PermisosTests(BaseHuertas):
    def test_permisos_por_sesion(self):
        p = self.anonimo().get("/agrohubs/AH-002/permisos").json()["data"]
        self.assertFalse(p["cambiar_plan"])
        self.assertTrue(p["reportar"])
        p = self.como(self.cuidadora).get("/agrohubs/ah-002/permisos").json()["data"]
        self.assertTrue(p["cambiar_plan"] and p["regar"] and p["es_cuidador"])
        self.assertFalse(p["configurar_camas"])
        # Cuida AH-002, no AH-003.
        self.assertFalse(self.como(self.cuidadora).get("/agrohubs/AH-003/permisos").json()["data"]["cambiar_plan"])
        self.assertTrue(self.como(self.admin).get(f"/agrohubs/{self.agrohub.id}/permisos").json()["data"]["configurar_camas"])

    def test_asignar_cuidador(self):
        self.assertEqual(self.como(self.cuidadora).post("/agrohubs/AH-003/cuidadores", {"usuario_id": self.vecino.id}).status_code, 403)
        r = self.como(self.admin).post("/agrohubs/AH-003/cuidadores", {"usuario_id": self.vecino.id}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(self.como(self.vecino).get("/agrohubs/AH-003/permisos").json()["data"]["cambiar_plan"])
        self.assertEqual(self.como(self.admin).delete(f"/agrohubs/AH-003/cuidadores/{self.vecino.id}").status_code, 200)
        # También por teléfono o cédula (el panel no ve la lista de usuarios)
        r = self.como(self.admin).post("/agrohubs/AH-003/cuidadores", {"identificador": self.vecino.phone}, format="json")
        self.assertEqual(r.json()["data"][0]["usuario_id"], self.vecino.id)
        r = self.como(self.admin).post("/agrohubs/AH-003/cuidadores", {"identificador": "000"}, format="json")
        self.assertEqual(r.status_code, 422)


class PlanTests(BaseHuertas):
    def test_config_tecnica_solo_equipo(self):
        r = self.como(self.cuidadora).post("/agrohubs/AH-002/camas", {"zona": "A"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.camas()
        r = self.como(self.admin).post("/agrohubs/AH-002/camas", {"zona": "D", "gateway_zona": "z1", "valvula": "RO1"}, format="json")
        self.assertEqual(r.status_code, 422)  # esa válvula ya gobierna la cama A
        publico = self.anonimo().get("/agrohubs/AH-002/plan").json()["data"]
        self.assertEqual([c["zona"] for c in publico["camas"]], ["A", "B", "C"])
        self.assertNotIn("tecnico", publico["camas"][0])  # el público no ve zona/válvula/sensor
        self.assertIn("tecnico", self.como(self.admin).get("/agrohubs/AH-002/plan").json()["data"]["camas"][0])

    def test_sembrar_liberar_intercambiar(self):
        self.camas()
        hace = (timezone.localdate() - timedelta(days=20)).isoformat()
        r = self.como(self.vecino).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate", "sembrado_el": hace}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        cama = r.json()["data"]["camas"][0]
        self.assertEqual((cama["cultivo_id"], cama["dias"], cama["momento"]["etapa"]["tipo"]), ("tomate", 20, "crecimiento"))
        self.assertEqual(cama["umbral"]["abrir"], 30)
        self.assertEqual(r.json()["data"]["envio"]["camas"]["A"]["resultado"], "desactivado")  # apagado por defecto
        self.assertEqual(r.json()["data"]["movimientos_nuevos"][0]["tipo"], "siembra")

        self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/B", {"cultivo_id": "aji"}, format="json")
        r = self.como(self.cuidadora).post("/agrohubs/AH-002/plan/intercambiar", {"zonas": ["A", "B"]}, format="json")
        self.assertEqual([c["cultivo_id"] for c in r.json()["data"]["camas"][:2]], ["aji", "tomate"])

        r = self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": None}, format="json")
        a = r.json()["data"]["camas"][0]
        self.assertTrue(a["libre"])
        self.assertEqual(a["anteriores"][0]["cultivo_id"], "aji")
        tipos = list(Movimiento.objects.filter(agrohub=self.agrohub).values_list("tipo", flat=True))
        self.assertEqual(sorted(tipos), ["cambio", "descanso", "siembra", "siembra"])

    def test_validaciones(self):
        self.camas()
        c = self.como(self.cuidadora)
        futuro = (timezone.localdate() + timedelta(days=2)).isoformat()
        self.assertEqual(c.put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate", "sembrado_el": futuro}, format="json").status_code, 422)
        self.assertEqual(c.put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "mango"}, format="json").status_code, 422)
        self.assertEqual(c.put("/agrohubs/AH-002/plan/camas/A", {"cosechando": True}, format="json").status_code, 422)
        self.assertEqual(c.put("/agrohubs/AH-002/plan/camas/A", {"ajuste": 9}, format="json").status_code, 422)
        self.assertEqual(c.put("/agrohubs/AH-002/plan/camas/Z", {"ajuste": 1}, format="json").status_code, 404)

    @override_settings(HUERTAS_ENVIAR_UMBRALES=True)
    def test_envio_al_gateway(self):
        self.camas()
        respuesta = {"resultado": "aplicada", "rev": 14, "errores": []}
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config", return_value=respuesta) as aplicar:
            r = self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate"}, format="json")
        self.assertEqual(r.json()["data"]["envio"]["resultado"], "aplicada")
        device, zonas = aplicar.call_args.args
        self.assertEqual(device, "device0014")
        self.assertEqual(zonas, {"z1": {"riego": {"RO1": {"abrir": 34, "cerrar": 46}}}})  # tomate recién sembrado: +4
        cama = Cama.objects.get(agrohub=self.agrohub, zona="A")
        self.assertEqual((cama.umbral_abrir, cama.envio_rev), (34, 14))

        # Mismo umbral → no se vuelve a mandar.
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config") as aplicar:
            res = plan.recalcular_y_enviar(self.agrohub)
        aplicar.assert_not_called()
        self.assertEqual(res["camas"]["A"]["resultado"], "sin_cambios")

        # Sin respuesta del gateway NO cuenta como aplicada: se reintenta al día siguiente.
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config", return_value={"resultado": "sin_respuesta", "rev": 15, "errores": []}):
            r = self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"ajuste": 3}, format="json")
        self.assertEqual(r.json()["data"]["envio"]["resultado"], "sin_respuesta")
        self.assertEqual(Cama.objects.get(agrohub=self.agrohub, zona="A").umbral_abrir, 34)

    @override_settings(HUERTAS_ENVIAR_UMBRALES=True)
    def test_zona_en_descanso_apaga_el_automatico(self):
        self.camas()
        ok = {"resultado": "aplicada", "rev": 1, "errores": []}
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config", return_value=ok):
            self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/C", {"cultivo_id": "aji"}, format="json")
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config", return_value=ok) as aplicar:
            self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/C", {"cultivo_id": None}, format="json")
        self.assertEqual(aplicar.call_args.args[1], {"z2": {"auto": False}})
        # Al volver a sembrar se reenciende.
        with mock.patch("apps.riego_iot.control_mqtt.aplicar_config", return_value=ok) as aplicar:
            self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/C", {"cultivo_id": "aji"}, format="json")
        self.assertTrue(aplicar.call_args.args[1]["z2"]["auto"])

    def test_regar(self):
        self.camas()
        with mock.patch("apps.riego_iot.control_mqtt.enviar_comando_valvula", return_value={"resultado": "enviada", "errores": []}) as enviar:
            r = self.como(self.cuidadora).post("/agrohubs/AH-002/camas/B/regar", {"accion": "abrir"}, format="json")
        self.assertEqual(r.json()["data"]["resultado"], "enviada")
        enviar.assert_called_once_with("device0014", "z1", "RO2", "abrir")
        self.assertEqual(self.como(self.vecino).post("/agrohubs/AH-002/camas/B/regar", {"accion": "abrir"}, format="json").status_code, 403)


def _dt(minutos_atras):
    return datetime.now(dt_timezone.utc) - timedelta(minutes=minutos_atras)


class LecturasTests(BaseHuertas):
    def setUp(self):
        super().setUp()
        self.camas()
        from apps.riego_iot.models import EstadoValvula, Healthcheck, LecturaAmbiente, LecturaSuelo

        for m in (100, 70, 40, 10):
            LecturaSuelo.objects.using("mqtt").create(
                device_id="device0014", dev_eui="s1", medido_en=_dt(m), humedad_suelo=20 + m / 10,
                temperatura_suelo=29, recibido_en=_dt(m), payload_crudo={"equipo": "SE01-01"},
            )
            LecturaAmbiente.objects.using("mqtt").create(
                device_id="device0014", medido_en=_dt(m), temperatura=31, humedad=70, recibido_en=_dt(m), payload_crudo={},
            )
        EstadoValvula.objects.using("mqtt").create(
            device_id="device0014", medido_en=_dt(45), ro1="abierta", ro2="cerrada", origen="reportado",
            recibido_en=_dt(45), payload_crudo={"zona": "z1"},
        )
        Healthcheck.objects.using("mqtt").create(
            device_id="device0014", medido_en=_dt(200), valvulas={"z1": {"RO1": "cerrada", "RO2": "cerrada"}},
            recibido_en=_dt(200), payload_crudo={"zonas_auto": {"z1": True, "z2": False}},
        )

    def test_lecturas_con_forma_del_front(self):
        r = self.anonimo().get("/agrohubs/AH-002/lecturas", {"desde": int(_dt(180).timestamp() * 1000)})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()["data"]
        self.assertEqual(d["paso_minutos"], 30)
        con_datos = [l for l in d["lecturas"] if l["enLinea"]]
        self.assertGreaterEqual(len(con_datos), 3)
        l = con_datos[-1]
        self.assertEqual(set(l), {"t", "temperatura", "humedadAire", "temperaturaSuelo", "enLinea", "eras", "relleno", "minutosSinDato"})
        self.assertEqual([e["zona"] for e in l["eras"]], ["A", "B", "C"])
        self.assertIsNotNone(l["eras"][0]["humedad"])
        self.assertIsNone(l["eras"][2]["humedad"])  # la cama C no tiene sensor: no se inventa
        self.assertTrue(l["eras"][0]["riego"])  # RO1 de z1 abierta desde hace 45 min
        self.assertFalse(l["eras"][1]["riego"])
        self.assertEqual((l["eras"][0]["auto"], l["eras"][2]["auto"]), (True, False))
        self.assertNotIn("device0014", r.content.decode())
        self.assertNotIn("s1", json.dumps(d["camas"]))

    def test_pasos_sin_datos_no_se_rellenan(self):
        r = self.anonimo().get("/agrohubs/AH-002/lecturas", {"desde": int(_dt(60 * 24).timestamp() * 1000)})
        viejas = [l for l in r.json()["data"]["lecturas"] if l["t"] < (_dt(300).timestamp() * 1000)]
        self.assertTrue(viejas)
        self.assertTrue(all(not l["enLinea"] and l["temperatura"] is None for l in viejas))

    def test_huecos_cortos_repiten_el_ultimo_dato_marcado(self):
        d = self.anonimo().get("/agrohubs/AH-002/lecturas", {"desde": int(_dt(180).timestamp() * 1000)}).json()["data"]
        self.assertEqual(d["tolerancia_minutos"], 180)
        self.assertIsNotNone(d["ultimoDatoReal"])
        ultima = d["lecturas"][-1]
        # El paso en curso aún no tiene lectura: repite la última medida, en línea y marcada
        self.assertTrue(ultima["enLinea"])
        self.assertIsNotNone(ultima["temperatura"])
        self.assertIn("relleno", ultima)
        self.assertIn("minutosSinDato", ultima)

    def test_ventana_maxima(self):
        r = self.anonimo().get("/agrohubs/AH-002/lecturas", {"desde": "2020-01-01"})
        self.assertEqual(r.status_code, 422)
        r = self.anonimo().get("/agrohubs/AH-002/lecturas", {"desde": int(_dt(8 * 24 * 60).timestamp() * 1000)})
        self.assertEqual(r.status_code, 200)  # «los últimos 8 días» exactos

    def test_sin_gateway(self):
        d = self.anonimo().get("/agrohubs/AH-003/lecturas").json()["data"]
        self.assertTrue(d["sin_gateway"])
        self.assertEqual(d["lecturas"], [])

    def test_reporte_anota_el_sensor(self):
        self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate", "sembrado_el": "2026-10-01"}, format="json")
        r = self.anonimo().post("/agrohubs/AH-002/reportes", {
            "zona": "A", "matas": "bonitas", "tierra": "seca", "plaga": "no", "riego_mano": "no", "cosecha": "no",
            "autor_rol": "Una vecina",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()["data"]
        # 21 de humedad con umbral 30: «seca» manda aunque la válvula esté abierta (como en lectura.ts).
        self.assertEqual((d["sensor"], Reporte.objects.get().sensor_humedad), ("seca", 21.0))
        self.assertEqual(d["autor"], "Una vecina")

    def test_sensores_para_el_equipo(self):
        d = self.como(self.admin).get("/agrohubs/AH-002/sensores").json()["data"]
        self.assertEqual(d["sensores"][0]["equipo"], "SE01-01")
        self.assertEqual(d["sensores"][0]["cama"], "A")
        self.assertEqual(d["zonas"], {"z1": ["RO1", "RO2"]})
        self.assertEqual(self.como(self.cuidadora).get("/agrohubs/AH-002/sensores").status_code, 403)


REPORTE = {"matas": "bonitas", "tierra": "humeda", "plaga": "no", "riego_mano": "no", "cosecha": "no"}


class ReportesTests(BaseHuertas):
    def test_reporte_abierto_y_moderacion(self):
        r = self.anonimo().post("/agrohubs/AH-002/reportes", {**REPORTE, "nota": "Todo bien"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["data"]["autor"], "Alguien de la comunidad")
        r = self.anonimo().post("/agrohubs/AH-002/reportes", {**REPORTE, "nota": "compra en www.spam.com"}, format="json")
        self.assertEqual(r.json()["data"]["moderacion"], "pendiente")
        publico = self.anonimo().get("/agrohubs/AH-002/reportes").json()["data"]
        self.assertEqual(len(publico), 1)
        self.assertNotIn("moderacion", publico[0])
        todos = self.como(self.cuidadora).get("/agrohubs/AH-002/reportes", {"moderacion": "todos"}).json()["data"]
        self.assertEqual(len(todos), 2)
        pendiente = next(x for x in todos if x["moderacion"] == "pendiente")
        self.assertEqual(self.anonimo().put(f"/agrohubs/AH-002/reportes/{pendiente['id']}/moderacion", {"moderacion": "visible"}, format="json").status_code, 401)
        r = self.como(self.cuidadora).put(f"/agrohubs/AH-002/reportes/{pendiente['id']}/moderacion", {"moderacion": "oculto"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_valores_invalidos(self):
        r = self.anonimo().post("/agrohubs/AH-002/reportes", {**REPORTE, "matas": "felices"}, format="json")
        self.assertEqual(r.status_code, 422)

    def test_limite_por_dispositivo(self):
        for _ in range(4):
            self.assertEqual(self.anonimo().post("/agrohubs/AH-002/reportes", REPORTE, format="json", HTTP_X_DISPOSITIVO="cel-1").status_code, 201)
        self.assertEqual(self.anonimo().post("/agrohubs/AH-002/reportes", REPORTE, format="json", HTTP_X_DISPOSITIVO="cel-1").status_code, 429)

    def test_foto(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (40, 40), "green").save(buf, "PNG")
        foto = SimpleUploadedFile("mata.png", buf.getvalue(), content_type="image/png")
        r = self.anonimo().post("/agrohubs/AH-002/reportes", {**REPORTE, "foto": foto}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        foto_url = r.json()["data"]["foto"]
        self.assertTrue(foto_url.endswith(".jpg"))
        self.assertTrue(foto_url.startswith("https://") or foto_url.startswith("http"), foto_url)


class BitacoraTests(BaseHuertas):
    def test_bitacora_de_la_huerta(self):
        r = self.como(self.vecino).post("/user-activity/logbooks", {
            "title": "Abono", "description": "x", "activity_date": "2026-11-20", "agrohub_id": self.agrohub.id,
        }, format="json")
        self.assertEqual(r.status_code, 403)  # no cuida esta huerta
        r = self.como(self.cuidadora).post("/user-activity/logbooks", {
            "title": "Abono", "description": "Compost en la cama A", "activity_date": "2026-11-20",
            "activity_type": "abono", "moon_phase": "Cuarto creciente", "agrohub_id": self.agrohub.id,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["data"]["moon_phase"], "Cuarto creciente")
        self.como(self.cuidadora).post("/user-activity/logbooks", {
            "title": "Solo equipo", "description": "y", "activity_date": "2026-11-21", "agrohub_id": self.agrohub.id, "publica": False,
        }, format="json")
        publico = self.anonimo().get("/agrohubs/AH-002/bitacora").json()["data"]
        self.assertEqual([n["title"] for n in publico], ["Abono"])
        self.assertEqual(publico[0]["autor"], "Persona")
        self.assertEqual(len(self.como(self.cuidadora).get("/agrohubs/AH-002/bitacora").json()["data"]), 2)

    def test_bitacora_personal_guarda_tipo_y_luna(self):
        self.como(self.vecino).post("/user-activity/logbooks", {
            "title": "Riego", "description": "z", "activity_date": "2026-11-20", "activity_type": "riego", "moon_phase": "Luna llena",
        }, format="json")
        l = Logbook.objects.get(user=self.vecino)
        self.assertEqual((l.activity_type, l.moon_phase, l.agrohub_id), ("riego", "Luna llena", None))


class CalibracionTests(BaseHuertas):
    def test_propuesta_y_aceptacion(self):
        self.camas()
        self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate", "sembrado_el": "2026-10-01"}, format="json")
        cama = Cama.objects.get(agrohub=self.agrohub, zona="A")
        for _ in range(2):
            Reporte.objects.create(agrohub=self.agrohub, cama=cama, sensor="bien", **{**REPORTE, "tierra": "seca"})
        recs = self.anonimo().get("/agrohubs/AH-002/recomendaciones").json()["data"]
        cal = next(r for r in recs if r["id"] == "calibrar-mas-A")
        self.assertEqual(cal["accion"]["puntos"], 3)
        self.assertEqual(self.anonimo().post("/agrohubs/AH-002/calibracion/aceptar", {"zona": "A", "puntos": 3}, format="json").status_code, 401)
        r = self.como(self.cuidadora).post("/agrohubs/AH-002/calibracion/aceptar", {"zona": "A", "puntos": 3}, format="json")
        self.assertEqual(r.json()["data"]["camas"][0]["ajuste"], 3)
        self.como(self.cuidadora).post("/agrohubs/AH-002/calibracion/aceptar", {"zona": "A", "puntos": 3}, format="json")
        r = self.como(self.cuidadora).post("/agrohubs/AH-002/calibracion/aceptar", {"zona": "A", "puntos": 3}, format="json")
        self.assertEqual(r.status_code, 422)  # pasaría de +6: avisar al equipo técnico
        self.assertIn("equipo técnico", r.json()["errores"][0]["mensaje"])


class SeguimientoTests(BaseHuertas):
    def _respuesta(self, *a, **k):
        cuerpo = {"resumen": "La huerta va bien.", "vaBien": ["Riego al día"], "cuidar": [], "pasos": ["Revisa la cama de tomate"], "pregunta": "¿Cómo ven las matas?"}
        return json.dumps(cuerpo), 1200, 150

    @override_settings(OPENAI_API_KEY="sk-prueba", HUERTAS_LLM_PROVEEDOR="")
    def test_genera_solo_con_novedades(self):
        self.camas()
        self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cultivo_id": "tomate", "sembrado_el": "2026-10-01"}, format="json")
        est = self.anonimo().get("/agrohubs/AH-002/seguimiento").json()["data"]
        self.assertTrue(est["hay_novedades"])
        self.assertIsNone(est["seguimiento"])
        with mock.patch("apps.huertas.seguimiento._llamar_openai", side_effect=self._respuesta) as llamar:
            r = self.anonimo().post("/agrohubs/AH-002/seguimiento")
            self.assertEqual(r.status_code, 201, r.content)
            self.assertEqual(r.json()["data"]["seguimiento"]["vaBien"], ["Riego al día"])
            r = self.anonimo().post("/agrohubs/AH-002/seguimiento")  # misma huella: no llama
            self.assertEqual(r.status_code, 200)
        self.assertEqual(llamar.call_count, 1)
        contexto = json.loads(llamar.call_args.args[1])
        self.assertEqual(contexto["camas"][0]["cultivo"], "Tomate")
        s = Seguimiento.objects.get()
        self.assertEqual((s.modelo, s.tokens_entrada), ("gpt-4o-mini", 1200))
        self.assertGreater(s.costo_usd, 0)
        self.assertFalse(self.anonimo().get("/agrohubs/AH-002/seguimiento").json()["data"]["hay_novedades"])

        # Hay novedades, pero no han pasado 6 horas: se conserva el anterior.
        self.anonimo().post("/agrohubs/AH-002/reportes", REPORTE, format="json")
        with mock.patch("apps.huertas.seguimiento._llamar_openai", side_effect=self._respuesta) as llamar:
            r = self.anonimo().post("/agrohubs/AH-002/seguimiento")
        self.assertEqual(r.status_code, 429)
        llamar.assert_not_called()
        self.assertEqual(r.json()["data"]["seguimiento"]["resumen"], "La huerta va bien.")

    @override_settings(OPENAI_API_KEY="sk-prueba", HUERTAS_LLM_TOPE_USD_MES=0)
    def test_tope_mensual(self):
        self.camas()
        r = self.anonimo().post("/agrohubs/AH-002/seguimiento")
        self.assertEqual(r.status_code, 429)

    @override_settings(OPENAI_API_KEY="", GEMINI_API_KEY="", HUERTAS_LLM_PROVEEDOR="")
    def test_sin_llave(self):
        self.camas()
        r = self.anonimo().post("/agrohubs/AH-002/seguimiento")
        self.assertEqual(r.status_code, 503)

    @override_settings(OPENAI_API_KEY="sk-prueba")
    def test_huerta_vacia_no_gasta(self):
        with mock.patch("apps.huertas.seguimiento._llamar_openai") as llamar:
            r = self.anonimo().post("/agrohubs/AH-002/seguimiento")
        self.assertEqual(r.status_code, 422)
        llamar.assert_not_called()


class CamasPorDefectoTests(BaseHuertas):
    def test_crea_camas_de_referencia_y_se_confirman_al_editar(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.riego_iot.models import LecturaSuelo

        for dev, equipo in (("s2", "SE01-02"), ("s1", "SE01-01")):
            LecturaSuelo.objects.using("mqtt").create(
                device_id="device0014", dev_eui=dev, medido_en=_dt(30), humedad_suelo=25,
                recibido_en=_dt(30), payload_crudo={"equipo": equipo},
            )
        call_command("huertas_camas_por_defecto", stdout=StringIO())  # vista previa: no crea
        self.assertFalse(Cama.objects.exists())
        call_command("huertas_camas_por_defecto", "--aplicar", stdout=StringIO())
        camas = list(Cama.objects.filter(agrohub=self.agrohub).order_by("orden"))
        self.assertEqual([(c.zona, c.cultivo_id, c.sensor) for c in camas], [("A", "aji", "s1"), ("B", "yuca", "s2")])
        self.assertTrue(all(c.origen == "referencia" and not c.valvula for c in camas))
        # AH-003 sin gateway: camas del micrositio sin sonda
        self.assertEqual(Cama.objects.filter(agrohub=self.otro, sensor__isnull=True).count(), 4)
        plan = self.anonimo().get("/agrohubs/AH-002/plan").json()["data"]
        self.assertTrue(plan["camas"][0]["referencia"])
        self.como(self.cuidadora).put("/agrohubs/AH-002/plan/camas/A", {"cosechando": True}, format="json")
        self.assertFalse(self.anonimo().get("/agrohubs/AH-002/plan").json()["data"]["camas"][0]["referencia"])
        call_command("huertas_camas_por_defecto", "--borrar", stdout=StringIO())
        self.assertEqual(list(Cama.objects.filter(agrohub=self.agrohub).values_list("zona", flat=True)), ["A"])


class ResumenTests(BaseHuertas):
    def test_huerta_en_una_llamada(self):
        self.camas()
        d = self.anonimo().get("/agrohubs/AH-002/huerta").json()["data"]
        self.assertEqual(d["agrohub"]["slug"], "ah-002")
        self.assertEqual(len(d["plan"]["camas"]), 3)
        self.assertIn("recomendaciones", d)
        self.assertFalse(d["permisos"]["cambiar_plan"])
        todas = self.anonimo().get("/agrohubs/huertas").json()["data"]
        self.assertEqual([h["numero"] for h in todas], ["AH-002", "AH-003"])
        self.assertEqual(len(todas[0]["camas"]), 3)
        self.assertNotIn("tecnico", todas[0]["camas"][0])
        # Las rutas del geovisor siguen funcionando.
        self.assertEqual(self.anonimo().get("/agrohubs/puntos").status_code, 200)
        self.assertEqual(self.anonimo().get(f"/agrohubs/{self.agrohub.id}").status_code, 200)
