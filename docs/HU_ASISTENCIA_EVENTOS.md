# Asistencia a eventos — historias de usuario para el front

Documento único para integrar el módulo **`asistencia_eventos`** (digitalizar hojas de asistencia
manuscritas con OCR, revisarlas, guardarlas y consultar el alcance demográfico). Los ids `HU-Wxx`
son los mismos de `historias-de-usuario.md`; acá están ordenados por el flujo de la pantalla y con
las reglas **vigentes** (donde una historia reemplaza a otra, se indica).

Detalle técnico/de infraestructura (motor de OCR, modelo, timeouts): `asistencia-eventos.md`.

## Índice

1. [Convenciones](#1-convenciones)
2. [Mapa del flujo y de endpoints](#2-mapa-del-flujo-y-de-endpoints)
3. [Digitalizar la hoja](#3-digitalizar-la-hoja) — HU-W18, HU-W30, HU-W32
4. [Revisar y guardar el evento](#4-revisar-y-guardar-el-evento) — HU-W19 y las reglas de cada campo (W24–W29)
5. [Consultar, corregir y eliminar](#5-consultar-corregir-y-eliminar) — HU-W20, W20b, W20c, W31
6. [Dashboard y Excel](#6-dashboard-y-excel) — HU-W21, W22, W23
7. [Límites conocidos y recomendaciones de UI](#7-límites-conocidos-y-recomendaciones-de-ui)
8. [Checklist de pruebas](#8-checklist-de-pruebas)

---

## 1. Convenciones

**Base URL:** `https://back.alunaia.co/api/agrohub` (todos los paths de abajo cuelgan de
`/asistencia-eventos/`).

**Autenticación.** `POST /user-activity/users/login` con
`{"phone_or_identification": "...", "password": "..."}` devuelve `data.token` y `data.role`.
Todas las llamadas llevan `Authorization: Token <token>`. Un usuario recién registrado **no tiene
rol** y recibe `403` hasta que un superadmin se lo asigne: si el escaneo "falla" para alguien
nuevo, casi seguro es esto.

**Quién puede qué.**

| Endpoint | `user` | `admin` | `superadmin` |
|---|---|---|---|
| Escanear, guardar, ver/editar/eliminar **eventos**, dashboard, Excel | sí, **solo lo suyo** | sí, **solo lo suyo** | sí, **todo** |
| Ficha de **persona** (`/personas/<documento>`) | no (`403`) | sí | sí |
| `GET /comunidades` | sí | sí | sí |

"Solo lo suyo" = los eventos que esa misma persona guardó (`registrado_por`). Un evento ajeno
responde `404`, igual que uno inexistente. El dashboard y el Excel también se acotan así.

**Respuestas.** Casi todas son `{"status": <int>, "message": "...", "data": ...}`. Los `DELETE`
responden `204` sin cuerpo.

**Errores.**

| Código | Forma | Cuándo |
|---|---|---|
| `401` | `{"detail": "..."}` | falta el token o es inválido |
| `403` | `{"detail": "..."}` | sin rol asignado, o un `user` entrando a `/personas` |
| `404` | `{"detail": "..."}` | evento/persona/escaneo inexistente o ajeno |
| `400` | `{"detail": "..."}` | falta el archivo, `data` no es JSON, PDF de varias páginas en `/scan` |
| `422` | `{"status":422,"message":"Datos inválidos en la solicitud","total_errores":N,"errores":[{"campo","mensaje","tipo_error","valor_recibido"}]}` | validación de campos |
| `503` | `{"detail": "..."}` | el servicio de OCR no responde |

En `422`, `campo` usa la ruta completa (ej. `asistentes.3.comunidad`): sirve para marcar la fila y
el input exactos.

**Fechas y horas — ojo.** El escaneo devuelve fecha y horas **tal como están escritas en la
hoja** (`"17-06-2026"`, `"28/08/2026"`, `"9:00am"`, `"8:30 am"`), no en ISO. `POST /eventos` solo
acepta **`YYYY-MM-DD`** y **`HH:MM`** (24 h). El front debe convertirlas al mostrarlas en los
inputs de revisión (formato colombiano día-mes-año) y mandar ISO al guardar. Si el texto no se
puede interpretar, dejar el input vacío para que lo escriba el usuario.

---

## 2. Mapa del flujo y de endpoints

```
 subir PDF/foto ──► POST /scan-async ──► (consultar) GET /scan-async/<job_id> ──► borrador
        │                                                                         │
        └─ una sola página: POST /scan (síncrono) ──────────────────────────────┤
                                                                                  ▼
                                                              pantalla de REVISIÓN (editable)
                                                                                  │
                                                       POST /eventos  (data + archivo)  → evento guardado
                                                                                  │
                          lista / detalle / corregir / eliminar  ·  dashboard  ·  Excel
```

| Acción | Método y path | Rol |
|---|---|---|
| Escanear (1 página) | `POST /scan` | cualquiera con rol |
| Escanear (cualquier PDF, en segundo plano) | `POST /scan-async` · `GET /scan-async/<job_id>` | cualquiera con rol |
| Carga masiva sin revisión | `POST /scan-bulk` | cualquiera con rol |
| Guardar evento | `POST /eventos` | cualquiera con rol |
| Listar eventos | `GET /eventos` | cualquiera con rol |
| Detalle / editar encabezado / eliminar | `GET` · `PUT` · `DELETE /eventos/<id>` | cualquiera con rol |
| Corregir o retirar a alguien de un evento | `PUT` · `DELETE /eventos/<id>/asistentes/<documento>` | cualquiera con rol |
| Ficha de persona | `GET` · `PUT` · `DELETE /personas/<documento>` | `admin`, `superadmin` |
| Opciones de comunidad | `GET /comunidades` | cualquiera con rol |
| Resumen / estadísticas / Excel | `GET /dashboard/resumen` · `/dashboard/estadisticas` · `/dashboard/excel` | cualquiera con rol |

---

## 3. Digitalizar la hoja

### HU-W18 — Digitalizar una hoja de una página

**Como** responsable de un evento, **quiero** subir la foto o el PDF de la hoja de asistencia
llenada a mano y recibir ya extraído el tema, responsable, lugar, fecha, horas y la lista de
asistentes, **para** no digitarlo todo desde cero.

- `POST /asistencia-eventos/scan` · `multipart/form-data` · campo **`archivo`** (PDF o imagen).
- **No guarda nada.** Devuelve un borrador para revisar.
- Tarda **~2 a 3 minutos por página**. Si el PDF tiene **más de una página** responde `400`
  indicando que se use `scan-async` (ver HU-W30). Recomendación: usar siempre `scan-async`.

Respuesta `200` — `data` es el borrador:

```json
{
  "status": 200,
  "message": "Documento escaneado — revisa y corrige antes de guardar",
  "data": {
    "tema": "Primera Sesión de Co creación del Modelo de Negocio",
    "responsable": "Co crecer Proyectos",
    "lugar": "Biblioteca Algarrobo",
    "fecha": "17-06-2026",
    "hora_inicio": "9:00am",
    "hora_final": "12:00pm",
    "asistentes": [
      {
        "nombre": "William Munoz",
        "numero_documento": "1081802196",
        "tipo_documento": "CC",
        "municipio": "Algarrobo",
        "telefono": "3007367905",
        "edad": 36,
        "genero": "M",
        "pertenencia_etnica": "ninguno",
        "persona_ya_registrada": false,
        "alerta": null
      }
    ],
    "texto_crudo_ocr": "{...}"
  }
}
```

Campos de cada asistente en el borrador: ver la tabla de la sección 4. Guardar `texto_crudo_ocr`
y reenviarlo tal cual al guardar (queda como respaldo para revisar lo que el OCR leyó).

`persona_ya_registrada: true` = ese documento ya existe en el sistema (posible duplicado o
persona que vuelve a asistir). Mostrar un indicador, no bloquear.

### HU-W30 — Escaneo en segundo plano (hojas de varias páginas)

**Como** usuario del panel, **quiero** subir una hoja de varias páginas y ver el avance mientras
se procesa, **para** no quedarme con la pantalla colgada ni perder el trabajo.

**Por qué existe:** una hoja de 5 páginas (~43 asistentes) tarda 10 a 15 minutos y una petición
HTTP aguanta máximo 5. Medido con una hoja real de 5 páginas: terminó en ~10.7 minutos y devolvió
44 filas.

**Flujo:**

1. `POST /asistencia-eventos/scan-async` (multipart, campo `archivo`) → **`202`** al instante.
2. `GET /asistencia-eventos/scan-async/<job_id>` cada **5 a 10 s**.
3. Cuando `estado = "completo"`, `data.resultado` es **idéntico a `data` de `POST /scan`**. Se
   revisa y se guarda con `POST /eventos` (reenviando el mismo archivo).

Respuesta de ambos (`data`):

```json
{
  "job_id": "919f93e9-be71-46ca-8231-891d581aec5c",
  "estado": "procesando",
  "nombre_archivo": "Primera sesión Modelo de Negocio Algarro.pdf",
  "paginas_total": 5,
  "paginas_procesadas": 2,
  "creado_en": "2026-10-08T14:22:37Z",
  "actualizado_en": "2026-10-08T14:26:10Z",
  "completado_en": null,
  "error": null,
  "resultado": null,
  "parcial": { "tema": "...", "lugar": "...", "asistentes": [ "...los leídos hasta la página 2..." ] }
}
```

| Campo | Significado |
|---|---|
| `estado` | `pendiente` → `procesando` → `completo` \| `error` |
| `paginas_procesadas` / `paginas_total` | barra de progreso real (avanza al terminar cada página) |
| `parcial` | solo en `procesando`: lo leído hasta ahora, **sin enriquecer** (sin `alerta`, `persona_ya_registrada` ni defaults). Sirve para ir mostrando filas; el dato definitivo es `resultado` |
| `resultado` | solo en `completo`: el borrador final |
| `error` | solo en `error`: mensaje legible para el usuario |

**Qué debe hacer el front:**

- Usar `scan-async` para **cualquier** PDF (también el de 1 página).
- Mostrar el progreso y avisar que tarda unos minutos por página.
- **Guardar el `job_id`** (por ejemplo en `localStorage`) para que el usuario pueda salir de la
  pantalla y volver a retomar el `GET`.
- Dejar de consultar con `completo` o `error`; ante `error`, ofrecer "volver a subir".
- No permitir editar el borrador mientras `estado` sea `procesando`.

**Reglas del backend:**

- Un escaneo solo lo ve quien lo subió (o un superadmin); otro usuario recibe `404`.
- Se procesa **una página a la vez en todo el servidor**: si dos personas suben a la vez, la
  segunda espera su turno y su `estado` sigue `procesando` (sin avance) hasta que le toque.
- Si el servicio se reinicia a mitad de un escaneo, el job pasa a `error` ("quedó sin avanzar más
  de 15 minutos…") la próxima vez que se consulte. Hay que volver a subir.

### HU-W32 — Carga masiva sin revisión (opcional)

**Como** usuario del panel, **quiero** subir varias hojas de una vez y que se guarden directamente,
**para** cargar rápido un lote cuando no es necesario revisar fila por fila.

- `POST /asistencia-eventos/scan-bulk` · multipart · campo **`archivos`** repetido (uno por archivo).
- **No hay paso de revisión**: se guarda lo que el OCR leyó, tal cual. Los errores de lectura
  (nombres, etnia, género) quedan guardados y se corrigen después con las ediciones de la
  sección 5. El front debe advertirlo antes de enviar.
- Cada archivo se procesa y guarda por separado; uno que falle no detiene a los demás.

```json
{
  "status": 200,
  "message": "2 de 3 documento(s) guardados",
  "data": [
    {"archivo": "hoja1.pdf", "status": "guardado", "evento_id": 5, "total_asistentes": 10},
    {"archivo": "hoja2.pdf", "status": "error", "detalle": "..."},
    {"archivo": "hoja3.pdf", "status": "guardado", "evento_id": 6, "total_asistentes": 8}
  ]
}
```

- **Límite:** es síncrono; con el motor actual solo aguanta **1 a 2 hojas de una página** por
  petición antes del tiempo máximo. Para hojas de varias páginas usar HU-W30 y guardar con
  revisión.

---

## 4. Revisar y guardar el evento

### HU-W19 — Revisar, corregir y guardar

**Como** responsable de un evento, **quiero** corregir lo que el OCR leyó mal antes de que quede
guardado en firme, **para** no ensuciar la base de datos con lecturas erróneas.

- `POST /asistencia-eventos/eventos` · `multipart/form-data` con dos campos:
  - **`data`**: el JSON ya corregido, **como texto** (`JSON.stringify(...)`).
  - **`archivo`**: el mismo PDF/imagen (queda guardado como evidencia).
- También acepta `application/json` puro, pero entonces no se guarda el archivo.

```js
const form = new FormData();
form.append('data', JSON.stringify(payload));
form.append('archivo', archivo);
await fetch(`${BASE}/asistencia-eventos/eventos`, {
  method: 'POST', headers: { Authorization: `Token ${token}` }, body: form,
});
```

`payload` (fechas y horas en **ISO**, ver sección 1):

```json
{
  "tema": "Primera Sesión de Co creación del Modelo de Negocio",
  "responsable": "Co crecer Proyectos",
  "lugar": "Biblioteca Algarrobo",
  "fecha": "2026-06-17",
  "hora_inicio": "09:00",
  "hora_final": "12:00",
  "texto_crudo_ocr": "{...tal cual vino del escaneo...}",
  "asistentes": [
    {
      "nombre": "Jeannis Quintero",
      "tipo_documento": "TI",
      "numero_documento": "1081806419",
      "municipio": "Algarrobo",
      "telefono": "3051035950",
      "edad": 17,
      "genero": "F",
      "pertenencia_etnica": "indigena",
      "comunidad": "Kogui"
    }
  ]
}
```

Respuesta `201`: `{"status":201,"message":"evento guardado","data":{"id":7,"total_asistentes":44}}`.

**Reglas al guardar:**

- Obligatorios: `tema` y **al menos un asistente**. Todo lo demás es opcional.
- Cada persona se guarda por **upsert de documento**: si ya existe, se actualizan sus datos en vez
  de duplicarla; una misma persona puede estar en muchos eventos con un solo registro.
- Dos filas de la misma carga con el mismo documento real → `422`
  ("Documentos repetidos en la misma carga: …").
- **Quién lo guardó** sale del token (ver HU-W31); no se manda.

### Campos de cada asistente (reglas vigentes)

| Campo | Tipo | Reglas |
|---|---|---|
| `nombre` | texto | opcional |
| `numero_documento` | texto | opcional. **Vacío → el backend asigna `PROV-XXXXXXXXXX`** (HU-W26). Se guarda solo con dígitos: puntos y espacios de miles se quitan (`1.081.806.419` → `1081806419`) |
| `tipo_documento` | texto | opcional; ver HU-W24/W29 abajo |
| `municipio` | texto | opcional; si falta se usa el **lugar del evento** (HU-W28) |
| `telefono` | texto | opcional |
| `edad` | entero | opcional |
| `genero` | `"F"` \| `"M"` \| `"O"` | opcional. También acepta `"Femenino"`, `"Masculino"`, `"Otro"`, `"mujer"`, `"hombre"` (y variantes en minúscula) y las normaliza |
| `pertenencia_etnica` | `"ninguno"` \| `"indigena"` \| `"afro"` \| `"rom"` \| `"raizal"` | opcional; vacío → `"ninguno"` (HU-W27) |
| `comunidad` | texto, máx. 100 | opcional; **solo si `pertenencia_etnica = "indigena"`** (HU-W25) |

Solo en las **respuestas** (no se envían): `persona_ya_registrada` (bool), `alerta` (texto o
`null`).

### HU-W24 + HU-W29 — Tipo de documento siempre asignado

**Como** usuario, **quiero** que cada asistente llegue con su tipo de documento ya propuesto,
**para** solo revisarlo. *(HU-W29 reemplaza la parte de W24 que lo dejaba vacío sin edad.)*

Regla, en este orden:

1. Si en la hoja venía escrito junto al número (`CC 1.081…`, `T.I. 100…`; también `CE`, `RC`,
   `PEP`, `PPT`, `PA`), se respeta y el número queda solo con dígitos.
2. Si no, por edad: **18 o más → `CC`, menos de 18 → `TI`**.
3. Sin tipo ni edad → **`CC`** por defecto.
4. Sin documento → **`PROV`** (HU-W26).

Front: mostrarlo como campo **editable** (es una propuesta). Si el usuario lo deja vacío, el
backend vuelve a aplicar la regla al guardar. Un tipo inferido **no pisa** uno que la persona ya
tenía guardado. Es aproximado: un menor de 7 años sería registro civil y un extranjero `CE`/`PEP`.

### HU-W25 — Comunidad indígena

**Como** usuario, **quiero** escoger de qué comunidad es una persona indígena, **para** reportar el
alcance por pueblo.

- Opciones del desplegable: `GET /asistencia-eventos/comunidades` →
  `{"status":200,"message":"comunidades","data":["Arhuaco","Kogui","Wiwa","Kankuamo","Zenú","Wayuú","Chimila (Ette Ennaka)","Otra"]}`.
  *(Lista inicial sugerida, pendiente de confirmar con el equipo.)*
- **El desplegable vive en el front.** El backend solo entrega las opciones y valida.

Lo que debe hacer el front:

1. Mostrar el selector **solo** cuando `pertenencia_etnica = "indigena"`.
2. Cargar las opciones desde `/comunidades`.
3. Incluir **"Otra"** con texto libre: el backend acepta cualquier texto; mandar el texto escrito.
4. Al cambiar la etnia a otra, **vaciar y no enviar** `comunidad`.
5. El OCR **no** llena este campo; se escoge en la revisión.

Reglas del backend:

- Con etnia distinta de `indigena`, mandar `comunidad` → `422`
  (`campo: "asistentes.N.comunidad"`): "Solo aplica cuando pertenencia_etnica es 'indigena'".
- Si a una persona le cambian la etnia a una no indígena (`PUT /personas/…`), su comunidad se
  **borra** sola.
- Reenviar a un asistente existente **sin** `comunidad` **no** la borra.
- Un texto que coincide con una opción sin importar mayúsculas (`" kogui "`) se guarda como `"Kogui"`.

### HU-W26 — Documento provisional y alerta

**Como** usuario, **quiero** poder guardar a alguien que asistió pero no dio su cédula, **para**
completar el evento y actualizar el documento después.

- Sin `numero_documento` → número provisional único `PROV-` + 10 caracteres (ej. `PROV-8A9EAF8711`)
  y `tipo_documento = "PROV"`. En `/scan` ya viene asignado en el borrador.
- Esas filas traen **`alerta`**: `"Documento provisional: la persona no presentó cédula; pendiente de actualizar"`
  (en las demás, `null`). Aparece en el borrador, el detalle del evento y la hoja "Asistentes" del Excel.
- Front: marcar visualmente las filas con `alerta` (ej. etiqueta amarilla) y permitir corregir el
  documento real desde la ficha de la persona.

### HU-W27 — Etnia "ninguno" por defecto

Sin etnia declarada se guarda y se muestra **`"ninguno"`**, nunca vacío. Una persona que ya existía
conserva la que tenía si el nuevo evento no la envía.

### HU-W28 — Municipio = lugar del evento si falta

Si un asistente no trae municipio se usa el **lugar del evento** (en el borrador, al guardar, en
el detalle, el Excel y las estadísticas). Si trae municipio, gana el suyo.

---

## 5. Consultar, corregir y eliminar

### HU-W20 — Lista, detalle, editar encabezado, eliminar evento

- `GET /asistencia-eventos/eventos` → lista, orden más reciente primero:

```json
{
  "status": 200, "message": "eventos",
  "data": [{
    "id": 6, "tema": "...", "responsable": "...", "lugar": "...", "fecha": "2026-09-18",
    "total_asistentes": 8,
    "registrado_por": "Alberto Mario Vargas Suárez",
    "registrado_por_id": 19,
    "registrado_por_correo": "alvargas89@hotmail.com",
    "editado_por": null
  }]
}
```

- `GET /asistencia-eventos/eventos/<id>` → detalle completo:

```json
{
  "status": 200, "message": "evento",
  "data": {
    "id": 6, "tema": "...", "responsable": "...", "lugar": "...", "fecha": "2026-09-18",
    "hora_inicio": "09:00:00", "hora_final": "12:00:00",
    "documento_escaneado": "/api/agrohub/media/asistencia_eventos/....pdf",
    "registrado_por": "...", "registrado_por_id": 19, "registrado_por_correo": "...",
    "editado_por": null, "actualizado_en": "...",
    "asistentes": [{
      "nombre": "...", "tipo_documento": "CC", "numero_documento": "...",
      "genero": "F", "pertenencia_etnica": "indigena", "comunidad": "Kogui",
      "municipio": "...", "telefono": "...", "edad": 17, "alerta": null
    }]
  }
}
```

  `documento_escaneado` es una ruta relativa al dominio: sirve para abrir el PDF/imagen original y
  contrastarlo con lo guardado (`https://back.alunaia.co` + la ruta).

- `PUT /asistencia-eventos/eventos/<id>` — **edición parcial del encabezado**: solo se aplican los
  campos que vengan (`tema`, `responsable`, `lugar`, `fecha`, `hora_inicio`, `hora_final`; fecha y
  horas en ISO). No toca la lista de asistentes. Registra quién editó.
- `DELETE /asistencia-eventos/eventos/<id>` → `204`. Borra el evento y su participación, pero **no
  borra a las personas** (siguen para otros eventos). Pedir confirmación.

### HU-W20c — Corregir o retirar a alguien de un evento puntual

- `PUT /asistencia-eventos/eventos/<evento_id>/asistentes/<numero_documento>` — parcial:
  `{"municipio": "...", "telefono": "...", "edad": 18}`. No toca la ficha de la persona ni otros
  eventos.
- `DELETE` el mismo path → `204`. Retira a esa persona **solo de ese evento**.
- `404` si la persona no está en ese evento.

### HU-W20b — Ficha de la persona (solo `admin` y `superadmin`)

- `GET /asistencia-eventos/personas/<numero_documento>` → ficha + historial de eventos:
  `{"tipo_documento","numero_documento","nombre","genero","pertenencia_etnica","comunidad","eventos":[...]}`.
- `PUT` — parcial: `{"nombre","tipo_documento","genero","pertenencia_etnica","comunidad"}`. Con
  etnia no indígena y `comunidad` → `422`; cambiar la etnia a no indígena borra la comunidad.
  Aplica a **todos** los eventos de esa persona (es la ficha compartida).
- `DELETE` → `204`. **La operación más amplia del módulo:** borra a la persona de **todos** los
  eventos donde aparece. Confirmación fuerte.
- Para un `user` estos tres responden `403`: ocultar la entrada a la ficha en ese rol.
- Si el documento es provisional (`PROV-…`), corregirlo al número real se hace por acá.

### HU-W31 — Saber quién cargó y quién editó cada evento

**Como** administrador, **quiero** ver qué usuario cargó cada hoja y quién la editó por última
vez, **para** hacer seguimiento y pedir correcciones a la persona correcta.

- Viene en la **lista** y el **detalle** de eventos: `registrado_por` (nombre), `registrado_por_id`,
  `registrado_por_correo`, `editado_por` (nombre).
- **El nombre no es único** (hay dos usuarios llamados "Ricardo Pupo"): identificar y agrupar por
  `registrado_por_id`, mostrar el correo en un tooltip o segunda línea.
- Pueden venir `null` (eventos antiguos; `editado_por` es `null` si nunca se editó).
- El front **no manda** `registrado_por`: se ignora, siempre sale del token.
- Un `superadmin` ve todos los eventos (la columna "cargado por" le sirve); `admin` y `user` ven
  solo los suyos, así que para ellos sería siempre su propio nombre: se puede ocultar.
- *(Pendiente de decisión: si el rol `admin` debe ver los eventos de todos.)*

---

## 6. Dashboard y Excel

Todo se acota igual que los eventos: un `superadmin` ve el sistema completo, los demás roles solo
lo que ellos cargaron.

### HU-W21 — Resumen general

`GET /asistencia-eventos/dashboard/resumen` →
`{"status":200,"message":"resumen","data":{"total_personas":18,"total_eventos":2,"total_asistencias":18}}`.
`total_personas` cuenta personas **distintas** (por documento).

### HU-W22 — Estadísticas demográficas

`GET /asistencia-eventos/dashboard/estadisticas` (opcional `?evento_id=<id>`) → tabla dinámica
municipio × género × rango de edad:

```json
{ "status": 200, "message": "estadisticas",
  "data": [
    { "municipio": "Algarrobo", "genero": "Masculino", "0-14": 1, "15-19": 2, "20-59": 9, "mayor de 60": 1, "total": 13 },
    { "municipio": "Algarrobo", "genero": "Femenino",  "0-14": 0, "15-19": 1, "20-59": 8, "mayor de 60": 3, "total": 12 },
    { "municipio": "Algarrobo", "genero": "Otro",      "0-14": 0, "15-19": 0, "20-59": 0, "mayor de 60": 0, "total": 0 },
    { "municipio": "Total", "genero": null, "0-14": 1, "15-19": 3, "20-59": 17, "mayor de 60": 4, "total": 25 }
  ] }
```

- Cada municipio trae tres filas (`Masculino`, `Femenino`, `Otro`); la **última fila** es el total
  general (`municipio: "Total"`, `genero: null`) — mostrarla destacada.
- Las claves de rango son textos con guion y espacio (`"0-14"`, `"mayor de 60"`): acceder por
  corchetes, no como propiedad.
- Una persona sin edad o sin género no entra en la tabla (no se puede ubicar en una celda).
- **No** desglosa por comunidad todavía.

### HU-W23 — Excel completo

`GET /asistencia-eventos/dashboard/excel` (opcional `?evento_id=`) devuelve un `.xlsx` binario con
cuatro hojas: **Resumen**, **Estadisticas**, **Eventos** (incluye `registrado_por`/`editado_por`)
y **Asistentes** (incluye `comunidad` y `alerta`).

Como lleva el header `Authorization`, **no se puede abrir con un enlace directo**: pedirlo con
`fetch`, convertir a `blob` y disparar la descarga desde el front:

```js
const r = await fetch(`${BASE}/asistencia-eventos/dashboard/excel`, { headers: { Authorization: `Token ${token}` } });
const url = URL.createObjectURL(await r.blob());
// <a href={url} download="dashboard_asistencia_eventos.xlsx">
```

---

## 7. Límites conocidos y recomendaciones de UI

**El OCR es un borrador, no un dato.** Leer manuscrito no es confiable. En una hoja real de 5
páginas (44 filas) se observó:

- **Etnia y género son los campos menos fiables**: el modelo tiende a repetir el mismo valor para
  casi toda la hoja en vez de leer la casilla marcada fila por fila (en esa hoja salieron 34
  indígenas, 9 afro y 1 rom, que no es creíble). **Mostrarlos siempre como editables y revisarlos
  fila por fila**; no usarlos para reportar sin revisión.
- Algunos números salen con dígitos de más o de menos (documentos de 10 dígitos en alguien de 72
  años, teléfonos de 8-9 dígitos) y algunos nombres salen aproximados.
- Puede haber **una fila de más o de menos**: contar contra la hoja física.
- El tipo de documento por edad es una propuesta.

**Recomendaciones:**

- Pantalla de revisión con el **documento original al lado** (usar `documento_escaneado` en la
  consulta, o el archivo local recién subido).
- Resaltar las filas con `alerta`, con `persona_ya_registrada: true`, y las que tengan campos
  vacíos o inusuales (documento sin 7-10 dígitos, edad vacía).
- Avisar claramente la duración: "unos 2 a 3 minutos por página".
- Antes de `POST /eventos`, validar en el front que `fecha` y horas estén en ISO.
- No enviar `comunidad` con etnia distinta de indígena.
- Manejar `403` ("sin rol") con un mensaje que diga que un superadmin debe asignarle un rol.

**Fuera de alcance por ahora:** estadísticas por comunidad, que el rol `admin` vea eventos de
otros usuarios, y reusar el archivo del escaneo en segundo plano al guardar (hoy hay que volver a
enviarlo en `POST /eventos`).

---

## 8. Checklist de pruebas

1. Login con un usuario **sin rol** → `403` al escanear; con rol → pasa.
2. `scan-async` con un PDF de 1 página → `202`, el `GET` llega a `completo` y `resultado` trae
   `asistentes`.
3. `scan-async` con un PDF de varias páginas → `paginas_total` correcto, `paginas_procesadas`
   avanza, aparece `parcial`, termina en `completo`.
4. `POST /scan` con un PDF de más de una página → `400` con el mensaje que apunta a `scan-async`.
5. Cerrar la pantalla durante el procesamiento y volver con el `job_id` guardado → se retoma.
6. Guardar con fecha `"17-06-2026"` → `422`; con `"2026-06-17"` → `201`.
7. Guardar un asistente sin documento → queda `PROV-…`, `tipo_documento = "PROV"` y trae `alerta`.
8. Guardar `pertenencia_etnica: "afro"` con `comunidad: "Kogui"` → `422` en `asistentes.N.comunidad`;
   con `"indigena"` → guarda.
9. Un asistente de 17 años sin tipo → `TI`; de 30 → `CC`; sin edad → `CC`.
10. Reenviar a una persona existente sin `comunidad` → la conserva.
11. Como `user`: `GET /personas/<doc>` → `403`; ver solo sus propios eventos; el evento de otro → `404`.
12. Como `superadmin`: ver todos los eventos con `registrado_por_id` y `registrado_por_correo`.
13. `DELETE` de un evento → `204` y las personas siguen existiendo.
14. `GET /dashboard/estadisticas` → la última fila es `Total`; la descarga del Excel funciona con
    `blob` y trae las 4 hojas.
