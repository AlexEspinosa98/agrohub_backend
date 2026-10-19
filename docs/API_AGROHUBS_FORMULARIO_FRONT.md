# Formulario de AgroHub (registro manual) — endpoints e historia para el front

El front ya tiene el formulario; esto es lo que necesita para **crear, editar y borrar un AgroHub a mano**.
Base: `https://back.alunaia.co/api/agrohub`. **Todo el formulario exige token** y uno de estos roles:
**`admin`, `superadmin` o `investigador`** (`user`, sin rol y `comunicaciones` reciben `403`; sin token, `401`).
Header: `Authorization: Token <token>` (el de `POST /user-activity/users/login`).

## HU-G08 — Registrar un AgroHub manualmente desde el formulario

**Roles:** admin, superadmin, investigador.
**Como** integrante del equipo, **quiero** llenar un formulario con los datos de un AgroHub y guardarlo, **para** que aparezca
en el geovisor sin depender de ninguna carga automática.

Criterios de aceptación:
1. Al abrir el formulario se cargan las opciones de los selectores (sección 1).
2. Campos **obligatorios**: `numero`, `departamento`, `municipio`, `es_cabecera_municipal`,
   `latitud` y `longitud`. Todo lo demás es opcional.
3. `vereda` se muestra y es **obligatoria solo si "¿Es cabecera municipal?" = No**; si es Sí, se oculta y no se envía.
4. `comunidad` se muestra solo si `grupo_etnico = indigena` (si se cambia a otro grupo, vaciarla).
5. `familias`, `asociaciones` y `cultivos` son **listas de texto libre** (chips o filas que se agregan y quitan).
6. `latitud` y `longitud` van **separadas**, como números (grados decimales; Colombia ≈ lat 1 a 12, long −79 a −67).
7. `dispositivo` (opcional) es un selector con los gateways IoT que aún no tienen AgroHub.
8. El video es opcional y se puede subir al crear o después.
9. Al guardar, el backend responde `201` con la ficha creada; si hay errores responde `422` y cada error trae el `campo`
   para marcarlo en el formulario.
10. Tras guardar, el nuevo AgroHub aparece en el mapa público (`GET /agrohubs/puntos`) de inmediato.

---

## 1. Opciones de los selectores (al abrir el formulario)

| Selector | Endpoint | Notas |
|---|---|---|
| Departamento, grupo étnico, comunidad, sugerencias de asociaciones y cultivos | `GET /agrohubs/catalogos` | |
| Dispositivo IoT | `GET /agrohubs/dispositivos-disponibles` | solo gateways activos sin AgroHub |
| Municipio | (en el front) | dependiente del departamento, igual que en el resto de la app |

`GET /agrohubs/catalogos` → 200:
```json
{ "status": 200, "message": "catalogos",
  "data": {
    "departamentos": ["Amazonas", "Antioquia", "Arauca", "… 33 en total, incluye Magdalena …"],
    "grupos_etnicos": ["ninguno", "indigena", "afro", "rom", "raizal"],
    "comunidades": ["Arhuaco", "Kogui", "Wiwa", "Kankuamo", "Zenú", "Wayuú", "Chimila (Ette Ennaka)", "Otra"],
    "asociaciones": ["Asociación de Productores de Guachaca"],
    "cultivos": ["Cacao", "Plátano"] } }
```
- `asociaciones` y `cultivos` son los **ya usados** en otros AgroHubs: sirven para autocompletar, pero se puede escribir cualquier texto.
- `comunidades`: con **"Otra"** el usuario escribe el nombre libremente y se envía ese texto.

`GET /agrohubs/dispositivos-disponibles` → 200:
```json
{
  "status": 200,
  "message": "dispositivos disponibles",
  "data": [
    {
      "device_id": "device0014",
      "nombre": "KIT 14 Loma del Bálsamo"
    },
    {
      "device_id": "device0001",
      "nombre": null
    },
    {
      "device_id": "device0002",
      "nombre": null
    }
  ]
}
```
`nombre` puede ser `null` (hoy los 16 gateways no tienen nombre): mostrar entonces solo el `device_id`.

## 2. Crear — `POST /agrohubs/`

Dos formas (elige una):

**a) JSON (sin video):** `Content-Type: application/json`
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
  "latitud": 11.2681,
  "longitud": -73.9872,
  "dispositivo": "device0014"
}
```

**b) Con video:** `multipart/form-data` con el campo **`data`** (el mismo JSON, **como texto**) y el campo **`video`** (archivo):
```js
const form = new FormData();
form.append('data', JSON.stringify(payload));
form.append('video', archivoVideo);            // .mp4 .webm .mov, máx. 200 MB
const r = await fetch(`${BASE}/agrohubs/`, {
  method: 'POST', headers: { Authorization: `Token ${token}` }, body: form,   // NO pongas Content-Type: lo arma el navegador
});
```

Respuesta `201`:
```json
{
  "status": 201,
  "message": "agrohub creado",
  "data": {
    "id": 1,
    "numero": "AH-014",
    "familias": [
      "Familia Pérez Mejía",
      "Familia Torres"
    ],
    "lugar": {
      "departamento": "Magdalena",
      "municipio": "Santa Marta",
      "es_cabecera_municipal": false,
      "vereda": "Guachaca"
    },
    "asociaciones": [
      "Asociación de Productores de Guachaca"
    ],
    "grupo_etnico": "indigena",
    "comunidad": "Kogui",
    "cultivos": [
      "Cacao",
      "Plátano"
    ],
    "coordenadas": {
      "latitud": 11.2681,
      "longitud": -73.9872
    },
    "video": null,
    "dispositivo": {
      "device_id": "device0014",
      "nombre": "KIT 14 Loma del Bálsamo"
    },
    "creado_por": "Equipo",
    "creado_por_id": 1,
    "editado_por": null,
    "created_at": "2026-10-14T15:31:21.558360Z",
    "updated_at": "2026-10-14T15:31:21.558368Z"
  }
}
```
(la ficha creada incluye `creado_por`, `created_at`, etc. porque quien guarda es del equipo.)

### Campos

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `numero` | texto (máx. 50) | sí | **único** (sin importar mayúsculas), ej. `AH-014` |
| `nombre` | texto (máx. 150) | no | nombre público del punto, ej. `Algarrobo Cabecera` |
| `familias` | lista de textos | no | puede ir vacía (AgroHub sin familias registradas) |
| `departamento` | texto | sí | |
| `municipio` | texto | sí | |
| `es_cabecera_municipal` | booleano | sí | |
| `vereda` | texto | solo si **no** es cabecera | si es cabecera se ignora y queda `null` |
| `asociaciones` | lista de textos | no | |
| `grupo_etnico` | `ninguno` \| `indigena` \| `afro` \| `rom` \| `raizal` \| `null` | no | |
| `comunidad` | texto (máx. 100) | no | solo con `grupo_etnico = indigena` |
| `cultivos` | lista de textos | no | |
| `latitud` | número | sí | −90 a 90 (hasta 6 decimales) |
| `longitud` | número | sí | −180 a 180 (hasta 6 decimales) |
| `dispositivo` | texto (`device_id`) | no | gateway activo y libre; `null`/vacío = sin dispositivo |
| `tipologia` | texto (máx. 50) | no | **solo gestión**: ej. `Small` |
| `responsable` | texto (máx. 200) | no | **solo gestión** |
| `celular` | texto (máx. 30) | no | **solo gestión** |
| `tipo_fuente` | texto (máx. 100) | no | **solo gestión**: ej. `Pozo` |
| `punto_captacion` | texto (máx. 150) | no | **solo gestión** |

Los campos "solo gestión" (`tipologia`, `responsable`, `celular`, `tipo_fuente`, `punto_captacion`) se devuelven únicamente
a admin/superadmin/investigador (listado y respuestas de crear/editar). **Nunca** salen en `puntos`, en el detalle público ni en `datos`.

### Errores del formulario — `422`

Forma: `{"status":422,"message":"Datos inválidos en la solicitud","total_errores":N,"errores":[{"campo","mensaje","tipo_error","valor_recibido"}]}`.
Usa `errores[].campo` para marcar el input y `mensaje` (ya está en español) para mostrarlo. Con varios errores llegan todos juntos.

| Situación | `campo` | `mensaje` |
|---|---|---|
| `numero` repetido | `numero` | Ya existe un AgroHub con el número 'AH-014'. |
| No es cabecera y falta la vereda | `vereda` | La vereda es obligatoria cuando no es cabecera municipal. |
| Comunidad con un grupo que no es indígena | `comunidad` | Solo aplica cuando grupo_etnico es 'indigena'. |
| Latitud o longitud fuera de rango | `latitud` / `longitud` | Asegúrese de que este valor es menor o igual a 90. |
| Dispositivo que no existe | `dispositivo` | No existe un dispositivo activo con id 'device9999'. |
| Dispositivo ya usado por otro AgroHub | `dispositivo` | El dispositivo 'device0014' ya está asociado al AgroHub 'AH-014'. |
| Falta un obligatorio | el campo | Este campo es requerido. |

Ejemplo (varios errores a la vez):
```json
{
  "status": 422,
  "message": "Datos inválidos en la solicitud",
  "total_errores": 2,
  "errores": [
    {
      "campo": "latitud",
      "mensaje": "Asegúrese de que este valor es menor o igual a 90.",
      "tipo_error": "max_value",
      "valor_recibido": 95
    },
    {
      "campo": "longitud",
      "mensaje": "Asegúrese de que este valor es mayor o igual a -180.",
      "tipo_error": "min_value",
      "valor_recibido": -200
    }
  ]
}
```

Otros códigos: `401` sin token (`{"detail":"Falta header Authorization: Token <token>"}`) · `403` rol no permitido
(`{"detail":"Requiere rol admin o investigador"}`).

## 3. Editar — `PUT /agrohubs/<id>`

**Parcial:** manda solo lo que cambió. Las listas (`familias`, `asociaciones`, `cultivos`) se **reemplazan completas** (manda la lista final).
Mismas reglas que al crear (vereda, comunidad, número único, dispositivo). `"dispositivo": null` lo desasocia.
Cambiar `es_cabecera_municipal` a `true` borra la vereda; cambiar `grupo_etnico` a uno no indígena borra la comunidad.

```json
{ "municipio": "Ciénaga", "cultivos": ["Cacao", "Plátano", "Yuca"] }
```
→ `200` `{"status":200,"message":"agrohub actualizado","data":{ …ficha completa… }}` · `404` si no existe.

## 4. Video

- `POST /agrohubs/<id>/video` (multipart, campo `video`) sube o **reemplaza** (borra el anterior) → `200`:
  `{"status": 200, "message": "video guardado", "data": {"id": 1, "video": "/api/agrohub/media/agrohubs/7cf87665-a7b1-4724-953d-3592594f01ea_finca.mp4"}}`
- `DELETE /agrohubs/<id>/video` → `204`.
- Formatos `.mp4 .webm .mov`, máx. **200 MB** (`422` en `video` si no cumple). Mostrar barra de progreso de subida.

## 5. Eliminar — `DELETE /agrohubs/<id>`

`204` sin cuerpo; borra la ficha y su video. Pedir confirmación en el front. `404` si no existe.

## 6. Listado del panel — `GET /agrohubs/?page=1&page_size=20&q=`

Con token. Tabla del equipo, paginada (`page_size` máx. 100) y con búsqueda `q` por número, familia, municipio, departamento o vereda.
`{"status":200,"message":"agrohubs","data":{"total","page","page_size","total_pages","results":[ficha completa + creado_por, editado_por, created_at, updated_at]}}`.
Funciona con o sin barra final (`/agrohubs` y `/agrohubs/`).

## 7. Checklist del front

1. Mostrar el formulario solo si el rol del usuario es `admin`, `superadmin` o `investigador`.
2. Cargar `catalogos` y `dispositivos-disponibles` al abrirlo.
3. Reglas condicionales: vereda ↔ cabecera, comunidad ↔ indígena.
4. Si hay video: enviar `multipart` con `data` + `video`; si no, JSON.
5. Marcar cada error 422 en su input con `errores[].campo`.
6. Tras guardar, refrescar la tabla y, si hay mapa, `GET /agrohubs/puntos`.
