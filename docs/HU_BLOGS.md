# Blogs — historias de usuario

Módulo `blogs`: entradas de blog con portada, etiquetas y contenido en Markdown. **Lo publicado se
lee sin token**; crear, editar, programar y borrar es de `admin`, `superadmin`, `investigador` y
`comunicaciones`.

Base URL: `https://back.alunaia.co/api/agrohub/blogs/` · Auth solo para escribir (y para que el
equipo vea borradores): `Authorization: Token <token>`.

## Ficha de una entrada

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `titulo` | texto | sí | |
| `resumen` | texto (máx. 600) | sí | extracto de la tarjeta; entra en la búsqueda |
| `contenido` | **Markdown** | sí | el front lo renderiza y **debe sanitizarlo** |
| `slug` | texto | no | URL amigable; se genera del título y es único (`mi-titulo`, `mi-titulo-2`) |
| `etiquetas` | lista de textos | no | se crean solas; no distingue mayúsculas |
| `autor` | texto | no | por defecto, el nombre de quien la crea |
| `estado` | `borrador` \| `publicado` | no | por defecto `borrador` |
| `fecha_publicacion` | fecha y hora ISO | no | al publicar sin fecha es "ahora"; **con fecha futura queda programada** |
| `portada` | imagen | no | `.jpg .jpeg .png .webp .gif`, máx. 5 MB |

Calculados: `tiempo_lectura_min` (≈200 palabras/min), `portada` (URL), y para el equipo editor
`estado`, `publicado`, `creado_por`, `editado_por`, `created_at`, `updated_at`.

## Endpoints

| Acción | Método y path | Quién |
|---|---|---|
| Listado + búsqueda | `GET /` | **público** (solo publicado) |
| Detalle (por id o slug) | `GET /<id o slug>` | **público** (solo publicado) |
| Etiquetas con conteo | `GET /etiquetas` | **público** |
| Crear | `POST /` | admin, superadmin, investigador, comunicaciones |
| Editar | `PUT /<id o slug>` | ídem |
| Poner/reemplazar portada | `POST /<id>/portada` | ídem |
| Quitar portada | `DELETE /<id>/portada` | ídem |
| Subir imagen para el contenido | `POST /imagenes` | ídem |
| Eliminar | `DELETE /<id o slug>` | ídem |

---

### HU-B01 — Crear una entrada

**Como** integrante de comunicaciones, **quiero** escribir una entrada con portada y etiquetas,
**para** publicarla o dejarla de borrador.

1. `POST /blogs/` con JSON, o `multipart/form-data` con **`data`** (JSON como texto) y **`portada`** (imagen opcional).
2. Obligatorios: `titulo`, `resumen`, `contenido`. Quien no sea del equipo editor recibe `403`; sin token, `401`.
3. `estado: "publicado"` sin `fecha_publicacion` la publica ya. Con fecha futura queda **programada**: no se
   ve en público hasta que llegue la hora. `borrador` nunca se ve en público.
4. `slug` repetido → `422` en `slug`. Portada que no sea imagen real o pase de 5 MB → `422` en `portada`.
5. Responde `201` con la entrada completa.

### HU-B02 — Contenido con imágenes

`POST /blogs/imagenes` (multipart, campo `imagen`) sube una imagen y devuelve `{"url": "/api/agrohub/media/blogs/contenido/….png"}`.
El editor la inserta en el Markdown como `![texto](url)` (anteponer el dominio `https://back.alunaia.co`).

### HU-B03 — Listado público con búsqueda

**Como** visitante, **quiero** ver las entradas más recientes primero y buscarlas, **para** encontrar lo que me interesa.

1. `GET /blogs/` **sin token**: solo `publicado` cuya `fecha_publicacion` ya llegó, de la más reciente a la más antigua.
2. **Búsqueda `?q=`** (no exacta): se parte en palabras y **todas** deben aparecer, sin importar mayúsculas
   ni tildes, en el título, resumen, contenido, autor o alguna etiqueta. Ej.: `?q=suelo seca`.
3. Filtro `?etiqueta=Suelos`. Paginación `?page=1&page_size=12` (máx. 100).
4. Cada resultado (sin `contenido`): `id, slug, titulo, resumen, portada, etiquetas, autor, fecha_publicacion, tiempo_lectura_min`.
5. `GET /blogs/etiquetas` → `[{nombre, total}]` solo con entradas publicadas (para filtros o nube de etiquetas).

### HU-B04 — Leer una entrada

`GET /blogs/<id o slug>` (sin token) devuelve todo, con `contenido` y hasta 3 `relacionados` (publicadas que
comparten etiquetas). Un borrador o una programada responden `404` en público. Si quien consulta es del
equipo editor y manda su token, **sí las ve** y recibe además `estado`, `publicado`, `creado_por`, etc.

### HU-B05 — Equipo editor: ver borradores y programadas

Con token de editor, `GET /blogs/?estado=borrador|publicado|todos` lista también lo no público
(un usuario sin rol de editor que mande `estado` simplemente lo ignora). Cada resultado trae `estado` y `publicado`.

### HU-B06 — Editar, portada y eliminar

1. `PUT /blogs/<id o slug>` es **parcial**; `etiquetas`, si viene, reemplaza la lista. Cambiar `estado` a
   `publicado` sin fecha la publica ya; volver a `borrador` la oculta. Registra quién editó.
2. `POST /blogs/<id>/portada` (campo `portada`) pone o reemplaza la imagen (borra la anterior);
   `DELETE /blogs/<id>/portada` la quita.
3. `DELETE /blogs/<id o slug>` → `204`; borra la entrada y su portada (no borra las etiquetas ni las imágenes
   que se hayan insertado en el contenido). El front pide confirmación.

## Permisos y errores

- Sin token → `401`; rol que no sea de los cuatro (`user`, sin rol) → `403`. El rol `comunicaciones` lo asigna un
  superadmin con `PUT /user-activity/users/<id>/role`.
- Validación → `422` con `{"status":422,"errores":[{"campo","mensaje",…}]}`.
- Límite de nginx: 20 MB por petición.
