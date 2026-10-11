# Mapa de módulos de `agrohub_backend`

Insumo para definir roles y permisos (ver `PLAN_UNIFICACION_IDENTIDAD.md`). Generado leyendo las
rutas reales del código y los conteos de la base de producción (11 oct 2026).

Base: Django + DRF · MySQL `agrohub_v2` (+ Postgres `agrohub_mqtt` solo para riego) · `/api/agrohub/`.
Auth: `Authorization: Token <token>` (tabla `Session`). Roles hoy: `user`, `admin`, `superadmin`.

## 1. Resumen: 8 módulos

| # | Módulo (app) | Qué hace | Datos en producción | Acceso hoy |
|---|---|---|---|---|
| 1 | `user_activity` | usuarios, login, roles, asociaciones, bitácoras, chat IA, WhatsApp | 16 usuarios, 25 sesiones, 3 roles, 1 asociación, 7 bitácoras | mixto (ver 2.1) |
| 2 | `data_characterization` | encuestas de caracterización (agrohub, educativa, derecho a la alimentación) | 0 | **público** |
| 3 | `hub_cgsm` | actores, faenas, puntos de acopio y monitoreo ambiental de la CGSM | 0 | **público** |
| 4 | `encuesta_nutricional` | encuestas nutricionales (ELCSA) con miembros del hogar | 410 personas · 162 encuestas · 445 miembros | casi todo **público** |
| 5 | `asistencia_eventos` | digitalizar hojas de asistencia con OCR, eventos, dashboard | 208 personas · 18 eventos · 235 asistencias · 32 escaneos | cualquier rol con sesión |
| 6 | `agrohubs` | fichas de AgroHubs para el geovisor (coordenadas, familias, video) | 0 | lectura **pública**, escritura admin |
| 7 | `riego_iot` | gateways de riego y lecturas (lee la BD de `mqtt_agrohub`) | 16 dispositivos · ~4.8 mil lecturas de suelo y ambiente | admin, superadmin e investigador |
| 8 | `cartillas` | biblioteca pública de cartillas en PDF con índice y búsqueda (ver `HU_CARTILLAS.md`) | 0 al crearse | lectura **pública**; escritura admin, superadmin, investigador y comunicaciones |

Servicios de apoyo en el servidor: `agrohub-ocr-llm` (modelo de visión local para el OCR de
asistencia). Otros sistemas fuera de este backend: `mqtt_agrohub` (ingesta MQTT/IoT) y el AgroHub
de red social (`/api/agrohub-rs/`).

## 2. Detalle por módulo

### 2.1 `user_activity` — `/user-activity/`
| Endpoint | Quién entra |
|---|---|
| `POST users/register` | público (nace con rol `user`) |
| `POST users/login`, `forgot-password`, `reset-password` | público |
| `POST users/logout` | sesión |
| `POST users/superadmin` | solo con el token secreto del servidor (crear el primer superadmin) |
| `POST users/admin-create` | admin |
| `GET users` | superadmin |
| `GET users/<id>` | **público** (devuelve los datos públicos del usuario) |
| `PUT users/<id>` | admin |
| `PUT users/<id>/role` | superadmin |
| `GET/POST roles`, `PUT/DELETE roles/<id>` | superadmin |
| `GET associations`, `GET/PUT associations/<id>` | lectura pública; `POST`/edición admin |
| `POST/GET/PUT/DELETE logbooks…`, `GET logbooks/me` | cualquier rol; cada quien ve las suyas |
| `POST chat` | cualquier rol (asistente Gemini que puede crear una bitácora) |
| `GET/POST whatsapp` | público (webhook de Meta) |

Modelos: `User`, `Session`, `Role`, `Association`, `Logbook`, `Conversation`.

### 2.2 `data_characterization` — raíz `/`
`surveys/` (POST/GET), `surveys/<id>` (PUT), `surveys/locations/` (GET). Tres encuestas:
`EncuestaAgrohub`, `EncuestaEducativa`, `EncuestaDerechoHumanoAlimentario`. **Sin autenticación.**

### 2.3 `hub_cgsm` — `/hub-cgsm/`
`survey/actors`, `survey/faena`, `survey/punto-acopio` (POST), `surveys/` (POST/GET),
`surveys/<id>` (PUT). Modelos: `EncuestaActor`, `EncuestaFaena`, `PuntoAcopioBiomasa`,
`MonitoreoAmbiental`. **Sin autenticación.**

### 2.4 `encuesta_nutricional` — `/encuesta-nutricional/`
| Endpoint | Quién entra |
|---|---|
| `POST /`, `GET /`, `GET/PUT/DELETE /<numero_encuesta>` | **público** |
| `POST /<n>/miembros`, `GET/PUT/DELETE …/miembros/<id>` | **público** |
| `GET personas/<cédula>`, `PUT personas/<cédula>` | **público** |
| `GET dashboard/municipios` | **público** |
| `GET dashboard/municipios/<municipio>`, `dashboard/veredas`, `export/excel` | cualquier rol con sesión |

Modelos: `PersonaNutricional` (ficha maestra por cédula), `EncuestaNutricional`, `Miembro`.

### 2.5 `asistencia_eventos` — `/asistencia-eventos/`
| Endpoint | Quién entra |
|---|---|
| `scan`, `scan-async` (+ consulta), `scan-bulk` | cualquier rol |
| `eventos` (lista/crear), `eventos/<id>`, `eventos/<id>/asistentes/<doc>` | cualquier rol, **solo lo propio**; superadmin ve todo |
| `comunidades`, `dashboard/resumen`, `dashboard/estadisticas`, `dashboard/excel` | cualquier rol, acotado igual |
| `personas/<doc>` (ficha maestra) | solo admin |

Modelos: `PersonaAsistente`, `Evento`, `RegistroAsistencia`, `ScanJob`. Contrato completo:
`HU_ASISTENCIA_EVENTOS.md`.

### 2.6 `agrohubs` — `/agrohubs/`
| Endpoint | Quién entra |
|---|---|
| `GET puntos`, `GET <id>` | **público** (geovisor) |
| `GET/POST /`, `PUT/DELETE <id>`, `POST/DELETE <id>/video`, `GET catalogos` | admin |

Modelo: `AgroHub`. Contrato: `HU_AGROHUBS_GEOVISOR.md`.

### 2.7 `riego_iot` — `/riego-iot/`
`dispositivos/` (CRUD + `rotar-password`), `dashboard/resumen/`, `dashboard/<device_id>/` y sus
lecturas (`ambiente`, `suelo`, `valvulas`, `conexion`, `health`). **Solo admin, superadmin e investigador.** Los modelos son de
solo lectura sobre tablas que escribe el daemon de `mqtt_agrohub` (otra base de datos).

## 3. Matriz de acceso actual

| Módulo | Público | `user` | `admin` | `superadmin` |
|---|---|---|---|---|
| user_activity | registro, login, ver asociaciones, ver datos públicos de un usuario, WhatsApp | bitácoras propias, chat | + crear/editar usuarios, crear asociaciones | + roles, listar usuarios |
| data_characterization | todo | — | — | — |
| hub_cgsm | todo | — | — | — |
| encuesta_nutricional | casi todo | + dashboard por municipio/vereda y Excel | igual | igual |
| asistencia_eventos | nada | sus eventos y dashboard | sus eventos + fichas de personas | todos los eventos |
| agrohubs | puntos y detalle | igual | + administrar | igual |
| riego_iot | nada | nada | todo (+ investigador) | todo (+ investigador) |

## 4. Lo que salta a la vista para definir roles

1. **Datos personales sin autenticación.** `encuesta_nutricional` (410 personas con cédula y datos de
   salud) se puede leer, crear, editar **y borrar** sin sesión; `data_characterization` y
   `hub_cgsm` también. Al definir roles hay que decidir cuáles de estas rutas quedan abiertas
   (captura en campo desde la app) y cuáles exigen sesión.
1b. **`GET /user-activity/users/<id>` es público** y devuelve nombre, teléfono, cédula, correo y rol de
   cualquier usuario; como los ids son consecutivos, se puede recorrer toda la lista de usuarios sin
   iniciar sesión.
2. **Dos módulos con un solo nivel de "admin"**: `riego_iot` (todo o nada) y `agrohubs`. Son los
   candidatos naturales a "admin de módulo".
3. **`asistencia_eventos` ya es por dueño** (cada quien ve lo suyo): encaja con los roles de líder y
   miembro y con "admin de módulo" sin rediseñar.
4. **Bitácoras, chat y WhatsApp** dependen de un usuario individual, no de un rol especial.
5. **`encuesta_nutricional` no guarda quién la registró**, ni `data_characterization` ni
   `hub_cgsm`: sin ese dato no se puede acotar por dueño ni por AgroHub más adelante.
6. Hay una sola asociación registrada (`Loma del balsamo`) y los usuarios la referencian de forma
   opcional.
