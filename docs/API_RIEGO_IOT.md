<title>API Riego IoT — Referencia</title>

# API de Riego IoT (`apps.riego_iot`) — referencia para frontend

**Última actualización:** 2026-08-30 · **Estado:** en producción, 16 gateways activos

Administración de gateways de riego (Milesight UG56) y dashboard de telemetría en tiempo real.
Los datos vienen de sensores de campo (temperatura/humedad ambiente, humedad/temperatura/
conductividad de suelo) y del estado de las electroválvulas de riego — todo 100% determinístico,
sin IA, escrito por un daemon de ingesta MQTT que corre 24/7 (ver `INSTALACION.md` en el repo
`mqtt_agrohub` para la infraestructura detrás de esta API).

## Base URL y autenticación

```
https://back.alunaia.co/api/agrohub/riego-iot/
```

Toda ruta requiere el header:

```
X-API-Key: <clave de administración>
```

Sin el header, o con una clave incorrecta, responde `401`:

```json
{"detail": "API key inválida o ausente (header X-API-Key)."}
```

## Resumen de endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/dispositivos/` | Lista todos los gateways |
| `POST` | `/dispositivos/` | Da de alta un gateway nuevo (crea su credencial MQTT) |
| `GET` | `/dispositivos/{device_id}/` | Detalle de un gateway |
| `DELETE` | `/dispositivos/{device_id}/` | Revoca el acceso de un gateway y lo marca inactivo |
| `POST` | `/dispositivos/{device_id}/rotar-password/` | Genera una contraseña nueva para ese gateway |
| `GET` | `/dashboard/resumen/` | Última lectura de cada tipo, de todos los gateways activos |
| `GET` | `/dashboard/{device_id}/` | Lo mismo, para un solo gateway |
| `GET` | `/dashboard/{device_id}/lecturas/ambiente/` | Histórico de temperatura/humedad ambiente |
| `GET` | `/dashboard/{device_id}/lecturas/suelo/` | Histórico de humedad/temperatura/conductividad de suelo |

---

## `GET /dispositivos/`

Lista todos los gateways registrados.

**Query params:** `solo_activos=true` — trae solo los que no han sido eliminados.

<details><summary>Ejemplo</summary>

```
GET /api/agrohub/riego-iot/dispositivos/?solo_activos=true
```

Response `200`:
```json
[
  {
    "device_id": "device0001",
    "base_topic": "ahub/device0001",
    "client_id": "ug56-agrohub1",
    "nombre": null,
    "activo": true,
    "primera_vez_visto": "2026-08-30T16:47:12.101Z",
    "ultima_vez_visto": "2026-08-30T16:47:12.101Z"
  },
  {
    "device_id": "device0002",
    "base_topic": "ahub/device0002",
    "client_id": "ug56-agrohub2",
    "nombre": null,
    "activo": true,
    "primera_vez_visto": "2026-08-30T16:47:13.554Z",
    "ultima_vez_visto": "2026-08-30T16:47:13.554Z"
  }
]
```
(hasta 16 elementos, uno por cada gateway dado de alta: `device0001`...`device0016`)
</details>

## `POST /dispositivos/`

Da de alta un gateway nuevo: crea su usuario/contraseña en el broker MQTT, su ACL (solo puede
tocar su propio namespace de tópicos), y su registro en la base de datos.

**Body:**
```json
{ "device_id": "device0017", "client_id": "ug56-agrohub17", "nombre": "Finca La Esperanza" }
```
- `device_id`: minúsculas, números, `-`/`_`, 3–40 caracteres. Convención del fabricante:
  `device0001`, `device0002`, ...
- `client_id`: alfanumérico + `-`/`_`, 3–60 caracteres. Debe ser único en el broker.
- `nombre`: opcional, texto libre para identificar el sitio.

<details><summary>Ejemplo</summary>

Response `201`:
```json
{
  "device_id": "device0017",
  "client_id": "ug56-agrohub17",
  "base_topic": "ahub/device0017",
  "password": "3f9a2c8e1b4d6f7a0e9c8b7a6d5e4f3c",
  "nota": "Guarda esta contraseña ahora — no se puede volver a consultar. Configurar en el gateway: host back.alunaia.co, puerto 8883, TLS, usuario y Client ID = client_id, keepalive 15s, clean session desactivado (ver manual UG56, sección 03)."
}
```

**La contraseña solo se muestra en esta respuesta — no hay forma de volver a consultarla.** Si
se pierde, usar `rotar-password` para generar una nueva.

Error — `device_id` ya existe y sigue activo, `422`:
```json
{
  "status": 422,
  "message": "Datos inválidos en la solicitud",
  "total_errores": 1,
  "errores": [{
    "campo": "",
    "mensaje": "Ya existe un dispositivo activo con device_id 'device0017'. Elimínalo primero o usa otro device_id.",
    "tipo_error": "invalid",
    "valor_recibido": {"device_id": "device0017", "client_id": "ug56-agrohub17"}
  }]
}
```

Error — `device_id`/`client_id` con formato inválido, `422`:
```json
{
  "status": 422,
  "message": "Datos inválidos en la solicitud",
  "total_errores": 1,
  "errores": [{
    "campo": "device_id",
    "mensaje": "device_id inválido — solo minúsculas, números, '-' y '_', 3 a 40 caracteres (convención del manual UG56: 'device0001', 'device0002', ...).",
    "tipo_error": "invalid",
    "valor_recibido": "Con Espacios!"
  }]
}
```

Error — problema creando la credencial en el broker (poco común), `502`:
```json
{ "detail": "mosquitto_passwd falló: ..." }
```
</details>

## `GET /dispositivos/{device_id}/`

<details><summary>Ejemplo</summary>

```
GET /api/agrohub/riego-iot/dispositivos/device0001/
```

Response `200`:
```json
{
  "device_id": "device0001",
  "base_topic": "ahub/device0001",
  "client_id": "ug56-agrohub1",
  "nombre": null,
  "activo": true,
  "primera_vez_visto": "2026-08-30T16:47:12.101Z",
  "ultima_vez_visto": "2026-08-30T16:47:12.101Z"
}
```

Error — no existe, `404`:
```json
{ "detail": "No existe el dispositivo 'device0099'." }
```
</details>

## `DELETE /dispositivos/{device_id}/`

Revoca el acceso del gateway al broker **de inmediato** (borra su usuario y su ACL) y lo marca
`activo: false`. **Las lecturas históricas NO se borran** — siguen disponibles en
`/dashboard/{device_id}/lecturas/...` para consulta, solo deja de recibir datos nuevos.

<details><summary>Ejemplo</summary>

```
DELETE /api/agrohub/riego-iot/dispositivos/device0017/
```

Response `204`: sin cuerpo.

Error — no existe, `404`:
```json
{ "detail": "No existe el dispositivo 'device0017'." }
```
</details>

## `POST /dispositivos/{device_id}/rotar-password/`

Genera una contraseña nueva para un gateway ya existente — la anterior deja de funcionar de
inmediato. Útil si se perdió la contraseña original o se sospecha que se filtró.

<details><summary>Ejemplo</summary>

```
POST /api/agrohub/riego-iot/dispositivos/device0001/rotar-password/
```

Response `200`:
```json
{
  "client_id": "ug56-agrohub1",
  "password": "93a8ddcbc7774c5014b669bd06dadc1e",
  "nota": "Guarda esta contraseña ahora y actualízala en el gateway — la anterior deja de funcionar de inmediato."
}
```

**Después de rotar, hay que actualizar la contraseña en el gateway físico** (Node-RED → nodo
"Servidor MQTT") — mientras no se actualice, ese gateway queda desconectado.
</details>

## `GET /dashboard/resumen/`

La vista principal para un dashboard: todos los gateways activos con su último dato de cada
tipo — las variables que se están recibiendo ahora mismo, de un vistazo.

<details><summary>Ejemplo real (probado en producción)</summary>

```
GET /api/agrohub/riego-iot/dashboard/resumen/
```

Response `200`:
```json
[
  {
    "device_id": "device0001",
    "en_linea": true,
    "ultimo_visto": "2026-08-30T21:50:00Z",
    "modo_control": null,
    "ambiente": {
      "medido_en": "2026-08-30T21:50:00Z",
      "temperatura": 26.8,
      "humedad": 68.5,
      "dev_eui": "24E124126D000001"
    },
    "suelo": null,
    "valvulas": null,
    "health": null
  },
  {
    "device_id": "device0002",
    "en_linea": false,
    "ultimo_visto": null,
    "modo_control": null,
    "ambiente": null,
    "suelo": null,
    "valvulas": null,
    "health": null
  }
]
```

Un gateway recién dado de alta (aún sin conectar en campo) aparece con todos los campos de datos
en `null` y `en_linea: false` — es el estado esperado hasta que se instale y configure
físicamente.
</details>

## `GET /dashboard/{device_id}/`

Mismo objeto que una entrada de `/dashboard/resumen/`, para un solo gateway.

<details><summary>Campos de la respuesta</summary>

| Campo | Tipo | Significado |
|---|---|---|
| `en_linea` | bool | `true` si el último `status` recibido fue `"online"` **y** hay una lectura (ambiente/suelo/health) dentro de los últimos 3 minutos. Misma ventana que usa el propio gateway para decidir si perdió la nube (ver `INSTALACION.md`). |
| `ultimo_visto` | datetime ó `null` | La más reciente entre `ambiente.medido_en`, `suelo.medido_en`, `health.medido_en`. |
| `modo_control` | `"nube"` \| `"local"` \| `null` | Quién está controlando el riego ahora mismo — `"nube"` mientras el gateway reciba el latido de la plataforma, `"local"` si perdió conexión y pasó a histéresis por humedad de suelo (ver `INSTALACION.md`, sección 7). `null` si nunca se recibió un healthcheck. |
| `ambiente` | objeto ó `null` | Última lectura de temperatura/humedad ambiente. `null` si el gateway no tiene sensor de ambiente o nunca reportó. |
| `suelo` | objeto ó `null` | Última lectura de humedad/temperatura/conductividad de suelo. |
| `valvulas` | objeto ó `null` | Último estado reportado de las electroválvulas — `origen` indica si vino de lógica automática (`"auto"`), un comando remoto (`"remoto"`), un botón físico (`"manual"`), o es el estado real confirmado por el controlador (`"reportado"`, la fuente de verdad). |
| `health` | objeto ó `null` | Último healthcheck completo del gateway (cada 60s) — incluye `mqtt_conectado`, `override_manual` (si un comando manual está bloqueando la lógica automática). |

</details>

## `GET /dashboard/{device_id}/lecturas/ambiente/` y `.../lecturas/suelo/`

Histórico de lecturas, más recientes primero.

**Query params:**
- `desde`, `hasta` — ISO 8601 (ej. `2026-08-01T00:00:00Z`). Por defecto, últimos 7 días.
- `limite` — máximo de filas a devolver (por defecto 500, tope 5000).

<details><summary>Ejemplo</summary>

```
GET /api/agrohub/riego-iot/dashboard/device0001/lecturas/ambiente/?limite=2
```

Response `200`:
```json
[
  {
    "medido_en": "2026-08-30T21:50:00Z",
    "temperatura": 26.8,
    "humedad": 68.5,
    "dev_eui": "24E124126D000001",
    "recuperado": false
  }
]
```

`recuperado: true` significa que el gateway estuvo desconectado, guardó la lectura en su microSD
local, y la reenvió al reconectar — `medido_en` sigue siendo el momento real de la medición, no
el momento en que llegó al servidor (puede ser horas antes).
</details>

---

## Notas para el frontend

- **Ningún endpoint de lectura tiene efectos secundarios** — se pueden llamar con la frecuencia
  que haga falta para refrescar un dashboard (recomendado: cada 30–60s, coincide con el
  intervalo real de los healthchecks).
- **Un gateway "sin datos todavía"** (recién creado, aún no instalado en campo) es un estado
  normal, no un error — `dashboard` devuelve todos los campos en `null` y `200`, no `404`. `404`
  solo ocurre si el `device_id` no existe en absoluto.
- **La contraseña de un gateway nunca es recuperable** por API — si el frontend necesita mostrar
  "¿tiene contraseña asignada?", usar el campo `client_id` de `/dispositivos/` (no nulo = tiene
  credencial activa).
- Todos los timestamps son UTC (`Z`).
