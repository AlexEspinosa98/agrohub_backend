# AgroHub — Traspaso: despliegue onpremise + migración completa de datos

Documento de traspaso para desplegar el backend en el servidor onpremise (`hubambiental002-alunakunsamu`, `45.65.200.111`) y migrar **todos** los datos desde la base de datos actual (`sh00008.hostgator.co` / `ricar394_agrohub`) hacia la base nueva onpremise. Escrito para que lo ejecute quien tenga acceso SSH real al servidor — esta sesión no tiene ese acceso configurado, así que los comandos de esta guía no fueron corridos contra el servidor, solo contra bases de datos de prueba desechables.

Antes de empezar, lee también:
- [onpremise-migration.md](onpremise-migration.md) — el mecanismo genérico de dump/restore (`scripts/db_dump.sh` / `scripts/db_restore.sh`).
- [asistencia-eventos.md](asistencia-eventos.md) — el módulo de OCR nuevo, incluye la nota de que el Dockerfile ya descarga los modelos de PaddleOCR en build time (no necesita internet en runtime).
- [historias-de-usuario.md](historias-de-usuario.md) — qué hace cada módulo, por si hay que verificar algo puntual después del corte.

## 0. Punto de partida importante: la base de datos actual no tiene historial de migraciones

Al conectar accidentalmente contra `sh00008.hostgator.co` durante esta sesión se confirmó que **las tablas ya existen** (`users`, `associations`, `roles`, etc., con las columnas que los modelos Django esperan) pero **`django_migrations` está vacía** para `user_activity` — la base nunca fue gestionada con `manage.py migrate`, aunque el backend Django lleva tiempo corriendo contra ella en producción (`backend.agroshub.online`).

Esto importa porque **no se puede simplemente correr `manage.py migrate` tal cual** contra una copia restaurada de esa base — Django intentaría recrear tablas que ya existen y fallaría (`Table 'associations' already exists`), exactamente el error que se vio en vivo durante esta sesión. La sección 4 de abajo explica cómo resolverlo marcando como aplicada (`--fake`) la historia que ya existe, app por app.

## 1. Preparar el servidor

```bash
ssh hubambiental002-alunakunsamu
docker --version && docker compose version   # confirmar que Docker está instalado
```

Si Docker no está instalado en el servidor, instalarlo antes de seguir (Docker Engine + el plugin `docker compose`).

## 2. Llevar el código al servidor

```bash
# en el servidor
git clone https://github.com/AlexEspinosa98/agrohub_backend.git
cd agrohub_backend
cp .env.example .env
nano .env   # completar con los valores REALES de producción:
            #   DJANGO_SECRET_KEY, SUPERADMIN_TOKEN, GEMINI_API_KEY/GOOGLE_API_KEY,
            #   MAIL_*, WHATSAPP_* (si aplica), y las credenciales de MySQL que
            #   quieras usar en el `db` local (DB_NAME/DB_USER/DB_PASSWORD/DB_ROOT_PASSWORD
            #   — DB_HOST se queda en "db", docker-compose lo fuerza así para el
            #   servicio `app`)
```

Si el servidor ya tiene una copia del repo de un intento anterior, usar `git pull` en vez de clonar de nuevo, y revisar `git status`/`git stash` antes de pisar cualquier cambio local que pueda haber quedado ahí.

## 3. Migrar los datos (dump de producción → restore onpremise)

Este paso corre en dos partes: el **dump** necesita salida a internet hacia `sh00008.hostgator.co` (se puede correr desde tu máquina local, que ya tiene ese acceso, o desde el propio servidor si también lo tiene); el **restore** corre en el servidor, contra el `db` de docker-compose.

```bash
# 3a. Generar un dump FRESCO de producción (no reusar el viejo del 2026-09-04
#     que quedó en backups/ de una prueba anterior — la producción puede
#     tener más datos ahora). Correr donde tengas red hacia sh00008.hostgator.co:
./scripts/db_dump.sh
#   -> genera backups/agrohub_<fecha>.sql

# 3b. Copiar el dump al servidor
scp backups/agrohub_<fecha>.sql hubambiental002-alunakunsamu:~/agrohub_backend/backups/

# 3c. En el servidor: levantar SOLO la base de datos primero (vacía)
ssh hubambiental002-alunakunsamu
cd agrohub_backend
docker compose up -d db
docker compose logs -f db   # esperar a que diga "ready for connections", Ctrl+C para salir

# 3d. Restaurar el dump dentro del contenedor db
./scripts/db_restore.sh backups/agrohub_<fecha>.sql
```

## 4. Reconciliar el historial de migraciones de Django (el paso que evita el error de "tabla ya existe")

**Importante:** `docker compose run --rm app <comando>` por sí solo NO sirve para esto — `entrypoint.sh` es el `ENTRYPOINT` de la imagen e ignora cualquier comando que le pases después del nombre del servicio (siempre corre su propia secuencia fija: esperar MySQL → `migrate --noinput` → `collectstatic` → gunicorn). Si en este punto haces `docker compose up -d app` directamente, ese `migrate --noinput` interno fallará exactamente con el mismo error de "tabla ya existe". Hay que pisar el entrypoint con `--entrypoint ''` para correr manage.py "a mano" antes de arrancar la app de verdad:

```bash
# En el servidor, con `db` ya arriba y con el dump restaurado:

docker compose build app   # primer build: descarga los modelos de PaddleOCR (puede tardar varios minutos)

# Marca como "ya aplicada" TODA la historia de migraciones de cada app que
# no cambió en esta sesión (sus tablas ya existen tal cual en el dump), y
# deja que Django corra de VERDAD solo lo genuinamente nuevo después.
#
# OJO: no uses `migrate --fake-initial` a secas — se probó en esta sesión
# contra una base simulando el estado real de producción y falla, porque
# --fake-initial solo marca como aplicada la PRIMERA migración de cada app;
# las migraciones posteriores de contenttypes/auth/admin (que producción sí
# tiene aplicadas de fábrica, aunque nunca quedaron registradas) intentan
# correr de verdad otra vez y truenan con "Unknown column ... already
# removed". Por eso cada app de abajo lleva su --fake explícito, sin acotar
# a una migración puntual (fakea toda su historia existente):
docker compose run --rm --entrypoint '' app python manage.py migrate contenttypes --fake
docker compose run --rm --entrypoint '' app python manage.py migrate auth --fake
docker compose run --rm --entrypoint '' app python manage.py migrate admin --fake
docker compose run --rm --entrypoint '' app python manage.py migrate sessions --fake
docker compose run --rm --entrypoint '' app python manage.py migrate data_characterization --fake
docker compose run --rm --entrypoint '' app python manage.py migrate hub_cgsm --fake
docker compose run --rm --entrypoint '' app python manage.py migrate encuesta_nutricional --fake
docker compose run --rm --entrypoint '' app python manage.py migrate user_activity 0002_seed_default_roles --fake

# Esto sí corre de verdad — son los cambios reales de esta sesión:
docker compose run --rm --entrypoint '' app python manage.py migrate user_activity      # aplica 0003: quita auth_token, crea sessions
docker compose run --rm --entrypoint '' app python manage.py migrate asistencia_eventos # crea las 3 tablas nuevas

# Verificar que no quedó nada pendiente:
docker compose run --rm --entrypoint '' app python manage.py showmigrations
docker compose run --rm --entrypoint '' app python manage.py migrate --check
echo "código de salida (debe ser 0): $?"
```

Esta secuencia exacta se probó en esta sesión contra una base MySQL desechable preparada para imitar el estado real de producción (tablas viejas presentes sin `auth_token`/`sessions`/`asistencia_eventos`, `django_migrations` vacía) y terminó limpia: `migrate --check` devolvió 0, `auth_token` quedó eliminada, y las tres tablas nuevas de `asistencia_eventos` más `sessions` quedaron creadas. Si en el servidor real algo de esto falla, es señal de que el esquema real divergió de lo que se probó aquí — no forzar nada a ciegas, revisar `showmigrations` primero.

**Riesgo residual a tener presente:** `--fake` confía ciegamente en que el esquema ya coincide con lo que la migración describe — no compara columna por columna. Si el esquema real de producción llegó a divergir de lo que esperan los modelos actuales (poco probable, pero no descartable dado que nunca hubo control de migraciones), podría no notarse en este paso y sí más tarde, al fallar un endpoint puntual en producción. Por eso el paso 5 (smoke test) no es opcional.

## 5. Levantar la aplicación y probar

```bash
docker compose up -d app nginx
docker compose logs -f app   # confirmar que gunicorn arrancó sin errores

# Smoke test mínimo — reemplaza <token> por uno real después de loguearte:
curl http://localhost/user-activity/associations
curl -X POST http://localhost/user-activity/users/login -H "Content-Type: application/json" \
  -d '{"phone_or_identification":"<telefono_de_un_usuario_real>","password":"<su_contraseña>"}'
curl http://localhost/user-activity/users -H "Authorization: Token <token_de_superadmin>"
curl http://localhost/asistencia-eventos/dashboard/resumen -H "Authorization: Token <token_de_superadmin>"
```

Si todo responde con datos reales (no 500, no errores de columna faltante), la migración quedó completa.

## 6. Cortar el tráfico real hacia el servidor onpremise

Esto ya es decisión de infraestructura (DNS, proxy, balanceador) fuera del alcance de este repo — `nginx/nginx.conf` no trae TLS configurado, así que hace falta un proxy con certificado delante (o extenderlo con certbot) antes de exponerlo públicamente. No lo hagas hasta confirmar el paso 5.

## Qué quedó pendiente de esta sesión (no ejecutado, solo preparado)

- Ningún comando de este documento se corrió contra `hubambiental002-alunakunsamu` ni contra `sh00008.hostgator.co` en modo escritura — todo se probó contra contenedores MySQL desechables.
- Hay un dump parcial de una conexión accidental a producción del 2026-09-04 en `backups/agrohub_20260904_081215.sql` (solo lectura, no se subió a ningún lado) — no usarlo para el restore real, generar uno nuevo (paso 3a).
- Las migraciones `user_activity.0003_remove_user_auth_token_session` y `asistencia_eventos.0001_initial` existen en el código pero no están aplicadas en ninguna base real todavía.
