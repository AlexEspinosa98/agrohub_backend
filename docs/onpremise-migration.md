# Migración de datos a onpremise

Cómo mover **todos** los datos actuales (todas las tablas de las 4 apps: `data_characterization`, `hub_cgsm`, `encuesta_nutricional`, `user_activity`) desde la base de datos MySQL actual hacia la base de datos onpremise que levanta `docker-compose.yml` (servicio `db`).

Es un dump/restore nativo de MySQL (`mysqldump` / `mysql`), no un export a nivel de Django — preserva todo exacto (ids, FKs, columnas `JSONField`, y la propia tabla `django_migrations`, así que `manage.py migrate` en el destino no tiene nada que aplicar).

Los scripts corren `mysqldump`/`mysql` dentro de un contenedor `mysql:8.0` desechable, así que no hace falta instalar el cliente de MySQL localmente — solo tener Docker disponible.

## 1. Generar el dump

Desde la máquina donde estés (necesita alcanzar el host de la base de datos actual, configurado en `.env`):

```bash
./scripts/db_dump.sh
```

Guarda un archivo en `backups/agrohub_<fecha>.sql` (esa carpeta está en `.gitignore` — nunca se commitea, contiene datos reales de usuarios: hashes de contraseña, cédulas, etc.).

Para apuntar a otra fuente sin tocar `.env`, pasa las variables por línea de comandos (tienen prioridad sobre `.env`):

```bash
DB_HOST=otro-host DB_NAME=otra_db DB_USER=otro_user DB_PASSWORD=otra_pass ./scripts/db_dump.sh
```

## 2. Copiar el dump al servidor onpremise

El `.sql` generado en el paso 1 hay que llevarlo al servidor onpremise (`scp`, USB, lo que aplique).

## 3. Levantar el stack onpremise (solo la base de datos por ahora)

En el servidor onpremise, con el `.env` de ese entorno ya configurado (mismos nombres de variable `DB_NAME`/`DB_USER`/`DB_PASSWORD`, pero apuntando al servicio local):

```bash
docker compose up -d db
```

## 4. Restaurar

Desde el directorio del proyecto en el servidor onpremise:

```bash
./scripts/db_restore.sh backups/agrohub_<fecha>.sql
```

Esto ejecuta `mysql` dentro del propio contenedor `db` vía `docker compose exec`, usando las credenciales del `.env` local — no expone el puerto de la base de datos hacia afuera para hacerlo.

## 5. Verificar y arrancar la app

```bash
docker compose up -d app nginx
python manage.py migrate   # debe decir "No migrations to apply"
```

Con eso el resto de la app (`entrypoint.sh` → `migrate` → `collectstatic` → gunicorn) arranca ya contra los datos migrados.

## Notas

- El dump incluye las tablas `sessions` y `conversations`. Los tokens de sesión activos al momento del dump siguen siendo válidos después de restaurar — no obliga a los usuarios a volver a loguearse si el corte se hace rápido.
- Si el usuario de la base de datos actual tiene privilegios restringidos (típico en hosting compartido), `mysqldump` puede advertir sobre `PROCESS privilege` al intentar volcar tablespaces — el script ya pasa `--no-tablespaces` para evitarlo; no afecta los datos.
- Repetir el dump/restore es seguro (`db_restore.sh` sobreescribe las tablas existentes), pero solo debe apuntar a la base onpremise — nunca usar `db_restore.sh` contra la base de datos actual en producción.
