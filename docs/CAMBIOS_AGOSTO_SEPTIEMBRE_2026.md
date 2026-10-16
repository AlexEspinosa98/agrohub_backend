# Registro de cambios — agosto y septiembre de 2026

Qué se hizo en el backend de AgroHub durante agosto y septiembre de 2026, y en qué commit quedó. Salió de `git log --since=2026-08-01 --until=2026-10-01`, de los archivos que toca cada commit y de los cambios hechos directamente en el servidor, que no pasaron por git (sección 3).

- **`agrohub_backend`** (este repo, rama `main`): 27 commits, 5 en agosto y 22 en septiembre.
- **`mqtt_agrohub`** (broker y demonio MQTT): 17 commits, sección 5.
- El rango termina el 30/09. En octubre ya hay commits nuevos, por ejemplo `b026be4` (enlace Energesis en `riego_iot`), que no están aquí.
- Los commits aparecen con dos identidades de git, `AlexEspinosa` y `Alex Espinosa`. Es la misma cuenta.

---

## 1. Hitos

### 1.1 Migración de FastAPI a Django (1–3 de agosto)
Se reemplazó el backend FastAPI por un proyecto Django + DRF con cuatro apps: `data_characterization`, `hub_cgsm`, `encuesta_nutricional` y `user_activity`. Se agregaron Docker, `docker-compose`, nginx, `CLAUDE.md` y los docs de roles, recuperación de contraseña y dashboard. Se borró el código FastAPI.
Commits: `37a1800`, `2480848`, `e1a3559`.

### 1.2 Gateways de riego (`apps.riego_iot`)
- **30/08:** la API de administración de gateways, que antes era un servicio FastAPI aparte en `mqtt_agrohub`, se incorporó a Django (`f3ebcec`) con su referencia de API (`da72693`). Sus tablas viven en Postgres (`agrohub_mqtt`) y se acceden con `managed=False` y un router de base de datos. El demonio MQTT sigue siendo un proceso separado.
- **16/09:** se completó el dashboard con históricos de válvulas, health y conexión, y edición del nombre del dispositivo (`e3d34a0`). Se documentaron las historias de usuario HU-01 a HU-11 (`6094852`).
- **16/09:** la autenticación pasó de un `X-API-Key` compartido a token de sesión con rol admin (`f86ab4a`). Antes se había registrado el `X-API-Key` como esquema de seguridad en Swagger (`62aa7c8`), y `f86ab4a` lo reemplazó.

### 1.3 Documentación OpenAPI (4 de septiembre)
Swagger con `drf-spectacular` para los 42 endpoints de las 5 apps (`7d5e771`), más el arreglo del crash de la interfaz fijando `swagger-ui-dist@5.17.14` (`98b1381`).

### 1.4 Asistencia a eventos con OCR (`apps.asistencia_eventos`)
- **06/09:** nace la app (`e99cf64`). El flujo es de dos pasos: `POST /scan` devuelve un borrador y `POST /eventos` guarda lo corregido. Incluye dashboard y exportación a Excel.
- **08/09:** se corrigen los dos problemas que impedían que el OCR corriera en producción: las librerías del sistema que faltaban para OpenCV (`f829737`) y el bug de oneDNN de PaddlePaddle (`2328ca5`).
- **08/09:** se agrega un motor alternativo con un modelo de visión local, Qwen2.5-VL vía `llama.cpp` (`a0167fe`), con dos ajustes posteriores a su esquema JSON (`163bd11`, `df83944`).
- **15/09:** `POST /scan-bulk` sube y guarda varios documentos sin paso de revisión (`9a276d5`).
- **16/09:** el servidor del modelo pasa a atender un escaneo a la vez (`b07da0c`).
- **23/09:** el flujo se vuelve editable y con dueño (`a1f8f39`). Cada evento guarda quién lo registró y quién lo editó, y hay `PUT`/`DELETE` para eventos, personas y asistentes sueltos. Un usuario normal solo ve y toca lo suyo, y un superadmin ve todo.
- **23/09:** el módulo se abre a cualquier usuario con rol asignado, no solo admin (`03f1ab4`). El dashboard, las estadísticas y el Excel quedan acotados por dueño (`d8d42e8`).
- **23/09:** el género se normaliza (`Femenino`/`FEMENINO` → `F`) y "Otro" deja de descartarse de las estadísticas (`5f7d85e`).

### 1.5 Autenticación
En `e99cf64` se reemplazó la columna única `User.auth_token` por una tabla `Session` (migración `user_activity.0003`). Un usuario puede tener una sesión por plataforma (app, web) a la vez.

---

## 2. Commit por commit (`agrohub_backend`)

| Commit | Fecha | Qué hace |
|---|---|---|
| `37a1800` | 01/08 | Corrección de identificación de personas en encuesta nutricional (toca `entities.py` y el repositorio MySQL del backend FastAPI anterior). |
| `2480848` | 02/08 | `migration_django`: reemplaza FastAPI por Django + DRF (4 apps, `config/`, Docker, nginx, docs). Elimina el código legado y `vercel.json`. |
| `e1a3559` | 03/08 | URLs de static y media configurables por variable de entorno, para el prefijo del proxy inverso. |
| `f3ebcec` | 30/08 | Agrega `apps.riego_iot` (gateways y dashboard), traído de `mqtt_agrohub`. Segunda base `mqtt` (Postgres) con `RiegoIotRouter`. |
| `da72693` | 30/08 | Referencia completa de la API de `riego_iot` para el frontend (`docs/API_RIEGO_IOT.md`). |
| `7d5e771` | 04/09 | Swagger/OpenAPI con `drf-spectacular` para los 42 endpoints. `FORCE_SCRIPT_NAME` para el prefijo `/api/agrohub`. |
| `98b1381` | 04/09 | Arregla el crash de Swagger UI (versión fija de `swagger-ui-dist`) y un campo `security` mal formado. |
| `e99cf64` | 06/09 | Crea `apps.asistencia_eventos` (OCR con PaddleOCR, scan → guardar, dashboard y Excel). Reemplaza `auth_token` por `Session`. Scripts `db_dump.sh`/`db_restore.sh` y `docs/onpremise-migration.md`. |
| `a74a6ac` | 08/09 | Merge de `migration_django` a `main`: `riego_iot` y el OCR quedan juntos en `main`. Agrega la migración inicial de `riego_iot`. |
| `f829737` | 08/09 | Documenta y agrega al `Dockerfile` las librerías del sistema que necesita OpenCV (`libgl1` y otras). |
| `2328ca5` | 08/09 | PaddleOCR con `enable_mkldnn=False` (bug de PaddlePaddle 3.x con oneDNN en CPU). |
| `a0167fe` | 08/09 | Motor OCR alternativo con modelo de visión local (`ASISTENCIA_OCR_ENGINE=llm`) y servicio `systemd/agrohub-ocr-llm.service`. |
| `163bd11` | 08/09 | Todos los campos del esquema JSON del LLM pasan a ser requeridos (antes omitía claves). |
| `df83944` | 08/09 | Deja de pedirle `tipo_documento` al LLM (desplazaba los demás campos). |
| `9a276d5` | 15/09 | `POST /asistencia-eventos/scan-bulk`. Agrega `python-dateutil` a `requirements.txt`. |
| `e3d34a0` | 16/09 | `riego_iot`: históricos de válvulas, health y conexión, y `PATCH` del nombre del dispositivo. |
| `6094852` | 16/09 | Historias de usuario de `riego_iot` (`docs/USER_STORIES_RIEGO_IOT.md`). |
| `62aa7c8` | 16/09 | `X-API-Key` como esquema de seguridad de OpenAPI en `riego_iot`. Lo reemplaza `f86ab4a`. |
| `1233635` | 16/09 | "feat: update riego eps". Por los archivos tocados cambia `asistencia_eventos` (serializers, urls y views), no `riego_iot`. Lo revierte el commit siguiente. |
| `23536b0` | 16/09 | Revierte `1233635`. |
| `f86ab4a` | 16/09 | `riego_iot` pasa de `X-API-Key` compartida a token de sesión con rol admin. Elimina `permissions.py` y `RIEGO_IOT_API_KEY`. |
| `2b1440c` | 16/09 | Merge de `origin/main`, sin cambios de contenido. |
| `b07da0c` | 16/09 | El servicio del modelo atiende un escaneo a la vez (`--parallel 1`). Los escaneos simultáneos fallaban por falta de memoria de contexto. |
| `a1f8f39` | 23/09 | Flujo editable con dueño: `registrado_por`, `editado_por`, `updated_at` (migraciones 0002 y 0003). `PUT`/`DELETE` de evento, persona y asistente. Agrega `docs/historias-de-usuario.md` y `docs/traspaso-informacion.md`. |
| `03f1ab4` | 23/09 | Escanear, guardar, ver, editar y borrar eventos queda abierto a cualquier rol asignado, acotado por dueño. |
| `d8d42e8` | 23/09 | Dashboard, estadísticas y Excel abiertos a cualquier rol, acotados por dueño. Solo `persona_detail` sigue siendo solo admin. |
| `5f7d85e` | 23/09 | Normaliza el género (`FEMENINO` → `F`) y agrega "Otro" a las estadísticas, que antes lo descartaban. |

---

## 3. Cambios en el servidor que no están en git

Estos cambios se hicieron directamente en el servidor. Si el servidor se reconstruye, hay que rehacerlos.

| Fecha | Cambio |
|---|---|
| 6–8/09 (aprox.) | Restauración de datos reales (6 tablas MySQL, 1.032 filas) en la base `agrohub_v2`, con un respaldo previo y el ajuste del charset (`utf8mb4`) para evitar caracteres corruptos. |
| 08/09 | Migraciones aplicadas en producción: `user_activity.0003`, `asistencia_eventos.0001` y `riego_iot.0001`, con respaldo previo de `users`. Despliegue de `main` con venv + gunicorn + systemd. |
| 08/09 | `apt install libgl1 libglib2.0-0 libsm6 libxext6 libxrender1` (necesarias para OpenCV/PaddleOCR). |
| noche del 08/09 | Se compiló `llama.cpp`, se descargó Qwen2.5-VL-7B (Q4_K_M) y se instaló el servicio `agrohub-ocr-llm` en el puerto 8010. En el `.env`: `ASISTENCIA_OCR_ENGINE=llm`. |
| noche del 08/09 | Timeout de gunicorn a 300 s (`--timeout 300`) y `proxy_read_timeout 300s` en nginx para `/api/agrohub/`. Sin esto, un escaneo con el LLM se cortaba. |
| 16/09 | `agrohub-ocr-llm` reiniciado con `--parallel 1` (el cambio está en `b07da0c`, pero el reinicio se hizo a mano). |
| 23/09 | Migraciones `asistencia_eventos.0002` y `0003` aplicadas, con respaldo previo de las tablas del módulo. Se borraron los eventos de prueba. |
| 23/09 | Ajustes puntuales de rol de algunos usuarios en producción. |

---

## 4. Cosas por revisar

- **Mensajes de commit poco claros:** `e99cf64` ("feat: upate backend") y `a1f8f39` ("feat: change of asistent flow") son cambios grandes con mensaje de una línea. `1233635` se llama "update riego eps" pero tocó `asistencia_eventos`. Conviene un mensaje que diga qué cambia y por qué.
- **PDF en la raíz del repo:** `a1f8f39` agregó `CamScanner 03-09-2026 10.07.pdf` (504 KB). Es una muestra de prueba, así que valdría moverlo a una carpeta de muestras o ignorarlo.
- **Servicio viejo `mqtt-agrohub-api` sigue activo:** es la API FastAPI standalone (puerto 8006). Se creía desactivada desde que `riego_iot` se movió a Django. Nginx no parece enrutarle tráfico, pero conviene confirmarlo y apagarla.
- **Paquete `mysql-server-8.0` a medio configurar en el host:** hace que `apt install` termine con error. No afecta al MySQL de Docker, que es el que usa la app.
- **Descripción del servicio:** el `systemd` de `agrohub-backend` todavía dice "(migration_django)" aunque corre `main`.
- **Género y etnia con el motor LLM:** las columnas angostas de género y pertenencia étnica no se leen de forma confiable (devuelve el mismo valor para todas las filas). Hay que revisar esos dos campos a mano antes de guardar. Está en `docs/asistencia-eventos.md`.
- **Pendiente:** la integración con la API de GPT para el OCR no se hizo, falta la clave de OpenAI.
- **Pendiente:** el reporte de cédulas únicas contra la población objetivo (tabla del DANE) y el campo de verificación de cédula.

---

## 5. `mqtt_agrohub` (broker Mosquitto y demonio de ingesta)

Fechas y mensajes tomados del historial de ese repo.

| Commit | Fecha | Qué hace |
|---|---|---|
| `6404a76` | 30/08 | Estructura inicial: broker Mosquitto y proceso Python que guarda los datos de los gateways. |
| `2b65e36` | 30/08 | Reutiliza el certificado de `back.alunaia.co` en vez de pedir un subdominio nuevo. |
| `24b2f5d` | 30/08 | Corrige la ruta del servicio systemd (`venv/` y no `.venv/`). |
| `3401ca1` | 30/08 | `agregar_gateway.sh`: da de alta un gateway con un solo comando. |
| `29c645e` | 30/08 | Ignora el archivo de credenciales que genera el alta por lote. |
| `a213223` | 30/08 | API de administración de gateways y telemetría (después reemplazada por `riego_iot` en Django). |
| `859f829` | 30/08 | Mueve esa API del puerto 8005 al 8006 por colisión. |
| `4b2c370` | 30/08 | Expone esa API por nginx en `/api/agrohub-mqtt/`. |
| `a43907d` | 30/08 | Documenta los permisos de `mosquitto-admin`: dos huecos encontrados en producción. |
| `6c0ea19` | 30/08 | Documentación completa de infraestructura e instalación. |
| `1821be6` | 01/09 | Los gateways pueden leer sus propios tópicos de salida (data, válvulas, health, status). |
| `7be6d78` | 01/09 | Merge de `origin/main`. |
| `99c6e16` | 27/09 | Tópicos `config/state`, `config/set` y `cloud/health`, y un usuario `ahub-monitor`. |
| `43c1d99` | 27/09 | Merge de `origin/main`. |
| `8b9dae7` | 27/09 | Aplica los cambios de `config/state` y tópicos con comodín también a la API de administración. |
| `93e29a1` | 27/09 | Da a los gateways ya existentes acceso de lectura a su propio `config/state`. |
| `8c6c628` | 27/09 | El script de recarga necesita `sudo` para `systemctl`, no solo acceso al archivo de grupo. |

---

Para regenerar la lista:

```bash
git log --since="2026-08-01" --until="2026-10-01" --reverse --date=short \
  --pretty=format:'%h | %ad | %an | %s'
```
