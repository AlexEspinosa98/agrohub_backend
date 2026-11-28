"""Lecturas abiertas por cama (HU-HB03).

Lee la base de mqtt_agrohub (alias 'mqtt', la misma de apps.riego_iot) y agrega en pasos de 30 min
con la forma de `Lectura` del frontend (`_lib/simulacion.ts`), para que reemplazar `simular()` sea
cambiar una función:

    {t, temperatura, humedadAire, temperaturaSuelo, enLinea, eras: [{zona, humedad, riego, auto}]}

Reglas:
- Zona rural: los gateways mandan a ratos (se saltan pasos o suben tarde lo que guardaron). Si la
  estación mandó datos hace menos de `HUERTAS_TOLERANCIA_MINUTOS` (3 h por defecto), un paso sin
  lectura repite el ÚLTIMO valor medido, sale `enLinea: true` y se marca `relleno: true` con
  `minutosSinDato`: no es una medición nueva y el cliente lo puede decir. Nunca se interpola ni
  se inventa un valor que no se haya medido.
- Pasada la tolerancia, sin datos se responde sin datos: `enLinea: false` y los valores en null.
- `ultimoDatoReal` (ms) dice cuándo llegó de verdad la última medición.
- `riego` es true si la válvula de esa cama estuvo abierta en algún momento del paso.
- `auto` es el modo automático de la zona del gateway según el último health conocido.
- Nunca salen device_id, dev_eui, temas MQTT ni credenciales.
"""
import math
from datetime import datetime, timedelta, timezone

from django.core.cache import cache
from django.db import connections

PASO_S = 30 * 60
VENTANA_MAXIMA = timedelta(days=8)
VENTANA_DEFECTO = timedelta(days=2)
CACHE_S = 60
DB = "mqtt"


def _bucket_sql(vendor):
    if vendor == "postgresql":
        return f"FLOOR(EXTRACT(EPOCH FROM medido_en) / {PASO_S})::bigint"
    # sqlite (pruebas)
    return f"CAST(CAST(strftime('%%s', medido_en) AS INTEGER) / {PASO_S} AS INTEGER)"


def _consulta(sql, params):
    with connections[DB].cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _r(valor, decimales=1):
    return None if valor is None else round(float(valor), decimales)


def _ventana(desde, hasta):
    ahora = datetime.now(timezone.utc)
    hasta = min(hasta or ahora, ahora + timedelta(minutes=PASO_S // 60))
    desde = desde or (hasta - VENTANA_DEFECTO)
    if hasta <= desde:
        raise ValueError("`hasta` debe ser posterior a `desde`.")
    # Holgura de un paso: «los últimos 8 días» pedidos desde el navegador llegan con milisegundos de más.
    if hasta - desde > VENTANA_MAXIMA + timedelta(seconds=PASO_S):
        raise ValueError("La ventana máxima es de 8 días por consulta.")
    return desde, hasta


def _pasos(desde, hasta):
    b0 = math.floor(desde.timestamp() / PASO_S)
    b1 = math.ceil(hasta.timestamp() / PASO_S)
    return list(range(b0, b1))


def _escalon(eventos, pasos, inicial=None):
    """Valor vigente por paso a partir de eventos [(timestamp_s, valor)] ordenados. Devuelve, por
    paso, (valor al empezar el paso, valores que tomó durante el paso)."""
    salida = {}
    i, actual = 0, inicial
    for b in pasos:
        inicio, fin = b * PASO_S, (b + 1) * PASO_S
        while i < len(eventos) and eventos[i][0] < inicio:
            actual = eventos[i][1]
            i += 1
        al_empezar = actual
        durante = []
        while i < len(eventos) and eventos[i][0] < fin:
            actual = eventos[i][1]
            durante.append(actual)
            i += 1
        salida[b] = (al_empezar, durante)
    return salida


def _tolerancia_pasos():
    from django.conf import settings

    minutos = int(getattr(settings, "HUERTAS_TOLERANCIA_MINUTOS", 180) or 0)
    return max(0, minutos * 60 // PASO_S)


def _rellenar(lecturas, tolerancia):
    """Repite el último valor medido en los pasos sin lectura, hasta `tolerancia` pasos."""
    ultimo = {}  # campo -> (valor, índice del paso donde se midió)
    ultimo_real = None
    for i, l in enumerate(lecturas):
        campos = [("temperatura", l), ("humedadAire", l), ("temperaturaSuelo", l)]
        campos += [("humedad", e) for e in l["eras"]]
        real = any(d[c] is not None for c, d in campos)
        if real:
            ultimo_real = i
        relleno = False
        for campo, d in campos:
            clave = (campo, d.get("zona"))
            if d[campo] is not None:
                ultimo[clave] = (d[campo], i)
            elif clave in ultimo and i - ultimo[clave][1] <= tolerancia:
                d[campo] = ultimo[clave][0]
                relleno = True
        if not l["enLinea"] and ultimo_real is not None and i - ultimo_real <= tolerancia and (relleno or real):
            l["enLinea"] = True
        l["relleno"] = relleno
        l["minutosSinDato"] = (i - ultimo_real) * PASO_S // 60 if ultimo_real is not None else None
    return lecturas


def lecturas_de(agrohub, camas, desde=None, hasta=None):
    """Lecturas agregadas de la huerta. `camas` es la lista de Cama en el orden en que se pintan."""
    desde, hasta = _ventana(desde, hasta)
    pasos = _pasos(desde, hasta)
    tolerancia = _tolerancia_pasos()
    # Se lee también lo de antes de la ventana (la tolerancia) para poder repetir el último valor
    # en sus primeros pasos; esos pasos previos no se devuelven.
    pasos_lectura = list(range(pasos[0] - tolerancia, pasos[0])) + pasos if pasos else pasos
    desde_lectura = datetime.fromtimestamp(pasos_lectura[0] * PASO_S, timezone.utc) if pasos else desde
    base = {
        "paso_minutos": PASO_S // 60,
        "desde": datetime.fromtimestamp(pasos[0] * PASO_S, timezone.utc) if pasos else desde,
        "hasta": hasta,
        "camas": [{"zona": c.zona, "con_sensor": bool(c.sensor), "con_valvula": c.conectada} for c in camas],
    }
    if not agrohub.dispositivo:
        return {**base, "sin_gateway": True, "lecturas": []}

    clave = f"huertas:lecturas:{agrohub.id}:{pasos[0]}:{pasos[-1]}:" + ",".join(
        f"{c.zona}-{c.sensor}-{c.gateway_zona}-{c.valvula}" for c in camas
    )
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado

    device = agrohub.dispositivo
    vendor = connections[DB].vendor
    b = _bucket_sql(vendor)
    rango = [device, desde_lectura, hasta]

    ambiente = {
        fila[0]: fila[1:]
        for fila in _consulta(
            f"SELECT {b} AS b, AVG(temperatura), AVG(humedad), COUNT(*) FROM lecturas_ambiente "
            f"WHERE device_id = %s AND medido_en >= %s AND medido_en < %s GROUP BY b",
            rango,
        )
    }
    suelo = {}  # (dev_eui, b) -> (humedad, temperatura)
    suelo_paso = {}  # b -> [temperaturas]
    con_suelo = set()  # pasos con alguna lectura de suelo
    for dev_eui, paso, hum, temp in _consulta(
        f"SELECT dev_eui, {b} AS b, AVG(humedad_suelo), AVG(temperatura_suelo) FROM lecturas_suelo "
        f"WHERE device_id = %s AND medido_en >= %s AND medido_en < %s GROUP BY dev_eui, b",
        rango,
    ):
        suelo[(dev_eui, paso)] = (hum, temp)
        con_suelo.add(paso)
        if temp is not None:
            suelo_paso.setdefault(paso, []).append(temp)

    # Válvulas: eventos por (zona, válvula) desde un día antes, para saber cómo estaban al empezar.
    from apps.riego_iot.models import EstadoValvula, Healthcheck

    eventos_valvula = {}
    for medido, ro1, ro2, zona in (
        EstadoValvula.objects.using(DB)
        .filter(device_id=device, medido_en__gte=desde_lectura - timedelta(days=1), medido_en__lt=hasta)
        .order_by("medido_en")
        .values_list("medido_en", "ro1", "ro2", "payload_crudo__zona")
    ):
        for valvula, estado in (("RO1", ro1), ("RO2", ro2)):
            if estado:
                eventos_valvula.setdefault((zona, valvula), []).append((medido.timestamp(), estado == "abierta"))

    eventos_auto = {}
    for medido, zonas_auto in (
        Healthcheck.objects.using(DB)
        .filter(device_id=device, medido_en__gte=desde_lectura - timedelta(hours=6), medido_en__lt=hasta)
        .order_by("medido_en")
        .values_list("medido_en", "payload_crudo__zonas_auto")
    ):
        for zona, valor in (zonas_auto or {}).items():
            eventos_auto.setdefault(zona, []).append((medido.timestamp(), bool(valor)))

    por_cama = []
    for c in camas:
        valv = _escalon(eventos_valvula.get((c.gateway_zona, c.valvula), []), pasos_lectura) if c.conectada else None
        auto = _escalon(eventos_auto.get(c.gateway_zona, []), pasos_lectura) if c.gateway_zona else None
        por_cama.append((c, valv, auto))

    lecturas = []
    for paso in pasos_lectura:
        amb = ambiente.get(paso)
        temps = suelo_paso.get(paso)
        en_linea = bool(amb) or paso in con_suelo
        eras = []
        for c, valv, auto in por_cama:
            hum = suelo.get((c.sensor, paso), (None, None))[0] if c.sensor else None
            riego = None
            if valv is not None:
                al_empezar, durante = valv[paso]
                if al_empezar is not None or durante:
                    riego = bool(al_empezar) or any(durante)
            modo = None
            if auto is not None:
                al_empezar, durante = auto[paso]
                modo = durante[-1] if durante else al_empezar
            eras.append({"zona": c.zona, "humedad": _r(hum), "riego": riego, "auto": modo})
        lecturas.append(
            {
                "t": paso * PASO_S * 1000,
                "temperatura": _r(amb[0]) if amb else None,
                "humedadAire": _r(amb[1]) if amb else None,
                "temperaturaSuelo": _r(sum(temps) / len(temps)) if temps else None,
                "enLinea": en_linea,
                "eras": eras,
            }
        )

    _rellenar(lecturas, tolerancia)
    reales = [l["t"] for l in lecturas if not l["relleno"] and l["enLinea"]]
    lecturas = lecturas[len(pasos_lectura) - len(pasos):]  # solo la ventana pedida
    resultado = {
        **base,
        "sin_gateway": False,
        "tolerancia_minutos": tolerancia * PASO_S // 60,
        "ultimoDatoReal": reales[-1] if reales else None,
        "lecturas": lecturas,
    }
    cache.set(clave, resultado, CACHE_S)
    return resultado


def humedad_actual(agrohub, cama, maximo=timedelta(hours=2)):
    """Última humedad de tierra del sensor de la cama (si es reciente), para anotar en un reporte."""
    if not (agrohub.dispositivo and cama and cama.sensor):
        return None
    from apps.riego_iot.models import LecturaSuelo

    fila = (
        LecturaSuelo.objects.using(DB)
        .filter(device_id=agrohub.dispositivo, dev_eui=cama.sensor, humedad_suelo__isnull=False)
        .order_by("-medido_en")
        .values_list("medido_en", "humedad_suelo")
        .first()
    )
    if not fila or datetime.now(timezone.utc) - fila[0] > maximo:
        return None
    return fila[1]


def valvula_abierta(agrohub, cama):
    if not (agrohub.dispositivo and cama and cama.conectada):
        return False
    from apps.riego_iot.models import EstadoValvula

    for ro1, ro2, zona in (
        EstadoValvula.objects.using(DB)
        .filter(device_id=agrohub.dispositivo)
        .order_by("-medido_en")
        .values_list("ro1", "ro2", "payload_crudo__zona")[:20]
    ):
        if zona == cama.gateway_zona:
            return (ro1 if cama.valvula == "RO1" else ro2) == "abierta"
    return False


def sensores_del_gateway(device_id, dias=7):
    """Sondas de tierra que reportaron en los últimos días (para que el equipo arme las camas)."""
    from apps.riego_iot.models import LecturaSuelo

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    vistos = {}
    for dev_eui, medido, payload_equipo, hum in (
        LecturaSuelo.objects.using(DB)
        .filter(device_id=device_id, medido_en__gte=desde)
        .order_by("-medido_en")
        .values_list("dev_eui", "medido_en", "payload_crudo__equipo", "humedad_suelo")[:5000]
    ):
        if dev_eui and dev_eui not in vistos:
            vistos[dev_eui] = {"sensor": dev_eui, "equipo": payload_equipo, "ultima_lectura": medido, "humedad_suelo": hum}
    return list(vistos.values())


def zonas_del_gateway(device_id):
    """Zonas y válvulas que el gateway ha reportado (health → valvulas), p. ej. {"z1": ["RO1","RO2"]}."""
    from apps.riego_iot.models import Healthcheck

    valvulas = (
        Healthcheck.objects.using(DB)
        .filter(device_id=device_id)
        .order_by("-medido_en")
        .values_list("valvulas", flat=True)
        .first()
    ) or {}
    return {zona: sorted(v.keys()) for zona, v in valvulas.items() if isinstance(v, dict)}
