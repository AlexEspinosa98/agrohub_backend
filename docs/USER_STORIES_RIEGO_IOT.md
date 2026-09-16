# Historias de usuario — `apps.riego_iot` (gateways de riego / dashboard MQTT)

**Última actualización:** 2026-09-16 · **Rol:** administrador de la plataforma AgroHub (panel
interno, no la app de campo). Todos los endpoints requieren el header `X-API-Key` (clave de
administración de riego IoT, distinta de los tokens de usuario de `user_activity`) — ver
`docs/API_RIEGO_IOT.md` para la referencia técnica completa con ejemplos reales.

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
