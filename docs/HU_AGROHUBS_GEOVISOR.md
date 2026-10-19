# Registro de AgroHubs y geovisor — historias de usuario

> Contratos para el frontend con JSON reales: **formulario manual** → [`API_AGROHUBS_FORMULARIO_FRONT.md`](API_AGROHUBS_FORMULARIO_FRONT.md) (HU-G08) · **mapa público** → [`API_GEOVISOR_FRONT.md`](API_GEOVISOR_FRONT.md).

Módulo **implementado**: app `apps/agrohubs`. El **administrador** registra
cada AgroHub (ficha con familias, lugar, asociaciones, cultivos, coordenadas y video) y el
**geovisor** del front pinta todos en un mapa con un solo GET liviano; al tocar un punto pide el
detalle.

Base URL: `https://back.alunaia.co/api/agrohub/agrohubs/` · Auth: `Authorization: Token <token>`
(solo para administración; `GET /puntos` y `GET /<id>` son **públicos**, sin token).

## 1. Modelo de datos

**AgroHub**

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `numero` | texto libre | sí | "Número de AgroHub" (ej. `AH-014`). **Único** |
| `nombre` | texto (máx. 150) | no | nombre público del punto (ej. `Algarrobo Cabecera`) |
| `tipologia`, `responsable`, `celular`, `tipo_fuente`, `punto_captacion` | texto | no | **datos de gestión, solo admin** (ver HU-G08); nunca salen en los endpoints públicos |
| `departamento` | texto | sí | |
| `municipio` | texto | sí | |
| `es_cabecera_municipal` | booleano | sí | |
| `vereda` | texto | **solo si** `es_cabecera_municipal = false` | si es cabecera se guarda vacía/`null` |
| `latitud` | decimal(9,6) | sí | −90 a 90 |
| `longitud` | decimal(9,6) | sí | −180 a 180 |
| `grupo_etnico` | opción | **no** | `indigena`, `afro`, `rom`, `raizal`, `ninguno`; vacío = no aplica |
| `comunidad` | texto (máx. 100) | **solo si** `grupo_etnico = indigena` | mismo catálogo y reglas que en asistencia (`GET /asistencia-eventos/comunidades`, "Otra" con texto libre); con otro grupo étnico se rechaza |
| `video` | archivo | no | material audiovisual (ver HU-G05) |
| `dispositivo` | texto (`device_id`) | **no** | gateway IoT asociado (ej. `device0014`); debe existir y estar activo en `riego_iot`, y **un dispositivo solo puede estar en un AgroHub** (ver HU-G07) |
| `creado_por`, `editado_por`, fechas | auditoría | automático | igual que en asistencia |

**Listas (relaciones, 1 AgroHub → N)**

| Lista | Contenido de cada ítem | Notas |
|---|---|---|
| `familias` | `nombre` (ej. "Familia Pérez Mejía"); **sin integrantes** | lista; puede estar vacía |
| `asociaciones` | texto libre | lista libre; puede estar vacía |
| `cultivos` | texto libre | lista libre; puede estar vacía |

## 2. Endpoints

| Acción | Método y path | Rol |
|---|---|---|
| Puntos para el mapa | `GET /puntos` | **público** (sin token) |
| Detalle de un AgroHub | `GET /<id>` | **público** (sin token) |
| Listar (tabla admin) | `GET /` | admin, superadmin, investigador |
| Crear | `POST /` | admin, superadmin, investigador |
| Editar | `PUT /<id>` (parcial) | admin, superadmin, investigador |
| Eliminar | `DELETE /<id>` | admin, superadmin, investigador |
| Subir/reemplazar video | `POST /<id>/video` · `DELETE /<id>/video` | admin, superadmin, investigador |
| Dispositivos IoT sin asociar | `GET /dispositivos-disponibles` | admin, superadmin, investigador |
| Datos abiertos del lugar | `GET /<id>/datos` | **público** (sin token) |
| Catálogos (departamentos/grupos étnicos) | `GET /catalogos` | admin, superadmin, investigador (alimenta el formulario) |

---

## 3. Historias

### HU-G01 — Registrar un AgroHub

**Como** administrador o investigador, **quiero** registrar un AgroHub con su número, familias, lugar,
asociaciones, grupo étnico, cultivos, coordenadas y video, **para** tener la ficha completa y verla
en el geovisor.

Criterios de aceptación:

1. `POST /agrohubs/` crea la ficha. Acepta `application/json` (sin video) o `multipart/form-data`
   con `data` (JSON como texto) y `video`.
2. Obligatorios: `numero`, `departamento`, `municipio`, `es_cabecera_municipal`, `latitud`,
   `longitud`, Opcionales: `nombre`, `familias` (puede ir vacía), datos de gestión (HU-G08), `grupo_etnico`, `comunidad` (solo con
   `grupo_etnico = indigena`; con otro grupo → `422` en `comunidad`), `asociaciones`, `cultivos`,
   `video`.
3. `numero` duplicado → `422` en el campo `numero`.
4. Si `es_cabecera_municipal = false`, `vereda` es obligatoria; si es `true`, `vereda` se ignora y
   se guarda vacía.
5. Las coordenadas se reciben **separadas** en `latitud` y `longitud` (nunca como un solo texto) y
   se validan por rango.
6. Registra `creado_por` desde el token.
7. Responde `201` con la ficha creada.

```json
{
  "numero": "AH-014",
  "familias": ["Familia Pérez Mejía", "Familia Torres"],
  "departamento": "Magdalena",
  "municipio": "Santa Marta",
  "es_cabecera_municipal": false,
  "vereda": "Guachaca",
  "asociaciones": ["Asociación de Productores de Guachaca"],
  "grupo_etnico": "indigena",
  "comunidad": "Kogui",
  "cultivos": ["Cacao", "Plátano"],
  "latitud": 11.268100,
  "longitud": -73.987200
}
```

### HU-G02 — Puntos para el geovisor

**Como** usuario del geovisor, **quiero** traer todas las coordenadas en una sola petición liviana,
**para** pintar todos los AgroHubs en el mapa sin cargar sus fichas completas.

Criterios de aceptación:

1. `GET /agrohubs/puntos` devuelve **solo** lo necesario para el marcador: `id`, `numero`,
   `latitud`, `longitud`, `municipio`, `departamento`, `nombre`, `tiene_dispositivo`.
2. **Sin paginación** (el mapa necesita todos) y sin listas ni video, para que pese poco.
3. Filtros opcionales por query: `?departamento=`, `?municipio=`, `?cultivo=`,
   `?grupo_etnico=` (para filtrar capas en el mapa).
4. Orden estable por `numero`.

```json
{ "status": 200, "message": "puntos",
  "data": [ { "id": 3, "numero": "AH-014", "nombre": "Guachaca Centro", "latitud": 11.2681, "longitud": -73.9872,
              "municipio": "Santa Marta", "departamento": "Magdalena" } ] }
```

### HU-G03 — Detalle de un AgroHub

**Como** usuario del geovisor, **quiero** abrir la ficha completa al tocar un punto, **para** ver
quién es, dónde está, qué cultiva y su video.

Criterios de aceptación:

1. `GET /agrohubs/<id>` devuelve todos los campos, las tres listas y la URL del video.
2. `lugar` se entrega compuesto y también desglosado para que el front elija cómo mostrarlo.
3. `video` es una URL relativa (`/api/agrohub/media/agrohubs/...`) o `null`.
4. `404` si no existe.

```json
{ "status": 200, "message": "agrohub",
  "data": {
    "id": 3, "numero": "AH-014", "nombre": "Guachaca Centro",
    "familias": ["Familia Pérez Mejía", "Familia Torres"],
    "lugar": { "departamento": "Magdalena", "municipio": "Santa Marta",
               "es_cabecera_municipal": false, "vereda": "Guachaca" },
    "asociaciones": ["Asociación de Productores de Guachaca"],
    "grupo_etnico": "indigena",
    "comunidad": "Kogui",
    "cultivos": ["Cacao", "Plátano"],
    "coordenadas": { "latitud": 11.2681, "longitud": -73.9872 },
    "video": "/api/agrohub/media/agrohubs/ah-014.mp4"
  } }
```

### HU-G04 — Editar y eliminar

**Como** administrador o investigador, **quiero** corregir o retirar un AgroHub, **para** mantener el registro al
día.

1. `PUT /agrohubs/<id>` es **parcial**: solo cambia lo que llegue.
2. Las listas (`familias`, `asociaciones`, `cultivos`) se **reemplazan completas** cuando se envían
   (el front manda la lista final).
3. Se mantienen las reglas de HU-G01 (vereda según cabecera, rangos, `numero` único).
4. Registra `editado_por`.
5. `DELETE` responde `204`, borra la ficha y su video del disco. El front pide confirmación.

### HU-G05 — Video (material audiovisual)

**Como** administrador o investigador, **quiero** adjuntar un video al AgroHub, **para** que quien vea el mapa
conozca el lugar y la iniciativa.

1. Un video por AgroHub. Formatos: `mp4`, `webm`, `mov`.
2. `POST /agrohubs/<id>/video` (multipart, campo `video`) sube o **reemplaza**; `DELETE` lo quita.
3. Se puede enviar también al crear (HU-G01).
4. El archivo se sirve por la ruta de media; el front lo reproduce con `<video src>`.
5. **Límite:** máximo **200 MB** (el back valida con `422` en `video`). nginx tiene 20 MB por
   defecto, así que en el nginx del servidor hay que agregar un `location ~ ^/agrohubs/` (o el
   prefijo `/api/agrohub/agrohubs/` que use allá) con `client_max_body_size 200M;` — ya está en
   `nginx/nginx.conf` del repo. Mostrar progreso de subida en el front.

### HU-G06 — Listados y catálogos para el formulario

1. `GET /agrohubs/` — tabla del admin, paginada (`?page=1&page_size=20`, máx. 100) con búsqueda
   `?q=` por número, nombre, familia, municipio, departamento o vereda. `data` = `{total, page, page_size,
   total_pages, results:[ficha]}`; cada ficha trae además `creado_por`, `creado_por_id`,
   `editado_por`, `created_at`, `updated_at`.
2. `GET /agrohubs/catalogos` (solo admin) — opciones para los desplegables: `grupos_etnicos`, y los
   `departamentos` (lista fija de Colombia). Los municipios se resuelven en el front (misma
   dependencia departamento → municipio que ya se usa en el resto de la app).
3. `asociaciones` y `cultivos` son **texto libre**; como ayuda, `catalogos.asociaciones` y
   `catalogos.cultivos` devuelven los ya usados para autocompletar (no obliga a escoger de ahí).
4. `catalogos.comunidades` devuelve las opciones de comunidad indígena.

---

### HU-G07 — Asociar un AgroHub a su dispositivo IoT y publicar sus datos

**Como** administrador o investigador, **quiero** indicar qué gateway de riego pertenece a cada
AgroHub, **para** que el geovisor muestre los datos ambientales de ese lugar y cualquiera pueda
consultarlos como datos abiertos.

Criterios de aceptación:

1. En el formulario del AgroHub hay un selector **Dispositivo IoT** (opcional). Sus opciones salen de
   `GET /agrohubs/dispositivos-disponibles` (`[{device_id, nombre}]`: gateways activos que aún no
   tienen AgroHub). El valor se envía como `dispositivo` en `POST /agrohubs/` o `PUT /agrohubs/<id>`.
2. Reglas: el dispositivo debe existir y estar activo (si no, `422` en `dispositivo`); un dispositivo
   solo puede estar en un AgroHub (`422` si ya está asociado a otro); `null` o vacío lo desasocia.
   Al editar, el propio AgroHub puede conservar el que ya tiene.
3. `GET /agrohubs/puntos` trae `tiene_dispositivo` (booleano) para que el mapa distinga los
   AgroHubs con sensores.
4. `GET /agrohubs/<id>` trae `dispositivo: {device_id, nombre}` o `null`.
5. **Datos abiertos:** `GET /agrohubs/<id>/datos` (sin token) devuelve la última lectura ambiental y
   de suelo del gateway asociado; `404` si el AgroHub no tiene dispositivo. Solo expone datos
   ambientales: **nunca** válvulas, configuración, salud ni credenciales del gateway.

```json
{ "status": 200, "message": "datos",
  "data": { "agrohub_id": 3, "numero": "AH-014", "ultima_lectura": "2026-10-11T21:17:54Z", "en_linea": true,
            "ambiente": { "medido_en": "...", "temperatura": 29.1, "humedad": 70.0 },
            "suelo": { "medido_en": "...", "humedad_suelo": 41.2, "temperatura_suelo": 27.5, "conductividad": 310 } } }
```

`en_linea` es `true` si hubo una lectura en los últimos 3 minutos. La relación es entre bases de datos
distintas (MySQL y la de `mqtt_agrohub`), por eso se valida al guardar y no con una llave foránea.

---

### HU-G08 — Datos de gestión del AgroHub (solo equipo)

**Como** administrador o investigador, **quiero** guardar la tipología, el responsable, su celular, el
tipo de fuente de agua y el punto de captación de cada AgroHub, **para** gestionar la red sin
exponer datos personales en el mapa público.

1. Campos opcionales en `POST /agrohubs/` y `PUT /agrohubs/<id>`: `tipologia` (Small/Medium/Large),
   `responsable`, `celular`, `tipo_fuente` (Pozo, Río, Punto de agua, Otro) y `punto_captacion`.
2. Se devuelven **solo con token** y rol admin/superadmin/investigador: en el listado `GET /agrohubs/`
   y en las respuestas de crear/editar.
3. **Nunca** aparecen en `GET /puntos`, `GET /<id>` ni `GET /<id>/datos` (públicos). El celular es un
   dato personal (Ley 1581): no debe pintarse en el geovisor.
4. Texto vacío se guarda como `null`.

### HU-G09 — AgroHub sin familias registradas

**Como** administrador, **quiero** registrar un AgroHub aunque todavía no tenga familias, **para**
poder publicar el punto en el mapa antes de levantar esa información.

1. `familias` es opcional; si no llega o va `[]`, la ficha se guarda con lista vacía.
2. El front debe mostrar "Sin familias registradas" (o esconder el bloque) cuando la lista viene vacía,
   igual que ya hace con `asociaciones` y `cultivos`.

---

## 4. Permisos y errores

- Crear, editar, eliminar y subir video: **admin, superadmin e investigador** (rol `investigador`, que se asigna con `PUT /user-activity/users/<id>/role`). Un `user` recibe `403`.
- Ver puntos y detalle: **públicos, sin autenticación** (el geovisor es abierto). Por eso el detalle
  público no expone datos de gestión: se omiten `creado_por`/`editado_por` y fechas de auditoría
  (solo salen en el listado de admin `GET /agrohubs/`). Los GET públicos solo leen; cualquier
  escritura exige token y rol.
- Errores igual que el resto de la API: `422` con `{"status":422,"errores":[{"campo","mensaje",...}]}`
  y `campo` con la ruta completa (`familias.0`, `vereda`, `latitud`).

## 5. Decisiones

Resueltas: `familias` = lista de nombres sin integrantes · `grupo_etnico` pide `comunidad` si es
indígena · `numero` = texto libre · `cultivos` y `asociaciones` = listas de texto libre.

Confirmadas también: **un solo video** por AgroHub · `puntos` y detalle **públicos** (sin token).

Sin decisiones pendientes.
