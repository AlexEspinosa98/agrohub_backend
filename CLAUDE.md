# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working preferences

Make the code changes needed to complete the task directly — don't stop to ask for confirmation before editing/creating files or running local commands (installs, running the server, etc.). Never run `git commit`, `git push`, or open a PR without the user's explicit go-ahead first.

## What this is

AgroHub Magdalena API — a Django + Django REST Framework backend, dockerized (app + nginx + MySQL), for a rural-communities platform in the Colombian Caribbean. It serves several independent survey/data modules plus a user/auth/logbook module. This is a from-scratch **Django rewrite** of a previous FastAPI backend, merged into `main` via the `migration_django` branch; the legacy FastAPI code (`main.py`, `modules/`, `common/`, `database/`, `migrations_service/`, `vercel.json`) has since been deleted from the repo — don't go looking for it, and don't recreate a Vercel/FastAPI deployment path.

## Running locally

```bash
python -m venv venv && source venv/bin/activate   # if venv/ doesn't already exist
pip install -r requirements.txt
cp .env.example .env   # fill in real DB/mail/Gemini/etc. values
python manage.py migrate
python manage.py runserver
```

There is no test suite and no lint step configured — verify changes by running the server and hitting endpoints directly (`curl`/Postman); Django admin is at `/admin/`.

Config is read from `.env` via `python-dotenv` (loaded in `config/__init__.py`/`config/settings.py`): DB credentials (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), `SUPERADMIN_TOKEN` (bootstraps the first superadmin), `MAIL_*` (OTP password reset), `GEMINI_API_KEY` (chat), `WHATSAPP_TOKEN`/`WHATSAPP_VERIFY_TOKEN` (webhook), `ENABLE_TRANSCRIBE`/`WHISPER_MODEL`. The MySQL driver is **PyMySQL**, shimmed as `MySQLdb` in `config/__init__.py` — this is intentional (avoids needing compiled `mysqlclient` build tooling); don't "fix" it by installing mysqlclient unless you also update the Dockerfile.

## Docker / deployment

```bash
cp .env.example .env   # fill in real values; DB_HOST=db is already set for compose
docker compose up --build
```

`docker-compose.yml` runs three services: `db` (MySQL 8, persisted volume, fresh — **not** the old FastAPI backend's HostGator database), `app` (this Django project via `entrypoint.sh` → `migrate` → `collectstatic` → gunicorn), and `nginx` (reverse proxy on port 80, serves `/static/` and `/media/` directly from shared volumes, proxies everything else to `app`). `nginx/nginx.conf` has no TLS config — put a TLS-terminating proxy/load balancer in front in production, or extend it with certbot.

## Architecture

`config/` is the Django project package (`settings.py`, `urls.py`, `wsgi.py`/`asgi.py`, and the project-wide DRF exception handler in `exceptions.py`). Five Django apps live under `apps/`, mounted in `config/urls.py` — the first four are straight ports of the corresponding FastAPI module, the fifth (`asistencia_eventos`) was added natively in Django:

- `apps.data_characterization` — mounted at root (no prefix, matches the old FastAPI router). Surveys for agro-hub organizations, educational institutions, and household "right to food" characterization. Three models (`EncuestaAgrohub`, `EncuestaEducativa`, `EncuestaDerechoHumanoAlimentario`), no auth.
- `apps.hub_cgsm` (`/hub-cgsm/`) — actors, faenas (fishing/harvest activities), collection points, and environmental monitoring surveys for the CGSM hub. No auth.
- `apps.encuesta_nutricional` (`/encuesta-nutricional/`) — household nutritional/food-security surveys (ELCSA), with per-member anthropometric data linked via FK to a master `PersonaNutricional` table (a participant can appear in multiple surveys over time). Registration/listing/detail endpoints are public; `/dashboard/veredas`, `/dashboard/municipios/<municipio>`, and `/export/excel` require a token.
- `apps.user_activity` (`/user-activity/`) — registration/login, role management, activity logbooks (bitácoras), associations, password reset via email OTP, a Gemini-powered chat assistant that can register a logbook entry from a natural-language conversation (`<BITACORA>` tag protocol in `chat_service.py`), and a WhatsApp (Meta Business API) webhook that reuses the same chat flow.
- `apps.asistencia_eventos` (`/asistencia-eventos/`, any authenticated user with a role — `user`/`admin`/`superadmin`) — OCR digitization of handwritten event attendance sheets. Two-step flow: `POST /scan` runs the configured OCR engine over an uploaded PDF/image and returns everything it extracted as an unsaved draft; `POST /eventos` takes the human-corrected version of that same payload (plus the original file) and actually saves it — nothing is written to the DB until confirm. People are upserted by `numero_documento` into a master `PersonaAsistente` table (same pattern as `PersonaNutricional`), separate from the per-event `RegistroAsistencia` row. Event CRUD is scoped by `registrado_por` — anyone below `superadmin` only sees/edits/deletes events they themselves registered (see `apps/asistencia_eventos/views.py::_eventos_visibles`); the dashboard/estadisticas/excel endpoints and the shared `persona_detail` are still admin/superadmin-only since those aren't owner-scoped. See `docs/asistencia-eventos.md` for the full contract and known OCR limitations — Tesseract was tried first and failed to read a single row on a real handwritten sample.

Each app follows plain Django conventions: `models.py` (ORM, `db_table` set to match the field/table names used in the JSON API), `serializers.py` (DRF `Serializer`, not `ModelSerializer` — input validation mirrors the old Pydantic entities field-by-field), `views.py` (function-based `@api_view`, or `APIView` subclasses where one URL needs different permissions per HTTP method), `urls.py`. `apps/encuesta_nutricional/services.py` holds the non-trivial query/aggregation logic (dashboard stats, Excel export rows, the persona upsert-by-cédula logic) — put new business logic there, not in views.

**Multiple HTTP methods on one path must be one view function/class**, not two separate `path()` entries with the same URL — Django's URLconf matches by path only, not by method, so a second `path("x", ...)` for a different verb is silently unreachable (the first match wins regardless of method). Grep for `@api_view(\[` to see the established pattern: either a single `@api_view(["GET", "POST"])` function branching on `request.method`, or an `APIView` subclass with `get()`/`post()`/etc. and a `get_permissions()` override when the methods need different permission classes.

### Auth

Custom opaque bearer token (not JWT, not DRF's built-in TokenAuthentication app): clients send `Authorization: Token <token>`. `apps/user_activity/authentication.py` (`TokenHeaderAuthentication`) looks the token up in the `Session` table (not a `User.auth_token` column — that was the old single-session design); `apps/user_activity/permissions.py` has the role checks (`IsAuthenticatedWithRole`, `IsAdminRole`, `IsSuperadminRole`, `HasSuperadminServerToken`). A user can hold one active session per `platform` ("app"/"web"/null) at once — logging in again on the same platform replaces only that platform's session (`Session.objects.filter(user=user, platform=platform).delete()` in `login`), leaving sessions on other platforms untouched; logging in without a `platform` always adds a new session rather than replacing one. `POST /user-activity/users/logout` deletes just the calling session's row; `reset_password` deletes *all* of a user's sessions. Users register with `role=None` and cannot use protected endpoints until a `superadmin` assigns a role via `PUT /user-activity/users/<id>/role`. The first superadmin is bootstrapped through `POST /user-activity/users/superadmin`, gated by the `X-Superadmin-Token` header matching the `SUPERADMIN_TOKEN` env var (server secret, not a user session) — see `apps/user_activity/permissions.py::HasSuperadminServerToken`. `docs/roles-api.md`, `docs/password-reset-api.md`, `docs/dashboard-api.md` describe these flows in detail (written against the old FastAPI backend, but the request/response contract was kept intentionally identical — see below).

### Response conventions — kept byte-for-byte compatible with the old API

This migration was done as a strict API-contract-compatible rewrite (same routes, same JSON shapes) so existing clients don't need to change. Two shapes coexist by design, matching the original inconsistency — don't "fix" one to match the other:

- `user_activity` and `encuesta_nutricional` endpoints return `{"status": <int>, "message": "...", "data": ...}`.
- `data_characterization` and `hub_cgsm` endpoints return bare bodies (a list, `{"message": "..."}`, or the object itself) — no wrapper.
- `asistencia_eventos` (added natively, no old-backend contract to preserve) follows the wrapped shape, matching the other auth-gated modules.

Validation errors (422) are reshaped by the project-wide `config/exceptions.py::agrohub_exception_handler` into `{"status": 422, "message": "...", "total_errores": N, "errores": [{"campo", "mensaje", "tipo_error", "valor_recibido", ...}]}`, with `miembro_index`/`miembro_cedula`/`miembro_nombre` attached when the error belongs to `miembros[i]` in an `encuesta_nutricional` submission. When you add a nested/list input serializer elsewhere and want the same per-item error shape, validate through the parent serializer (`serializer.is_valid(raise_exception=True)`) rather than validating list items one-by-one and raising your own `ValidationError` — the exception handler derives `campo`/`valor_recibido` by walking the DRF error tree alongside the original request body, so it needs that nesting to line up (see `apps/data_characterization/views.py::_save_surveys` for the pattern used to get index-correct errors on a manually-validated list).

### Fixes made during the Django port (the FastAPI versions of these were broken/dead code)

- **`hub_cgsm`'s survey persistence was non-functional in the old backend**: its repository used Postgres-only SQL (`execute_values` from `psycopg2.extras`, which wasn't even imported; `ON CONFLICT ... DO UPDATE`; `RETURNING *`) against a `mysql-connector` connection, and referenced field names that didn't exist on the domain entities (e.g. `survey.hora_inicio`, `survey.mapa_offline`). The Django models or serializers you're looking at now are correct and match the Pydantic domain entities (the real client contract) — do not "restore" the old SQL.
- **`POST /hub-cgsm/surveys/`** was (and still is, for contract-compatibility) a no-op stub that just echoes back an unrelated `SurveyParametersCreate` payload — real survey creation happens through `/hub-cgsm/survey/actors`, `/survey/faena`, `/survey/punto-acopio`.
- List/array-typed survey fields (`rol_hub`, `tipo_activo`, `checklist_bioseguridad`, etc.) are `JSONField`s now, which the old raw-SQL insert couldn't have handled correctly anyway.

### Legacy FastAPI code

The pre-migration FastAPI app has been removed from the repo. If you see references to it (docs written against it, comments, old commit messages), treat the Django app under `apps/` as the source of truth for current behavior — don't try to resurrect or extend the FastAPI code.
