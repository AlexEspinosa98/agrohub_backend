# Historias de usuario — `apps.riego_iot` (gateways de riego / dashboard MQTT)

**Última actualización:** 2026-10-11 · **Quién:** equipo de la plataforma AgroHub (panel interno,
no la app de campo). Todos los endpoints de administración requieren `Authorization: Token <token>`
de una cuenta con rol **`admin`, `superadmin` o `investigador`** — mismo login que el resto de la app
(`user_activity`), no una API key separada. Ver `docs/API_RIEGO_IOT.md` para la referencia técnica
completa con ejemplos reales.

## Quién ve qué

| Qué | `admin` / `superadmin` / `investigador` | `user` (y sin rol) | Visitante sin cuenta |
|---|---|---|---|
| Gateways, dashboard, históricos (HU-05 a HU-11) | sí | **no** (`403`) | no (`401`) |
| Alta, nombre, baja y contraseña de gateways (HU-01 a HU-04) | sí | no | no |
| Configuración remota y órdenes de válvula (HU-12 a HU-14) | sí | no | no |
| Historial de cambios (HU-15) | sí | no | no |
| **Datos abiertos del lugar** (última temperatura, humedad y suelo) — HU-16 | sí | sí | **sí, sin token** |

El módulo de riego es **solo del equipo**. Lo único que ve el público (y cualquier usuario) son los
**datos ambientales abiertos** de cada AgroHub, a través del geovisor (`GET /agrohubs/<id>/datos`), que
nunca expone válvulas, configuración, salud ni credenciales.

---

### HU-01 — Dar de alta un gateway nuevo
Como administrador quiero registrar un gateway de riego (Milesight UG56) nuevo, para que empiece
a poder conectarse al broker MQTT y enviar sus lecturas.
- `POST /riego-iot/dispositivos/` con `device_id`, `client_id` y opcionalmente `nombre`.
- Efecto real, no solo una fila en base de datos: crea el usuario/contraseña del gateway en
  Mosquitto y su ACL (solo puede publicar/suscribirse a su propio namespace de tópicos,
  `ahub/<device_id>/...`), y recarga el broker para que el cambio tome efecto de inmediato.
- La contraseña generada se devuelve **una sola vez**, en la respuesta del `POST` — no queda
  guardada en ningún lado en texto plano y no se puede volver a consultar. Si se pierde, hay que
  rotarla (HU-04), no hay forma de recuperarla.
- Rechaza con `422` si `device_id`/`client_id` no cumplen el formato esperado, o si ya existe un
  dispositivo **activo** con ese `device_id` (para reactivar uno dado de baja hay que usar otro
  `device_id`, o pedir soporte para reactivar el registro existente).
- Si falla la escritura en Mosquitto (raro — problema de permisos/disco), responde `502` sin
  dejar el dispositivo a medio crear.

### HU-02 — Editar el nombre de un gateway ya registrado
Como administrador quiero poder ponerle o cambiarle el nombre a un gateway después de creado
(ej. "Finca La Esperanza"), para identificarlo por sitio en vez de por su `device_id` técnico,
sin tener que darlo de baja y perder su credencial MQTT en el proceso.
- `PATCH /riego-iot/dispositivos/{device_id}/` con `{"nombre": "..."}`.
- Solo `nombre` es editable aquí — `device_id`/`client_id`/`base_topic` identifican la
  credencial MQTT real; cambiarlos requeriría recrearla, no es un simple update de fila.
- `404` si el `device_id` no existe.

### HU-03 — Dar de baja un gateway
Como administrador quiero revocar el acceso de un gateway que ya no está en uso (se dañó, se
retiró de campo, se reemplazó), para que deje de poder conectarse al broker sin perder su
historial de lecturas.
- `DELETE /riego-iot/dispositivos/{device_id}/` — borra su usuario/ACL de Mosquitto de inmediato
  y marca el registro `activo: false`.
- **Las lecturas históricas NO se borran** — siguen consultables en todos los endpoints de
  `/dashboard/{device_id}/lecturas/...` (HU-07 a HU-11); solo se corta el acceso al broker.
- `400` si el dispositivo no tiene `client_id` registrado (fue creado antes de esta API, o solo
  se detectó por telemetría sin pasar por `POST /dispositivos/`) — en ese caso hay que borrar la
  credencial a mano en Mosquitto primero.

### HU-04 — Rotar la contraseña de un gateway
Como administrador quiero generar una contraseña nueva para un gateway sin cambiar su
`device_id`/`client_id`, para recuperar el acceso si se perdió la contraseña original o se
sospecha que se filtró.
- `POST /riego-iot/dispositivos/{device_id}/rotar-password/`.
- La contraseña anterior deja de funcionar **de inmediato** al aplicarse (recarga el broker) —
  el gateway queda desconectado hasta que se le actualice la contraseña físicamente (Node-RED →
  nodo "Servidor MQTT").
- Igual que en el alta, la nueva contraseña se devuelve una sola vez en la respuesta.

### HU-05 — Ver de un vistazo el estado de todos los gateways activos
Como administrador quiero una vista única con el último dato de cada gateway activo (¿está en
línea?, última temperatura/humedad, último estado de válvulas...), para monitorear toda la red
de riego sin tener que consultar dispositivo por dispositivo.
- `GET /riego-iot/dashboard/resumen/` — un objeto por gateway activo, con su última lectura de
  ambiente, suelo, válvulas y health, más `en_linea` (calculado) y `ultimo_visto`.
- Un gateway recién dado de alta que aún no se instaló físicamente aparece con todos los campos
  de datos en `null` y `en_linea: false` — es el estado esperado, no un error (`404` solo ocurre
  si el `device_id` no existe en absoluto).
- Pensado para refrescarse periódicamente (cada 30-60s, coincide con el intervalo real de los
  healthchecks) — ningún endpoint de lectura tiene efectos secundarios.

### HU-06 — Ver el resumen de un gateway puntual
Como administrador quiero el mismo resumen de HU-05 pero para un solo gateway, para revisar su
estado sin traer el de los otros 15.
- `GET /riego-iot/dashboard/{device_id}/` — misma forma que una entrada de `/dashboard/resumen/`.
- `en_linea` se calcula igual que decide el propio gateway si perdió la nube: `true` solo si el
  último evento de conexión fue `"online"` **y** hay una lectura de los últimos 3 minutos (misma
  ventana del manual UG56, sección 08, para el failover nube→local).

### HU-07 — Consultar el histórico de temperatura/humedad ambiente, filtrado por fecha
Como administrador quiero ver la serie histórica de temperatura y humedad de un gateway en un
rango de fechas, para graficar su evolución (ej. detectar un pico de temperatura, comparar
semanas) en vez de solo ver el último valor.
- `GET /riego-iot/dashboard/{device_id}/lecturas/ambiente/?desde=...&hasta=...&limite=...`
  — `desde`/`hasta` en ISO 8601 (por defecto, últimos 7 días); `limite` tope de filas (por
  defecto 500, máximo 5000).
- Cada fila trae `recuperado: true` cuando el gateway estuvo desconectado, guardó la lectura en
  su microSD local y la reenvió al reconectar — `medido_en` sigue siendo el momento real de la
  medición, no el momento en que llegó al servidor (puede ser horas antes).

### HU-08 — Consultar el histórico de humedad/temperatura/conductividad de suelo, filtrado por fecha
Como administrador quiero lo mismo que HU-07 pero para las variables de suelo, para decidir
cuándo regar con datos reales en vez de solo el último valor puntual.
- `GET /riego-iot/dashboard/{device_id}/lecturas/suelo/` — mismos parámetros y semántica de
  `recuperado` que HU-07.

### HU-09 — Consultar el histórico de estado de las electroválvulas
Como administrador quiero ver cuándo se abrió/cerró cada válvula de un gateway y quién originó
ese cambio, para auditar el riego de un periodo (¿regó automático o alguien lo forzó
manualmente?) en vez de solo ver el estado actual.
- `GET /riego-iot/dashboard/{device_id}/lecturas/valvulas/` — mismos `desde`/`hasta`/`limite` que
  HU-07/HU-08. Cada fila trae `ro1`/`ro2` (estado de cada electroválvula), `origen` y
  `ultimo_comando`.
- `origen` distingue la **intención** de un cambio (`"auto"` = lógica automática por humedad de
  suelo, `"remoto"` = comando desde la plataforma, `"manual"` = botón físico en el gateway) del
  **hecho confirmado** (`"reportado"` = el controlador confirmó que la válvula efectivamente
  quedó en ese estado — la fuente de verdad si hay que reconciliar una discrepancia).
- Antes de esta historia, solo se podía ver el último estado (vía HU-05/HU-06) — no había forma
  de reconstruir el historial de riego de un gateway.

### HU-10 — Consultar el histórico de health/conectividad de un gateway
Como administrador quiero ver la serie histórica de healthchecks de un gateway (modo de control
vigente, si hubo un override manual activo), para diagnosticar problemas pasados — ej. "¿desde
cuándo está en modo local en vez de nube?" — en vez de solo el último healthcheck.
- `GET /riego-iot/dashboard/{device_id}/lecturas/health/` — mismos parámetros que HU-07 a HU-09.
  Cada fila trae `mqtt_conectado`, `ultimo_uplink`, `modo_control` (`"nube"`/`"local"`),
  `override_manual`, y el `valvulas` que el propio gateway reportó tener en ese healthcheck.
- Antes de esta historia, igual que HU-09, solo se veía el último valor.

### HU-11 — Consultar el histórico de conexión (online/offline) para graficar uptime
Como administrador quiero un log de cuándo un gateway se conectó y desconectó del broker, para
armar un gráfico de disponibilidad (uptime) o detectar patrones de caídas (ej. "se desconecta
todas las noches"), algo que no se puede reconstruir solo con el estado "en línea ahora mismo".
- `GET /riego-iot/dashboard/{device_id}/lecturas/conexion/` — mismos `desde`/`hasta`/`limite`,
  pero **filtrando por `recibido_en`, no por `medido_en`** como los demás históricos: este dato
  no lo mide el gateway, lo genera Mosquitto cuando la conexión cambia de estado (LWT al
  desconectar, reconexión al volver).
- Cada fila es un evento (`{"recibido_en": ..., "estado": "online"|"offline"}`), no una medición
  — el frontend arma el gráfico de uptime a partir de la secuencia de eventos.
- Antes de esta historia no existía ningún endpoint para esto — el dato solo se usaba
  internamente para calcular `en_linea` en HU-05/HU-06, sin exponerse como historial.

---

## Control desde la plataforma (octubre 2026)

La plataforma **solo configura umbrales y manda órdenes manuales**; no publica el latido `cloud/health`,
así que cada gateway sigue decidiendo el riego solo. Todo va por MQTT con el usuario `agrohub-plataforma`.

### HU-12 — Ver la configuración vigente de un gateway
Como integrante del equipo quiero ver los umbrales de riego y el modo automático de cada zona, para saber con qué
reglas está regando hoy.
- `GET /riego-iot/dispositivos/<device_id>/config/` → `config` con `rev`, `origen` (`defecto` | `sd` | `remoto`),
  `aplicada_en` y, por zona, `auto` y `riego.RO1/RO2.{abrir, cerrar}`; `ultimo_rechazo` si el último cambio fue rechazado.
- `config` es `null` si el gateway nunca publicó configuración. **Hoy solo `device0014` la publica**; los demás
  necesitan el flow de Node-RED v3.
- `503` si el broker MQTT no está disponible.

### HU-13 — Cambiar umbrales y modo automático
Como integrante del equipo quiero ajustar cuándo se abre y se cierra cada válvula, para adaptar el riego al cultivo.
- `PUT /riego-iot/dispositivos/<device_id>/config/` con un cambio **parcial**:
  `{"zonas": {"z1": {"riego": {"RO1": {"abrir": 28, "cerrar": 38}}}, "z3": {"auto": false}}}`.
- El backend calcula `rev = vigente + 1`, valida (0 a 100, `cerrar − abrir ≥ 3`, zona y válvula existentes, `auto`
  booleano) y espera hasta ~20 s la confirmación del gateway.
- `data.resultado`: `aplicada` (200) · `rechazada` por el gateway (422, con `errores`) · `invalida` por validación previa (422)
  · `sin_respuesta` (202: offline o `rev` vieja; **no darlo por aplicado**, volver a leer la configuración).
- Si cambias un solo extremo de un rango, la histéresis se valida contra el valor vigente del otro.

### HU-14 — Abrir o cerrar una válvula ahora
Como integrante del equipo quiero mandar una orden manual a una válvula, para probar o regar en un momento concreto.
- `POST /riego-iot/dispositivos/<device_id>/valvulas/` con `{"zona": "z1", "valvula": "RO1", "accion": "abrir"}`
  (`accion`: `abrir` | `cerrar`).
- Responde `202` con `resultado`: `enviada` (el gateway reconoció la orden) o `sin_eco` (enviada, posiblemente offline);
  `422` si la orden es inválida.
- La orden activa un **override manual de 30 min** en esa válvula. La confirmación física tarda hasta ~10 min y se ve en
  `GET /riego-iot/dashboard/<device_id>/lecturas/valvulas/` (`origen: "reportado"`).
- Una orden por controlador a la vez y esperar su confirmación antes de la siguiente. Ver la guía de pruebas de N14.

### HU-15 — Historial de cambios
Como integrante del equipo quiero saber quién cambió qué y con qué resultado, para hacer seguimiento.
- `GET /riego-iot/dispositivos/<device_id>/cambios/?limite=100` → `tipo` (`config` | `valvula`), `rev`, `resultado`, `errores`,
  `payload`, `creado_en`, `usuario` y `usuario_id`. Quedan registrados también los intentos inválidos.

### HU-16 — Datos abiertos del lugar (lo que ve el público)
Como visitante del geovisor quiero ver la temperatura y humedad actuales de un AgroHub, para conocer las condiciones del lugar.
- Cada AgroHub se asocia a su gateway desde el admin (campo `dispositivo` de la ficha; ver `HU_AGROHUBS_GEOVISOR.md`, HU-G07).
- `GET /agrohubs/<id>/datos` (**sin token**) → `ultima_lectura`, `en_linea`, `ambiente {temperatura, humedad}` y
  `suelo {humedad_suelo, temperatura_suelo, conductividad}`. `404` si el AgroHub no tiene dispositivo.

---

## Resumen de qué quedó cubierto vs. qué faltaba antes de esta ronda

| Dato que envía el gateway | ¿Histórico filtrable por fecha? | Historia |
|---|---|---|
| Ambiente (temperatura/humedad) | Ya existía | HU-07 |
| Suelo (humedad/temp/conductividad) | Ya existía | HU-08 |
| Válvulas (ro1/ro2/origen/comando) | **Nuevo en esta ronda** | HU-09 |
| Health (modo_control/override_manual) | **Nuevo en esta ronda** | HU-10 |
| Conexión (online/offline) | **Nuevo en esta ronda** | HU-11 |
| Nombre del dispositivo | Editable | **Nuevo en esta ronda** — HU-02 |

Con esto, los 5 tipos de dato que el gateway reporta (ambiente, suelo, válvulas, health,
conexión) tienen el mismo nivel de visualización: resumen en vivo (HU-05/HU-06) **y** histórico
filtrable por fecha (HU-07 a HU-11) — antes solo ambiente y suelo tenían la parte de histórico.
