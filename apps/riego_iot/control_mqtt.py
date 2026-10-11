"""Control de gateways desde la plataforma: leer su configuración vigente, cambiarla y mandar
órdenes de válvula, todo por MQTT (ver mqtt_agrohub/docs/TOPICS.md y la guía de configuración
remota). La plataforma SOLO configura umbrales y manda órdenes manuales: NO publica el latido
`cloud/health` (con latido el gateway deja de decidir el riego solo).

Cada operación abre su propia conexión corta al broker local con el usuario MQTT de la plataforma
(ACL: leer config/state, valvulas/state, health y status; escribir config/set y control/valvulas)."""
import json
import queue
import re
import ssl
import time
import uuid

import paho.mqtt.client as mqtt
from django.conf import settings

ESPERA_CONEXION = 5
ESPERA_ESTADO = 4
ESPERA_CONFIRMACION_CONFIG = 20
ESPERA_ECO_VALVULA = 5
HISTERESIS_MINIMA = 3
VALVULAS_VALIDAS = ("RO1", "RO2")
ACCIONES_VALIDAS = ("abrir", "cerrar")
_ZONA_RE = re.compile(r"^z\d+$")


class MqttNoDisponible(Exception):
    pass


class SesionMqtt:
    """Conexión corta: se suscribe, publica y espera mensajes con un predicado."""

    def __init__(self, topics):
        self.topics = topics
        self._cola = queue.Queue()
        self._conectado = False
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"agrohub-plataforma-{uuid.uuid4().hex[:8]}",
        )

    def __enter__(self):
        c = self.client
        if settings.RIEGO_IOT_MQTT_USER:
            c.username_pw_set(settings.RIEGO_IOT_MQTT_USER, settings.RIEGO_IOT_MQTT_PASSWORD)
        if settings.RIEGO_IOT_MQTT_TLS:
            c.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        c.on_connect = self._on_connect
        c.on_message = self._on_message
        try:
            c.connect(settings.RIEGO_IOT_MQTT_HOST, settings.RIEGO_IOT_MQTT_PORT, keepalive=30)
        except OSError as exc:
            raise MqttNoDisponible(f"No se pudo conectar al broker MQTT: {exc}") from exc
        c.loop_start()
        limite = time.time() + ESPERA_CONEXION
        while not self._conectado and time.time() < limite:
            time.sleep(0.05)
        if not self._conectado:
            self.__exit__(None, None, None)
            raise MqttNoDisponible("El broker MQTT no aceptó la conexión (¿usuario o clave de la plataforma?).")
        return self

    def __exit__(self, *exc):
        self.client.loop_stop()
        try:
            self.client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if getattr(reason_code, "is_failure", False) or reason_code != 0:
            return
        for topic in self.topics:
            client.subscribe(topic, qos=1)
        self._conectado = True

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload) if msg.payload else None
        except ValueError:
            data = None
        self._cola.put((msg.topic, data))

    def vaciar(self, pausa=0.6):
        """Descarta lo que ya estaba retenido para no confundirlo con la respuesta a lo que se envíe."""
        time.sleep(pausa)
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                return

    def esperar(self, predicado, timeout):
        limite = time.time() + timeout
        while True:
            restante = limite - time.time()
            if restante <= 0:
                return None
            try:
                topic, data = self._cola.get(timeout=restante)
            except queue.Empty:
                return None
            if data is not None and predicado(topic, data):
                return data

    def publicar(self, topic, payload):
        info = self.client.publish(topic, json.dumps(payload), qos=1, retain=False)
        info.wait_for_publish(timeout=ESPERA_CONEXION)
        if not info.is_published():
            raise MqttNoDisponible(f"No se pudo publicar en {topic}.")


def _topic(device_id, sufijo):
    return f"ahub/{device_id}/{sufijo}"


def leer_config(device_id):
    """config/state vigente del gateway (mensaje retenido) o None si nunca publicó uno."""
    with SesionMqtt([_topic(device_id, "config/state")]) as s:
        return s.esperar(lambda t, d: True, ESPERA_ESTADO)


def validar_config(zonas, vigente):
    """Mismas reglas que el gateway (todo o nada), para no enviar algo que se va a rechazar.
    `vigente` es el config/state actual o None (entonces no se puede comprobar zonas/histéresis
    contra lo guardado y eso lo valida el gateway)."""
    errores = []
    if not isinstance(zonas, dict):
        return ["zonas debe ser un objeto"]
    zonas_vigentes = (vigente or {}).get("zonas") or {}
    for zona, cambio in zonas.items():
        if not _ZONA_RE.match(str(zona)):
            errores.append(f"zona inválida: {zona}")
            continue
        if vigente and zona not in zonas_vigentes:
            errores.append(f"zona inexistente: {zona}")
            continue
        if not isinstance(cambio, dict):
            errores.append(f"{zona}: debe ser un objeto")
            continue
        if "auto" in cambio and not isinstance(cambio["auto"], bool):
            errores.append(f"{zona}.auto debe ser booleano")
        for valvula, umbrales in (cambio.get("riego") or {}).items():
            if valvula not in VALVULAS_VALIDAS:
                errores.append(f"{zona}: valvula invalida {valvula}")
                continue
            actual = (((zonas_vigentes.get(zona) or {}).get("riego") or {}).get(valvula)) or {}
            nuevo = {}
            for campo in ("abrir", "cerrar"):
                valor = umbrales.get(campo, actual.get(campo)) if isinstance(umbrales, dict) else None
                if campo in (umbrales or {}):
                    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 100:
                        errores.append(f"{zona}.{valvula}.{campo} debe ser un número entre 0 y 100")
                        valor = None
                nuevo[campo] = valor
            if nuevo["abrir"] is not None and nuevo["cerrar"] is not None:
                if nuevo["cerrar"] - nuevo["abrir"] < HISTERESIS_MINIMA:
                    errores.append(
                        f"{zona}.{valvula}: cerrar debe superar a abrir por >= {HISTERESIS_MINIMA} "
                        f"(abrir={nuevo['abrir']}, cerrar={nuevo['cerrar']})"
                    )
    return errores


def aplicar_config(device_id, zonas):
    """Cambio parcial con rev = vigente + 1 y espera de la confirmación (config/state con esa rev).
    Devuelve {resultado: aplicada|rechazada|sin_respuesta|invalida, rev, ...}."""
    with SesionMqtt([_topic(device_id, "config/state")]) as s:
        vigente = s.esperar(lambda t, d: True, ESPERA_ESTADO)
        errores = validar_config(zonas, vigente)
        if errores:
            return {"resultado": "invalida", "rev": None, "errores": errores}
        rev = int((vigente or {}).get("rev") or 0) + 1

        def es_respuesta(topic, data):
            rechazo = data.get("ultimo_rechazo") or {}
            return data.get("rev") == rev or rechazo.get("rev") == rev

        s.publicar(_topic(device_id, "config/set"), {"rev": rev, "zonas": zonas})
        respuesta = s.esperar(es_respuesta, ESPERA_CONFIRMACION_CONFIG)

    if respuesta is None:
        return {"resultado": "sin_respuesta", "rev": rev, "errores": []}
    if respuesta.get("rev") == rev:
        return {"resultado": "aplicada", "rev": rev, "errores": [], "config": respuesta}
    return {"resultado": "rechazada", "rev": rev, "errores": (respuesta.get("ultimo_rechazo") or {}).get("errores", [])}


def validar_comando_valvula(zona, valvula, accion, vigente=None):
    errores = []
    if not _ZONA_RE.match(str(zona)):
        errores.append(f"zona inválida: {zona}")
    elif vigente and zona not in (vigente.get("zonas") or {}):
        errores.append(f"zona inexistente: {zona}")
    if valvula not in VALVULAS_VALIDAS:
        errores.append(f"valvula inválida: {valvula} (usa RO1 o RO2)")
    if accion not in ACCIONES_VALIDAS:
        errores.append(f"accion inválida: {accion} (usa abrir o cerrar)")
    return errores


def enviar_comando_valvula(device_id, zona, valvula, accion):
    """Publica la orden y espera el primer eco del gateway (valvulas/state con origen "remoto").
    La confirmación física ("reportado") puede tardar hasta ~10 min y se ve en las lecturas de válvulas."""
    comando = {"zona": zona, "valvula": valvula, "accion": accion}
    with SesionMqtt([_topic(device_id, "valvulas/state"), _topic(device_id, "config/state")]) as s:
        vigente = s.esperar(lambda t, d: t.endswith("config/state"), 1.5)
        errores = validar_comando_valvula(zona, valvula, accion, vigente)
        if errores:
            return {"resultado": "invalida", "errores": errores, "comando": comando}
        s.vaciar(0.3)
        s.publicar(_topic(device_id, "control/valvulas"), comando)
        eco = s.esperar(
            lambda t, d: t.endswith("valvulas/state") and d.get("origen") == "remoto" and d.get("zona") == zona,
            ESPERA_ECO_VALVULA,
        )
    return {"resultado": "enviada" if eco else "sin_eco", "errores": [], "comando": comando, "estado": eco}
