# Riego IoT — historias de usuario completas (administración y datos abiertos)

Documento único del módulo de riego: el **panel del equipo** (administrar gateways, ver el dashboard,
configurar y mandar órdenes) y la parte **abierta** al público (datos ambientales de cada AgroHub en
el geovisor). **Cada historia indica los roles que pueden usarla.**

Base URL: `https://back.alunaia.co/api/agrohub` · Referencia técnica con más ejemplos: `API_RIEGO_IOT.md`.
Autenticación del panel: `POST /user-activity/users/login` → `Authorization: Token <token>`.

## 1. Roles y accesos de un vistazo

| Quién | Panel de riego (Parte A) | Datos abiertos (Parte B) |
|---|---|---|
| **Visitante sin cuenta** | no (`401`) | **sí, sin token** |
| **`user`** | no (`403`) | sí |
| **Sin rol asignado** | no (`403`) | sí |
| **`comunicaciones`** | no (`403`) | sí |
| **`investigador`** | **sí, todo** | sí |
| **`admin`** | **sí, todo** | sí |
| **`superadmin`** | **sí, todo** | sí |

- **"Equipo"** en este documento = `admin`, `superadmin` e `investigador`: pueden ver, administrar y
  controlar los dispositivos. No hay un nivel intermedio (solo ver / ver y controlar).
- Para dar el rol: `PUT /user-activity/users/<id>/role` (lo hace un superadmin).

## 2. Convenciones

- **Forma de las respuestas.** Los endpoints históricos (alta, listado, dashboard, lecturas) devuelven el
  cuerpo directo (una lista u objeto, sin envoltura). Los endpoints nuevos de control
  (`config`, `valvulas`, `cambios`) y los de AgroHubs devuelven `{"status","message","data"}`.
- **Errores:** `401` sin token · `403` rol no permitido (`{"detail": "Requiere rol admin o investigador"}`) ·
  `404` no existe · `422` validación (`{"status":422,"errores":[{"campo","mensaje",…}]}`) · `502` falló
  Mosquitto · `503` el broker MQTT no está disponible.
- **Fechas** en ISO 8601 (UTC). Todos los endpoints de lectura son de solo lectura, sin efectos secundarios.
- **Gateways:** 16 activos (`device0001` … `device0016`). Hoy **solo `device0014` publica configuración
  remota**; los demás necesitan el flow de Node-RED v3 para HU-12/13.

---

# PARTE A — Panel del equipo (admin, superadmin, investigador)

> **Roles de toda la Parte A: `admin`, `superadmin`, `investigador`.** Cualquier otro rol recibe `403`.

## A1. Administrar gateways

### HU-17 — Ver la lista y el detalle de los gateways
**Roles:** admin, superadmin, investigador.
Como integrante del equipo quiero ver todos los gateways registrados, para saber cuáles existen y cuáles están activos.
- `GET /riego-iot/dispositivos/` (opcional `?solo_activos=true`) → lista ordenada por `device_id`.
- `GET /riego-iot/dispositivos/<device_id>/` → un gateway; `404` si no existe.
- Cada uno: `device_id`, `base_topic`, `client_id`, `nombre`, `activo`, `primera_vez_visto`, `ultima_vez_visto`.

### HU-01 — Dar de alta un gateway nuevo
**Roles:** admin, superadmin, investigador.
Como integrante del equipo quiero registrar un gateway de riego (Milesight UG56), para que pueda conectarse al broker y enviar lecturas.
- `POST /riego-iot/dispositivos/` con `device_id`, `client_id` y opcional `nombre`.
- Efecto real: crea usuario/contraseña en Mosquitto y su ACL (solo su propio namespace `ahub/<device_id>/…`, incluidos
  `config/state`, `config/set` y `control/valvulas`) y recarga el broker.
- La contraseña se devuelve **una sola vez** en la respuesta; si se pierde hay que rotarla (HU-04).
- `422` si el formato no es válido (`device_id`: minúsculas, números, `-`, `_`, 3 a 40) o ya existe uno **activo** con ese id;
  `502` si falla Mosquitto (sin dejar el dispositivo a medio crear).

### HU-02 — Cambiar el nombre de un gateway
**Roles:** admin, superadmin, investigador.
- `PATCH /riego-iot/dispositivos/<device_id>/` con `{"nombre": "Finca La Esperanza"}`. Solo `nombre` es editable;
  `device_id`/`client_id` son la identidad MQTT. `404` si no existe.
- Este nombre es el que aparece en el selector al asociar un AgroHub a su dispositivo (HU-18).

### HU-03 — Dar de baja un gateway
**Roles:** admin, superadmin, investigador.
- `DELETE /riego-iot/dispositivos/<device_id>/` → revoca de inmediato su acceso a Mosquitto y lo marca `activo: false`.
- **Las lecturas históricas no se borran.** `400` si no tiene `client_id` registrado (hay que borrar su credencial a mano).
- Pedir confirmación en el front.

### HU-04 — Rotar la contraseña de un gateway
**Roles:** admin, superadmin, investigador.
- `POST /riego-iot/dispositivos/<device_id>/rotar-password/` → la anterior deja de funcionar **al instante** (el gateway
  queda desconectado hasta actualizarla en Node-RED, nodo "Servidor MQTT"). La nueva se muestra una sola vez.

## A2. Dashboard y datos históricos (solo lectura)

### HU-05 — Estado de todos los gateways
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/resumen/` → un objeto por gateway activo con `en_linea`, `ultimo_visto`, `modo_control` y la última
  lectura de `ambiente`, `suelo`, `valvulas` y `health`.
- Un gateway recién creado sin instalar sale con datos `null` y `en_linea: false` (es lo esperado). Refrescar cada 30–60 s.

### HU-06 — Estado de un gateway
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/` → mismo objeto que una entrada de HU-05. `en_linea` es `true` solo si el último
  evento fue `online` **y** hubo una lectura en los últimos 3 minutos.

### HU-07 — Histórico de temperatura y humedad ambiente
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/lecturas/ambiente/?desde=&hasta=&limite=` (por defecto últimos 7 días; `limite` 500, máx. 5000).
- `recuperado: true` = el gateway estuvo desconectado, guardó la lectura en su microSD y la reenvió; `medido_en` es el momento real.

### HU-08 — Histórico de suelo
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/lecturas/suelo/` — humedad, temperatura y conductividad del suelo; mismos parámetros que HU-07.

### HU-09 — Histórico de electroválvulas
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/lecturas/valvulas/` — `ro1`/`ro2`, `origen` y `ultimo_comando`.
- `origen`: `auto` (lógica por humedad), `remoto` (orden de la plataforma), `manual` (botón físico) y `reportado`
  (**el controlador confirmó** el estado: la fuente de verdad).

### HU-10 — Histórico de salud del gateway
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/lecturas/health/` — `mqtt_conectado`, `ultimo_uplink`, `modo_control` (`nube`/`local`),
  `override_manual` y `valvulas`. Sirve para saber desde cuándo opera en modo local.

### HU-11 — Histórico de conexión (uptime)
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dashboard/<device_id>/lecturas/conexion/` — eventos `online`/`offline`. **Filtra por `recibido_en`**
  (lo genera Mosquitto), no por `medido_en`. El front arma el gráfico de disponibilidad con la secuencia de eventos.

## A3. Control desde la plataforma

La plataforma **solo configura umbrales y manda órdenes manuales**. No publica el latido `cloud/health`, así que cada gateway
**sigue decidiendo el riego solo**. Todo va por MQTT con el usuario `agrohub-plataforma` (permisos mínimos). Los cambios
quedan registrados (HU-15).

### HU-12 — Ver la configuración vigente
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dispositivos/<device_id>/config/` → `data.config`: `rev`, `origen` (`defecto` | `sd` | `remoto`), `aplicada_en`,
  `zonas` (por zona: `auto` y `riego.RO1`/`RO2` con `abrir`/`cerrar`), `inventario` y `ultimo_rechazo`.
- `config` es `null` si el gateway nunca publicó configuración. `503` si el broker no responde.

### HU-13 — Cambiar umbrales y modo automático
**Roles:** admin, superadmin, investigador.
- `PUT /riego-iot/dispositivos/<device_id>/config/` — cambio **parcial**:
  ```json
  { "zonas": { "z1": { "riego": { "RO1": { "abrir": 28, "cerrar": 38 } } }, "z3": { "auto": false } } }
  ```
- Reglas (todo o nada): números de 0 a 100, `cerrar − abrir ≥ 3` (usa el valor vigente si solo mandas un extremo), válvulas
  `RO1`/`RO2`, `auto` booleano, zona existente. El backend calcula la versión (`rev = vigente + 1`) y espera hasta ~20 s la confirmación.
- `data.resultado`: `aplicada` (200) · `rechazada` por el gateway (422, `errores`) · `invalida` por validación previa (422) ·
  `sin_respuesta` (202: offline o `rev` vieja; **no darlo por aplicado**, releer con HU-12).
- Frontend: mostrar "Aplicando…", y según el resultado, ✅ / errores / "Pendiente" con botón de reintento.

### HU-14 — Abrir o cerrar una válvula
**Roles:** admin, superadmin, investigador.
- `POST /riego-iot/dispositivos/<device_id>/valvulas/` con `{"zona": "z1", "valvula": "RO1", "accion": "abrir"}`
  (`accion`: `abrir` | `cerrar`).
- Responde `202`, `resultado`: `enviada` (el gateway reconoció la orden) o `sin_eco` (enviada, posiblemente offline); `422` si es inválida.
- La orden activa un **override manual de 30 min** en esa válvula. La **confirmación física tarda hasta ~10 min** y se ve en
  HU-09 (`origen: "reportado"`).
- Una orden por controlador a la vez y esperar su confirmación. **Terminar las pruebas con las válvulas cerradas.**

### HU-15 — Historial de cambios
**Roles:** admin, superadmin, investigador.
- `GET /riego-iot/dispositivos/<device_id>/cambios/?limite=100` (máx. 500) → `tipo` (`config` | `valvula`), `rev`, `resultado`,
  `errores`, `payload`, `creado_en`, `usuario`, `usuario_id`. Incluye también los intentos inválidos.

## A4. Asociar cada AgroHub a su dispositivo

### HU-18 — Asociar un AgroHub a un gateway
**Roles:** admin, superadmin, investigador (quienes administran AgroHubs).
Como integrante del equipo quiero indicar qué gateway pertenece a cada AgroHub, para que el geovisor muestre sus datos.
- `GET /agrohubs/dispositivos-disponibles` → `[{device_id, nombre}]`: gateways activos sin AgroHub (alimenta el selector).
- El campo `dispositivo` se envía en `POST /agrohubs/` o `PUT /agrohubs/<id>`; `null` o vacío lo desasocia.
- Reglas: el gateway debe existir y estar activo (`422`) y **un gateway solo puede estar en un AgroHub** (`422`).
- Detalle del formulario del AgroHub: `HU_AGROHUBS_GEOVISOR.md`.

---

# PARTE B — Datos abiertos (público)

> **Roles de la Parte B: todos, incluido el visitante sin cuenta (sin token).**

### HU-16 — Ver los datos ambientales de un AgroHub
**Roles:** público (visitante sin token), y cualquier usuario autenticado.
Como visitante del geovisor quiero ver la temperatura y humedad actuales de un AgroHub, para conocer las condiciones del lugar.
- `GET /agrohubs/<id>/datos` → última lectura ambiental y de suelo del gateway asociado:
  ```json
  { "status": 200, "message": "datos",
    "data": { "agrohub_id": 3, "numero": "AH-014", "ultima_lectura": "2026-10-11T21:17:54Z", "en_linea": true,
              "ambiente": { "medido_en": "…", "temperatura": 29.1, "humedad": 70.0 },
              "suelo": { "medido_en": "…", "humedad_suelo": 41.2, "temperatura_suelo": 27.5, "conductividad": 310 } } }
  ```
- `en_linea` es `true` si hubo una lectura en los últimos 3 minutos. `404` si el AgroHub no existe o **no tiene dispositivo asociado**.
- **Lo que NUNCA se expone al público:** estado de válvulas, configuración, salud del gateway, credenciales ni el historial de cambios.

### HU-19 — Distinguir en el mapa los AgroHubs con sensores
**Roles:** público (sin token).
- `GET /agrohubs/puntos` trae `tiene_dispositivo` (booleano) en cada punto, y `GET /agrohubs/<id>` trae `dispositivo: {device_id, nombre}` o `null`.
  El front puede mostrar un ícono de sensores y habilitar el botón "Ver datos en vivo" solo cuando sea `true`.

---

## 3. Resumen de endpoints por rol

| Endpoint | Visitante | `user` / sin rol / `comunicaciones` | `investigador` / `admin` / `superadmin` |
|---|---|---|---|
| `GET /agrohubs/puntos`, `GET /agrohubs/<id>`, `GET /agrohubs/<id>/datos` | sí | sí | sí |
| `GET /agrohubs/dispositivos-disponibles` | no | no | sí |
| `GET/POST/PATCH/DELETE /riego-iot/dispositivos/…` (HU-17, 01–04) | no | no | sí |
| `GET /riego-iot/dashboard/…` (HU-05 a 11) | no | no | sí |
| `GET/PUT …/config/`, `POST …/valvulas/`, `GET …/cambios/` (HU-12 a 15) | no | no | sí |

## 4. Checklist de integración

1. Panel de riego: mostrarlo **solo** si el rol del usuario (`data.role` del login) es `admin`, `superadmin` o `investigador`.
2. Pantalla de gateways con nombre editable (HU-02) para que el selector de AgroHubs (HU-18) sea legible: hoy los 16 no tienen nombre.
3. Edición de umbrales con la misma validación del backend (0–100, histéresis ≥ 3) y manejo de los 4 resultados de HU-13.
4. Órdenes de válvula: una por controlador, esperar confirmación (HU-09) y avisar que puede tardar ~10 min.
5. Geovisor: pintar `tiene_dispositivo`, consultar `/datos` solo para esos AgroHubs y refrescar cada 60 s.
6. Manejar `403` (rol no permitido), `503` (broker MQTT caído) y `202 sin_respuesta` (gateway offline).
