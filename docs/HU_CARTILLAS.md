# Cartillas — historias de usuario

Módulo `cartillas`: biblioteca pública de cartillas educativas en PDF (ej. *Lo que aprendimos del
mercado de nuestras hortalizas*), con su índice de páginas. **Leer es público**; subir, editar y
borrar es de `admin`, `superadmin`, `investigador` y `comunicaciones`.

Base URL: `https://back.alunaia.co/api/agrohub/cartillas/` · Auth solo para escribir:
`Authorization: Token <token>`.

## Ficha de una cartilla

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `tema` | texto | sí | ej. `Mercados`; sirve de filtro |
| `titulo` | texto | sí | ej. `Lo que aprendimos del mercado de nuestras hortalizas` |
| `resumen` | texto | sí | se usa en la búsqueda |
| `para` | texto | no | público objetivo, ej. `Productor` |
| `fecha_publicacion` | fecha `YYYY-MM-DD` | no | por defecto hoy; define el orden del listado |
| `paginas` | entero | no | **se cuenta del PDF**; solo se manda si no se pudo leer |
| `indice` | lista de `{titulo, pagina}` | no | secciones y página del PDF donde empiezan |
| archivo PDF | archivo | **sí** al crear | máximo **20 MB** |

Calculados por el sistema: `tamano_bytes`, `archivo` (URL del PDF), y para el equipo editor
`creado_por`, `editado_por`, `created_at`, `updated_at`.

## Endpoints

| Acción | Método y path | Quién |
|---|---|---|
| Listado + búsqueda | `GET /` | **público** |
| Detalle (con índice) | `GET /<id>` | **público** |
| Temas y públicos usados | `GET /filtros` | **público** |
| Subir cartilla | `POST /` | admin, superadmin, investigador, comunicaciones |
| Editar | `PUT /<id>` | ídem |
| Reemplazar el PDF | `POST /<id>/archivo` | ídem |
| Eliminar | `DELETE /<id>` | ídem |

---

### HU-C01 — Subir una cartilla

**Como** integrante de comunicaciones, investigación o administración, **quiero** subir una cartilla
con su PDF, resumen e índice, **para** ponerla a disposición pública.

1. `POST /cartillas/` · `multipart/form-data`: campo **`data`** (JSON como texto) y campo **`archivo`** (PDF).
2. Obligatorios: `tema`, `titulo`, `resumen` y el PDF. Sin PDF → `400`.
3. El archivo debe ser PDF real (`.pdf` y cabecera `%PDF`) de máximo 20 MB; si no → `422` en `archivo`.
4. `paginas` se cuenta del PDF. Cada `pagina` del índice debe estar entre 1 y `paginas`; si no → `422` en `indice`.
5. El índice se guarda ordenado por página. Queda registrado quién la creó.
6. Responde `201` con la ficha completa.

```js
const form = new FormData();
form.append('data', JSON.stringify({
  tema: 'Mercados',
  titulo: 'Lo que aprendimos del mercado de nuestras hortalizas',
  resumen: 'Lo que encontramos al preguntar por precios y comercialización…',
  para: 'Productor',
  fecha_publicacion: '2026-09-01',
  indice: [
    { titulo: 'Portada', pagina: 1 },
    { titulo: '¿Para qué sirve esta cartilla?', pagina: 5 },
    { titulo: '1. Lo que fuimos a preguntar', pagina: 6 },
    { titulo: '2. Lo que encontramos', pagina: 7 },
    { titulo: 'Actividad: ¿Dónde se me pierde a mí?', pagina: 10 },
    { titulo: '3. La cuenta que hay que aprenderse', pagina: 12 },
    { titulo: '4. Nuestra ruta', pagina: 14 },
    { titulo: '5. Para tener a mano', pagina: 16 },
    { titulo: 'Lo que este grupo se compromete a hacer', pagina: 17 },
    { titulo: 'Mis apuntes', pagina: 18 },
  ],
}));
form.append('archivo', pdf);
await fetch(`${BASE}/cartillas/`, { method: 'POST', headers: { Authorization: `Token ${token}` }, body: form });
```

### HU-C02 — Listado público con búsqueda

**Como** visitante, **quiero** ver las cartillas ordenadas de la más reciente a la más antigua y
buscarlas por lo que recuerde, **para** encontrar la que necesito.

1. `GET /cartillas/` **sin token**. Orden: `fecha_publicacion` descendente.
2. **Búsqueda `?q=`** (no exacta): se parte en palabras y **todas** deben aparecer, sin importar
   mayúsculas ni tildes (`comercializacion` encuentra *comercialización*), en el tema, el título, el
   resumen, el público o **algún título del índice**. Ej.: `?q=hortalizas precios`.
3. Filtros opcionales: `?tema=Mercados`, `?para=Productor`. Paginación: `?page=1&page_size=20` (máx. 100).
4. Cada resultado trae: `id, tema, titulo, resumen, para, paginas, tamano_bytes, fecha_publicacion, archivo` (sin índice).
5. `GET /cartillas/filtros` devuelve `{temas: [...], para: [...]}` para armar los filtros.

```json
{ "status": 200, "message": "cartillas",
  "data": { "total": 2, "page": 1, "page_size": 20, "total_pages": 1,
    "results": [ { "id": 1, "tema": "Mercados", "titulo": "Lo que aprendimos del mercado de nuestras hortalizas",
                   "resumen": "…", "para": "Productor", "paginas": 22, "tamano_bytes": 2831155,
                   "fecha_publicacion": "2026-09-01", "archivo": "/api/agrohub/media/cartillas/…pdf" } ] } }
```

### HU-C03 — Detalle público con índice

`GET /cartillas/<id>` (sin token) devuelve la ficha y `indice: [{titulo, pagina}]` ordenado por
página. El PDF se abre con `archivo` (ruta relativa al dominio: `https://back.alunaia.co` + la ruta);
para saltar a una sección usa `…pdf#page=<pagina>`. `404` si no existe. Si quien consulta tiene rol
editor y manda su token, la respuesta incluye también `creado_por`, `editado_por` y fechas.

### HU-C04 — Editar y reemplazar el PDF

1. `PUT /cartillas/<id>` es **parcial** (`tema, titulo, resumen, para, fecha_publicacion, paginas, indice`).
   Si viene `indice`, **reemplaza el índice completo**. Registra quién editó.
2. `POST /cartillas/<id>/archivo` (multipart, campo `archivo`) reemplaza el PDF: recalcula
   `paginas` y `tamano_bytes` y borra el anterior.
3. Al editar solo el índice se valida contra las páginas del PDF actual.

### HU-C05 — Eliminar

`DELETE /cartillas/<id>` → `204`; borra la ficha, su índice y el PDF. El front pide confirmación.

## Permisos y errores

- Escribir sin token → `401`; con un rol que no sea de los cuatro (`user`, sin rol) → `403`.
- El rol `comunicaciones` se asigna con `PUT /user-activity/users/<id>/role` (un superadmin).
- Validación → `422` con `{"status":422,"errores":[{"campo","mensaje",…}]}`; `campo` indica el input.
- **Límite de nginx:** el cuerpo de la petición no puede pasar de 20 MB (es también el máximo del PDF).
