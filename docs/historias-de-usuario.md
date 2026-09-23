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
Como usuario del panel, quiero corregir el nombre, tipo de documento, género o pertenencia étnica de una persona cuando el OCR (o quien digitó) se equivocó, o eliminarla del sistema si no debía existir.
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

---

## Historias transversales (no atadas a un único endpoint)

**HU-T01 — Errores de validación consistentes**
Como integrador de un frontend, quiero que cualquier error de validación (en cualquier módulo) me devuelva la misma forma `{"status":422,"message","total_errores","errores":[...]}` con el campo, el mensaje, el tipo de error y el valor recibido, para poder armar un manejo de errores genérico.

**HU-T02 — Bloqueo por rol antes de asignación**
Como sistema, quiero que ningún usuario recién registrado pueda usar un endpoint protegido hasta que un superadmin le asigne un rol explícitamente, para que el acceso siempre sea una decisión humana y no un descuido de configuración.
