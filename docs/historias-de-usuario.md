# AgroHub Magdalena — Historias de usuario del backend

Cubre los 5 módulos Django del proyecto (`apps/data_characterization`, `apps/hub_cgsm`, `apps/encuesta_nutricional`, `apps/user_activity`, `apps/asistencia_eventos`). Cada historia referencia el endpoint real que la implementa.

## Cómo se divide App vs Web

- **Flujo APP** (captura de datos en campo, sin sesión iniciada en la mayoría de los casos): las encuestas de `data_characterization`, los formularios de actores/faenas de `hub_cgsm`, y el registro/consulta de encuestas de `encuesta_nutricional`.
- **Flujo WEB** (panel administrativo, siempre con `Authorization: Token`): gestión de usuarios y roles, asociaciones, bitácoras, los tres dashboards (nutricional, asistencia a eventos), el módulo de OCR de asistencia, y — según lo que confirmaste — el registro de **puntos de acopio** de `hub_cgsm` (aunque su endpoint vive físicamente en el mismo módulo que las encuestas de actores/faenas; si en realidad los puntos de acopio también se capturan desde la app en campo, avísame y lo reclasifico).
- **Compartido**: registro, login, logout y recuperación de contraseña — el mismo sistema de auth sirve para las dos superficies (ver `[[flujo-app-vs-web]]` en la conversación previa: un usuario puede tener token de app y de web activos a la vez).

---

## Flujo APP — Encuestas de campo

### `data_characterization` (sin autenticación, montado en la raíz)

**HU-A01 — Registrar encuesta Agrohub**
Como promotor de campo, quiero enviar los datos de caracterización de una organización agrohub (ubicación, actividad productiva, etc.) para que quede registrada en el sistema sin necesitar una cuenta.
- `POST /surveys/` (tipo `agrohub`)
- Criterios: valida campo por campo contra el serializer; errores 422 devuelven `campo`/`valor_recibido`/`tipo_error` por cada dato inválido.

**HU-A02 — Registrar encuesta educativa**
Como promotor de campo, quiero enviar la caracterización de una institución educativa rural para que quede en el sistema.
- `POST /surveys/` (tipo `educativa`)

**HU-A03 — Registrar encuesta de derecho humano al alimento**
Como promotor de campo, quiero registrar la encuesta de caracterización de hogares sobre derecho humano a la alimentación.
- `POST /surveys/` (tipo `derecho_humano_alimentario`)

**HU-A04 — Consultar encuestas guardadas**
Como miembro del equipo, quiero listar las encuestas ya registradas (de cualquiera de los tres tipos) para revisarlas o darles seguimiento.
- `GET /surveys/`

**HU-A05 — Editar una encuesta ya enviada**
Como promotor de campo, quiero corregir datos de una encuesta que ya envié (ej. un error de digitación) sin tener que crear un registro nuevo.
- `PUT /surveys/<id>`

**HU-A06 — Consultar ubicaciones registradas**
Como miembro del equipo, quiero obtener todas las ubicaciones (lat/long) de las encuestas registradas para poder ubicarlas en un mapa.
- `GET /surveys/locations/`

### `hub_cgsm` (sin autenticación, `/hub-cgsm/`)

**HU-A07 — Registrar un actor del HUB CGSM**
Como encuestador de campo, quiero registrar un actor (pescador, comercializador, etc. de la Ciénaga Grande) con su foto, su activo asociado y su foto del activo, para caracterizar quién participa en la cadena.
- `POST /hub-cgsm/survey/actors` (multipart: `fotografia_actor`, `fotografia_activo` obligatorias)
- Criterios: rechaza con 400 si falta cualquiera de las dos fotos.

**HU-A08 — Registrar una faena (actividad de pesca/recolección)**
Como encuestador de campo, quiero registrar una faena con su punto GPS inicial/final y fotos de antes/después, para dejar evidencia de la actividad productiva.
- `POST /hub-cgsm/survey/faena` (multipart: `fotografia_antes`, `fotografia_despues` obligatorias)

**HU-A09 — Registrar un punto de acopio de biomasa**
Como encuestador de campo (o desde el panel web, según confirmes), quiero registrar un punto de acopio con su ubicación georreferenciada y evidencia fotográfica.
- `POST /hub-cgsm/survey/punto-acopio` (multipart: `fotografia_georreferenciada` obligatoria)

**HU-A10 — Consultar y editar encuestas del HUB CGSM**
Como miembro del equipo, quiero listar y corregir los registros ya capturados del HUB CGSM.
- `GET /hub-cgsm/surveys/`, `PUT /hub-cgsm/surveys/<id>`

**HU-A11 — Endpoint heredado sin funcionalidad real**
Como integrador que aún llama al contrato viejo, necesito que `POST /hub-cgsm/surveys/` siga respondiendo 201 sin romper el cliente, aunque no persiste nada — es un stub heredado de la API FastAPI original, mantenido solo por compatibilidad. No construir nada nuevo sobre este endpoint.

### `encuesta_nutricional` (público excepto dashboards/export, `/encuesta-nutricional/`)

**HU-A12 — Registrar una encuesta nutricional (ELCSA) de un hogar**
Como encuestador de campo, quiero registrar la encuesta de seguridad alimentaria de un hogar (sección hogar, hábitos alimentarios, ELCSA) para caracterizar su situación nutricional.
- `POST /encuesta-nutricional/`

**HU-A13 — Agregar miembros del hogar con datos antropométricos**
Como encuestador de campo, quiero agregar cada integrante del hogar (con su cédula, edad, peso, talla, perímetro braquial) a una encuesta ya creada, para completar el diagnóstico nutricional del hogar.
- `POST /encuesta-nutricional/<numero_encuesta>/miembros`
- Criterios: cada miembro se vincula a una `PersonaNutricional` maestra por cédula — si la persona ya existe (apareció en otra encuesta antes), se actualiza en vez de duplicarse.

**HU-A14 — Consultar, editar o retirar un miembro**
Como encuestador, quiero corregir o dar de baja (soft-delete) un miembro que agregué por error.
- `GET/PUT/DELETE /encuesta-nutricional/<numero_encuesta>/miembros/<miembro_id>`

**HU-A15 — Consultar/editar/retirar una encuesta completa**
Como miembro del equipo, quiero consultar, corregir o dar de baja una encuesta nutricional completa.
- `GET/PUT/DELETE /encuesta-nutricional/<numero_encuesta>`

**HU-A16 — Listar encuestas nutricionales**
Como miembro del equipo, quiero ver todas las encuestas nutricionales registradas.
- `GET /encuesta-nutricional/`

**HU-A17 — Buscar una persona por cédula o id**
Como encuestador, quiero consultar si una persona ya tiene historial nutricional antes de registrarla de nuevo, para no duplicar su ficha.
- `GET /encuesta-nutricional/personas/<value>`

### `user_activity` — canal conversacional (parte del flujo app)

**HU-A18 — Registrar una bitácora conversando con un asistente**
Como usuario de campo, quiero contarle a un asistente (por chat o WhatsApp) qué actividad realicé en lenguaje natural, y que él mismo arme y guarde la bitácora, sin tener que llenar un formulario.
- `POST /user-activity/chat` (requiere sesión) y `POST /user-activity/whatsapp` (webhook de Meta Business API, mismo motor conversacional)
- Criterios: el asistente pide título/descripción/fecha/asociación si faltan, y solo emite el bloque `<BITACORA>` cuando tiene los 4 datos completos; confirma con un resumen legible.

---

## Flujo WEB — Panel administrativo

### Autenticación y sesión (`user_activity`, compartido con la app)

**HU-W01 — Registrarme como nuevo usuario**
Como persona nueva del equipo, quiero crear mi cuenta para poder loguearme después, aunque quede sin permisos hasta que un superadmin me asigne un rol.
- `POST /user-activity/users/register`

**HU-W02 — Iniciar sesión desde la app o desde la web con la misma cuenta**
Como usuario, quiero loguearme indicando si es desde la app o desde la web, y que ambas sesiones convivan sin que una cierre la otra.
- `POST /user-activity/users/login` (campo opcional `platform`: `"app"` / `"web"`)
- Criterios: un segundo login con el mismo `platform` reemplaza solo esa sesión; loguear en la otra plataforma no la afecta.

**HU-W03 — Cerrar sesión**
Como usuario, quiero cerrar mi sesión activa (de una sola plataforma) sin afectar la sesión que tengo abierta en la otra.
- `POST /user-activity/users/logout`

**HU-W04 — Recuperar contraseña olvidada por correo (OTP)**
Como usuario que olvidó su contraseña, quiero pedir un código de 6 dígitos a mi correo y usarlo para definir una contraseña nueva, sin necesitar sesión activa.
- `POST /user-activity/users/forgot-password`, `POST /user-activity/users/reset-password`
- Criterios: el código expira en 10 minutos, es de un solo uso, y al usarlo se cierran **todas** las sesiones activas del usuario (debe volver a loguearse en cada plataforma).

**HU-W05 — Bootstrap del primer superadmin**
Como quien despliega el servidor, quiero crear la primera cuenta superadmin usando un secreto de servidor (no una sesión de usuario), para poder arrancar el sistema de roles desde cero.
- `POST /user-activity/users/superadmin` (header `X-Superadmin-Token`)

### Gestión de usuarios y roles (`user_activity`, solo superadmin/admin)

**HU-W06 — Listar todos los usuarios**
Como superadmin, quiero ver todos los usuarios registrados para saber a quién le falta asignar un rol.
- `GET /user-activity/users`

**HU-W07 — Asignar un rol a un usuario**
Como superadmin, quiero asignarle un rol existente a un usuario para que deje de estar bloqueado y pueda usar los endpoints protegidos según su perfil.
- `PUT /user-activity/users/<user_id>/role`

**HU-W08 — Crear un usuario directamente desde el panel (sin que se autorregistre)**
Como admin, quiero dar de alta a un usuario yo mismo (ej. alguien sin acceso a internet en el momento) en vez de esperar a que se registre.
- `POST /user-activity/users/admin-create`

**HU-W09 — Consultar, editar o eliminar un usuario**
Como admin, quiero ver el detalle de un usuario, corregir sus datos, o eliminarlo si ya no debe tener acceso.
- `GET/PUT/DELETE /user-activity/users/<user_id>`

**HU-W10 — Administrar el catálogo de roles**
Como superadmin, quiero crear, listar, editar o eliminar roles (más allá de los tres sembrados: `user`, `admin`, `superadmin`) para representar perfiles de permisos específicos del equipo.
- `GET/POST /user-activity/roles`, `PUT/DELETE /user-activity/roles/<role_id>`
- Criterios: no se puede eliminar un rol que todavía tiene usuarios asignados.

### Asociaciones (`user_activity`)

**HU-W11 — Administrar asociaciones**
Como admin, quiero crear, listar, editar y eliminar las asociaciones (agrupaciones de productores/comunidades) a las que se vincula cada usuario y cada bitácora.
- `GET/POST /user-activity/associations`, `GET/PUT/DELETE /user-activity/associations/<id>`

### Bitácoras (`user_activity`)

**HU-W12 — Registrar mi bitácora de actividad desde el panel**
Como usuario con rol asignado, quiero registrar una bitácora (título, descripción, fecha, asociación) directamente por formulario, sin pasar por el asistente conversacional.
- `POST /user-activity/logbooks`

**HU-W13 — Consultar mis bitácoras (o las de otro usuario, si soy autorizado)**
Como usuario, quiero ver el historial de bitácoras filtrado por fecha o asociación, paginado.
- `GET /user-activity/logbooks/me`

**HU-W14 — Editar o eliminar una bitácora**
Como el usuario dueño de una bitácora, quiero corregirla o eliminarla si me equivoqué.
- `GET/PUT/DELETE /user-activity/logbooks/<logbook_id>`

### Dashboard nutricional (`encuesta_nutricional`, requiere token)

**HU-W15 — Ver el resumen por municipio**
Como usuario del panel, quiero ver cuántas encuestas nutricionales hay por municipio, para entender la cobertura del proyecto.
- `GET /encuesta-nutricional/dashboard/municipios` (público) y `GET /dashboard/municipios/<municipio>` (detalle, con token)

**HU-W16 — Ver el resumen por vereda**
Como usuario del panel, quiero ver la cobertura desagregada por vereda dentro de cada municipio.
- `GET /encuesta-nutricional/dashboard/veredas` (con token)

**HU-W17 — Exportar todas las encuestas nutricionales a Excel**
Como usuario del panel, quiero descargar un Excel con todas las encuestas activas, separadas en una hoja por municipio, para análisis externo o para reportar a los financiadores del proyecto.
- `GET /encuesta-nutricional/export/excel`

### Asistencia a eventos con OCR (`asistencia_eventos`, solo admin/superadmin)

**HU-W18 — Digitalizar una hoja de asistencia escaneada**
Como responsable de un evento, quiero subir la foto/PDF de la hoja de asistencia que se llenó a mano, y que el sistema me devuelva ya extraído el tema, responsable, lugar, fecha, horas y la lista de asistentes, para no tener que digitarlo todo desde cero.
- `POST /asistencia-eventos/scan`
- Criterios: no guarda nada todavía; marca qué asistentes ya existen en el sistema (`persona_ya_registrada`) para que se note un posible duplicado antes de confirmar.

**HU-W19 — Revisar, corregir y guardar el evento**
Como responsable de un evento, quiero corregir lo que el OCR haya leído mal (sobre todo nombres y las casillas de género/etnia) antes de que quede guardado en firme, para no ensuciar la base de datos con lecturas erróneas.
- `POST /asistencia-eventos/eventos` (multipart: `data` con el JSON corregido + `archivo` con el mismo PDF, guardado como evidencia)
- Criterios: cada asistente se guarda por *upsert* de número de documento — si la persona ya existe, se actualiza en vez de duplicarse; rechaza si dos filas de la misma carga comparten documento.

**HU-W20 — Consultar, editar o eliminar un evento**
Como usuario del panel, quiero ver la lista de eventos registrados y, de cada uno, el detalle completo de quién asistió; también corregir el encabezado (tema, responsable, lugar, fecha, horas) o eliminar el evento por completo si se cargó por error.
- `GET /asistencia-eventos/eventos`, `GET/PUT/DELETE /asistencia-eventos/eventos/<id>`
- Criterios: eliminar un evento borra en cascada sus registros de asistencia, pero **no** borra a las personas — siguen en el sistema para otros eventos.

**HU-W20b — Corregir o eliminar una persona**
Como usuario del panel, quiero corregir el nombre, tipo de documento, género, pertenencia étnica o comunidad (HU-W25) de una persona cuando el OCR (o quien digitó) se equivocó, o eliminarla del sistema si no debía existir.
- `GET/PUT/DELETE /asistencia-eventos/personas/<numero_documento>`
- Criterios: `GET` muestra también todos los eventos a los que asistió; eliminar una persona la borra en cascada de **todos** los eventos donde aparece — es la operación más amplia de las tres de este módulo, hay que usarla con cuidado.

**HU-W20c — Corregir o retirar a alguien de un evento puntual, sin tocar su ficha ni el resto del evento**
Como usuario del panel, quiero corregir el municipio/teléfono/edad con que quedó una persona en un evento específico, o retirarla de ese evento (porque en realidad no asistió, o se cargó dos veces), sin afectar su ficha maestra ni su historial en otros eventos.
- `PUT/DELETE /asistencia-eventos/eventos/<evento_id>/asistentes/<numero_documento>`

**HU-W21 — Ver el resumen general de asistencia**
Como usuario del panel, quiero ver de un vistazo cuántas personas únicas, cuántos eventos y cuántas asistencias totales hay registradas.
- `GET /asistencia-eventos/dashboard/resumen`

**HU-W22 — Ver estadísticas demográficas de asistencia**
Como usuario del panel, quiero ver cuántos asistentes hay por municipio, género y rango de edad (0-14 / 15-19 / 20-59 / mayor de 60), con totales, para reportar el alcance demográfico del proyecto.
- `GET /asistencia-eventos/dashboard/estadisticas` (opcional `?evento_id=` para un solo evento)

**HU-W23 — Descargar el dashboard completo en Excel**
Como usuario del panel, quiero descargar un solo archivo Excel con el resumen, las estadísticas, el listado de eventos y el detalle de asistentes, para compartirlo o analizarlo fuera del sistema.
- `GET /asistencia-eventos/dashboard/excel` (opcional `?evento_id=`)

**HU-W24 — Que el tipo de documento (CC / TI) venga prellenado**
Como usuario del panel, quiero que al digitalizar una hoja el sistema ya me proponga el tipo de documento de cada asistente, para no tener que escribirlo a mano en cada fila — solo revisar y corregir si hace falta.
- Aplica en `POST /asistencia-eventos/scan` (el borrador ya trae `tipo_documento` por asistente) y de nuevo al guardar (`POST /asistencia-eventos/eventos`, `POST /asistencia-eventos/scan-bulk`).
- **Regla, en este orden:**
  1. Si en la hoja el tipo venía escrito junto al número (`CC 1.081.806.419`, `T.I. 1004163795`; también CE, RC, PEP, PPT, PA), se respeta ese y el número queda solo con dígitos.
  2. Si no venía escrito pero hay edad: **18 o más → `CC`, menos de 18 → `TI`**.
  3. Sin tipo escrito ni edad: `null` (no se inventa).
- Criterios:
  - El front debe mostrar `tipo_documento` como un campo editable en la pantalla de revisión (el valor que llega es una propuesta, no un dato confirmado) y mandar en `POST /eventos` el valor final que dejó el usuario.
  - Si el usuario lo deja vacío, el backend vuelve a aplicar la regla de edad al guardar; no hace falta que el front la replique.
  - Un tipo inferido por edad **nunca pisa** uno que la persona ya tenía guardado de un evento anterior (p. ej. un CE corregido a mano).
  - Es una aproximación: un menor de 7 años tendría registro civil y un extranjero CE/PEP; el usuario lo corrige en la revisión o con `PUT /personas/<numero_documento>`.
- Ejemplo de borrador devuelto por `/scan` (fragmento):
  ```json
  {"nombre": "Laura Rojas", "numero_documento": "1004163795", "edad": 17, "tipo_documento": "TI", ...}
  ```

**HU-W25 — Registrar la comunidad cuando la persona es indígena**
Como usuario del panel, quiero que cuando marque a un asistente como indígena pueda escoger de qué comunidad es (y que ese campo no aparezca para el resto), para poder reportar el alcance del proyecto por pueblo indígena.
- Campo nuevo **`comunidad`** (texto, máx. 100, opcional), guardado en la **ficha de la persona** (igual que género y etnia), no en cada evento.
- `GET /asistencia-eventos/comunidades` (cualquier rol autenticado) → opciones sugeridas para el desplegable: `{"status":200,"message":"comunidades","data":["Arhuaco","Kogui","Wiwa","Kankuamo","Zenú","Wayuú","Chimila (Ette Ennaka)","Otra"]}`. *(Lista inicial sugerida, pendiente de confirmar con el equipo — se ajusta en `apps/asistencia_eventos/catalogos.py`.)*
- Se envía dentro de cada asistente en `POST /asistencia-eventos/eventos` y en `PUT /asistencia-eventos/personas/<numero_documento>`; se devuelve en el detalle del evento, el detalle/historial de la persona y la hoja "Asistentes" del Excel.
- **Lo que debe hacer el front (el desplegable vive en el front, el backend solo entrega las opciones y valida):**
  1. Mostrar el selector de comunidad **solo** cuando `pertenencia_etnica = "indigena"`; ocultarlo en cualquier otro caso.
  2. Cargar las opciones desde `GET /asistencia-eventos/comunidades`.
  3. Incluir la opción **"Otra"** con un campo de texto libre: el backend acepta cualquier texto, no solo los de la lista. Mandar el texto escrito en `comunidad`.
  4. Al cambiar la etnia a una que no sea indígena, vaciar y no enviar `comunidad`.
  5. El OCR **no** llena este campo: llega vacío y se escoge en la revisión.
- Criterios del backend:
  - `comunidad` es opcional; omitirlo o mandar `null`/`""` equivale a "sin comunidad".
  - Con una etnia distinta de `indigena`, mandar `comunidad` responde `422` (`campo: "asistentes.0.comunidad"` al guardar un evento, `campo: "comunidad"` en el `PUT` de la persona): "Solo aplica cuando pertenencia_etnica es 'indigena'".
  - Si a una persona con comunidad le cambian la etnia (por `PUT /personas/...`) a una que no es indígena, la comunidad guardada se **borra** automáticamente.
  - Si un asistente ya existente se vuelve a mandar en otro evento **sin** `comunidad`, la que ya tenía se **conserva** (omitir no borra; para borrarla hay que cambiar la etnia o mandar el `PUT` con `comunidad: null`).
  - Si el texto coincide con una opción sugerida sin importar mayúsculas o espacios (`" kogui "`), se guarda con la forma de la lista (`"Kogui"`); si no coincide, se guarda tal cual.
- Ejemplo (`POST /asistencia-eventos/eventos`, fragmento de `data`):
  ```json
  {"asistentes": [
    {"numero_documento": "1081806419", "nombre": "Jeannis Quintero", "edad": 17,
     "genero": "F", "pertenencia_etnica": "indigena", "comunidad": "Kogui"},
    {"numero_documento": "1067838582", "nombre": "Kathy Menao", "edad": 31,
     "genero": "F", "pertenencia_etnica": "raizal"}
  ]}
  ```
- Fuera de alcance por ahora: el dashboard de estadísticas (`HU-W22`) no desglosa por comunidad.

**HU-W26 — Documento provisional y alerta para asistentes sin cédula**
Como usuario del panel, quiero que si una persona asistió pero no tiene o no dio su documento, el sistema le asigne un número provisional y me avise con una alerta, para poder guardar el evento completo y actualizar el documento real después.
- Si `numero_documento` llega vacío, `null` o el OCR no lo lee, el backend genera un número **provisional único** `PROV-` + 10 caracteres (ej. `PROV-8A9EAF8711`) y fija `tipo_documento = "PROV"`.
- `numero_documento` deja de ser obligatorio en `POST /asistencia-eventos/scan`, `/eventos` y la carga múltiple. En `/scan` el número provisional ya viene asignado en el borrador para que se vea en la revisión.
- Cada asistente con número provisional devuelve **`alerta`**: `"Documento provisional: la persona no presentó cédula; pendiente de actualizar"` (en caso contrario `null`). Aparece en el borrador de `/scan`, el detalle del evento, y como columna **alerta** en la hoja "Asistentes" del Excel.
- Lo que debe hacer el front: mostrar un aviso (ej. etiqueta amarilla) en las filas con `alerta` y permitir corregir el documento real desde la ficha de la persona.
- Los documentos repetidos en una misma carga solo se validan entre números reales (los provisionales son siempre distintos).

**HU-W27 — Pertenencia étnica "ninguno" por defecto**
Como usuario del panel, quiero que cuando no se declare etnia aparezca "ninguno" y no un campo vacío, para que los reportes y las descargas no tengan huecos.
- Una persona **nueva** sin `pertenencia_etnica` se guarda como `"ninguno"`; una persona que ya existía **conserva** la etnia (y comunidad) que tenía si en el nuevo evento no se envía.
- Los listados, el detalle del evento y el Excel muestran `"ninguno"` cuando está vacía.

**HU-W28 — Municipio del asistente = lugar del evento si no se indica**
Como usuario del panel, quiero que si un asistente no trae municipio se use el lugar donde se hizo el evento, para que las estadísticas por municipio no pierdan asistentes en "Sin municipio".
- Se aplica al guardar, en el borrador de `/scan`, el detalle del evento, el Excel, las estadísticas por municipio (HU-W22) y el historial de eventos de una persona.
- Si el asistente sí trae municipio, siempre gana el suyo.

**HU-W29 — Tipo de documento siempre asignado**
Como usuario del panel, quiero que todo asistente quede con un tipo de documento, para no tener que completarlo a mano.
- Se respeta el tipo escrito en la hoja; si no hay, por edad (18+ → `CC`, menor → `TI`); si tampoco hay edad → `CC` por defecto (ajusta HU-W24, que antes lo dejaba vacío). Sin documento → `PROV` (HU-W26).

**HU-W30 — Digitalizar hojas de varias páginas sin que se caiga (escaneo en segundo plano)**
Como usuario del panel, quiero subir una hoja de asistencia de varias páginas y poder seguir viendo el avance mientras se procesa, para no quedarme con la pantalla colgada ni perder el trabajo cuando el archivo es largo.
- **Por qué existe:** con el motor LLM cada página tarda ~2-3 minutos y una petición HTTP aguanta máximo 5. Una hoja de 5 páginas (~43 asistentes) tarda 10-15 minutos, así que `POST /scan` no puede terminarla: el servidor cortaba la petición y el trabajo se perdía.
- **Flujo (3 pasos, el resto del flujo no cambia):**
  1. `POST /asistencia-eventos/scan-async` (multipart, campo `archivo`) → `202` al instante con el `job_id`.
  2. `GET /asistencia-eventos/scan-async/<job_id>` cada **5-10 s** hasta que `estado` sea `completo` o `error`.
  3. Con `estado = "completo"`, `data.resultado` trae **exactamente lo mismo que `data` de `POST /scan`** (tema, responsable, lugar, fecha, horas, `asistentes[]` con `alerta`, `persona_ya_registrada`, tipo de documento, etc.). Desde ahí se revisa y se guarda con `POST /eventos` igual que siempre (reenviando el mismo archivo como `archivo`).
- **Respuesta de ambos endpoints** (`data`):
  ```json
  {
    "job_id": "3f1c7c1e-8a4b-4f63-9a52-0d1b7f6a9c11",
    "estado": "procesando",
    "nombre_archivo": "Primera sesión Modelo de Negocio Algarro.pdf",
    "paginas_total": 5,
    "paginas_procesadas": 2,
    "creado_en": "...", "actualizado_en": "...", "completado_en": null,
    "error": null,
    "resultado": null,
    "parcial": { "tema": "...", "asistentes": [ ...los leídos hasta la página 2... ] }
  }
  ```
  - `estado`: `pendiente` → `procesando` → `completo` | `error`.
  - `paginas_procesadas / paginas_total` sirve para una barra de progreso real (se actualiza al terminar cada página).
  - `parcial` (solo mientras `procesando`): lo leído hasta la última página terminada, **sin** enriquecer (sin alertas ni `persona_ya_registrada`); sirve para ir mostrando filas, pero el dato definitivo es `resultado`.
  - `resultado` (solo con `completo`): el borrador final.
  - `error` (con `estado = "error"`): mensaje legible para mostrar al usuario.
- **Qué debe hacer el front:**
  - Usar `scan-async` para cualquier PDF (es seguro también con 1 página). Mostrar progreso con `paginas_procesadas`/`paginas_total` y dejar claro que tarda unos minutos por página.
  - Permitir que el usuario **salga de la pantalla** y vuelva: guardar el `job_id` (por ejemplo en `localStorage`) y retomar el `GET`.
  - Dejar de consultar cuando `estado` sea `completo` o `error`. Ante `error`, ofrecer "volver a subir".
- Criterios del backend:
  - `POST /scan` (síncrono) **sigue funcionando** para hojas de una página. Si el PDF tiene más de una página y el motor es el LLM, responde `400` con el mensaje "…usa POST /asistencia-eventos/scan-async…" en vez de dejar morir la petición.
  - Un escaneo solo lo ve quien lo subió (o un superadmin); otro usuario recibe `404`.
  - Solo se procesa **una página a la vez** en todo el servidor: si dos personas suben a la vez, la segunda espera su turno (cada una tarda lo mismo que sola, en vez de las dos el doble). El `estado` queda en `procesando` mientras espera.
  - Si el servicio se reinicia a mitad de un escaneo, el job queda `error` ("quedó sin avanzar más de 15 minutos") la próxima vez que se consulte; hay que volver a subir.
  - Los archivos del escaneo quedan guardados en el servidor (`media/asistencia_eventos/scans/`).
- Límite conocido: `POST /scan-bulk` (carga masiva sin revisión) sigue siendo síncrono, así que con el motor LLM solo aguanta 1-2 hojas de una página por petición.

---

## Historias transversales (no atadas a un único endpoint)

**HU-T01 — Errores de validación consistentes**
Como integrador de un frontend, quiero que cualquier error de validación (en cualquier módulo) me devuelva la misma forma `{"status":422,"message","total_errores","errores":[...]}` con el campo, el mensaje, el tipo de error y el valor recibido, para poder armar un manejo de errores genérico.

**HU-T02 — Bloqueo por rol antes de asignación**
Como sistema, quiero que ningún usuario recién registrado pueda usar un endpoint protegido hasta que un superadmin le asigne un rol explícitamente, para que el acceso siempre sea una decisión humana y no un descuido de configuración.
