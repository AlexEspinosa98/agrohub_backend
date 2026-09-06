# AgroHub — OCR de listas de asistencia (`asistencia_eventos`)

Módulo independiente (propio `apps/asistencia_eventos`, propias tablas) para digitalizar las hojas físicas manuscritas "Formato de Asistencia" que se llenan en los eventos de AgroHub (tema, responsable, lugar, fecha, horas, y la tabla de asistentes: nombre, documento, municipio, teléfono, edad, género, pertenencia étnica).

**Base URL:** `/asistencia-eventos/` — todos los endpoints requieren `Authorization: Token <token>` de un usuario con rol `admin` o `superadmin` (es la parte del flujo **web**, no la app de encuestas de campo).

## Por qué el flujo es en dos pasos

El formato es manuscrito. Se probó primero con Tesseract (OCR clásico) y no reconoció ni un solo asistente sobre una hoja real — Tesseract está pensado para texto impreso. Se cambió a **PaddleOCR** (modelo PP-OCRv6, corre 100% local en CPU, sin llamadas a APIs externas — importante porque el servidor va a ser onpremise), que sobre la misma hoja sí reconoció 9 de 10 asistentes, con los números de documento exactos.

Aun así, la letra manuscrita hace que el resultado sea un **borrador**, no un dato final — especialmente en nombres y en las casillas de género/etnia (una X manuscrita dentro de una columna angosta). Por eso el guardado real es un flujo de dos pasos:

```
1. POST /asistencia-eventos/scan     → sube el escaneo, corre OCR, devuelve TODO lo extraído
2. (front) el usuario revisa/corrige los datos devueltos
3. POST /asistencia-eventos/eventos  → recibe los datos ya depurados + el mismo archivo, y ahí sí guarda
```

Nada se guarda en el paso 1 — es solo lectura del archivo. El paso 2 es el único que escribe en la base de datos.

## 1. Escanear (`POST /scan`)

Multipart, campo `archivo` (PDF o imagen).

```bash
curl -X POST "$BASE/asistencia-eventos/scan" \
  -H "Authorization: Token $TOKEN" \
  -F "archivo=@hoja_asistencia.pdf"
```

Respuesta — devuelve **todo** lo que el OCR pudo extraer, sin filtrar nada, para que el frontend muestre el formulario ya prellenado:

```json
{
  "status": 200,
  "message": "Documento escaneado — revisa y corrige antes de guardar",
  "data": {
    "tema": "Socializacion de resultados: Agrohub del Magdalena",
    "responsable": "John Taborda Garaldo",
    "lugar": "Universidad del Magdalena -sta Mta",
    "fecha": "28/08/2026",
    "hora_inicio": "8:30 am",
    "hora_final": "12:30 pm",
    "asistentes": [
      {
        "nombre": "Leanis",
        "tipo_documento": null,
        "numero_documento": "1081806419",
        "municipio": "fundacion",
        "telefono": "1035950",
        "edad": null,
        "genero": "F",
        "pertenencia_etnica": "ninguno",
        "persona_ya_registrada": false
      }
    ],
    "texto_crudo_ocr": "... todo el texto reconocido, como respaldo si el parser de la tabla se equivocó ..."
  }
}
```

`persona_ya_registrada` indica si ese número de documento ya existe en la base — útil para que el frontend avise "esta persona ya está registrada, va a actualizar sus datos" en vez de tratarlo como alguien nuevo.

## 2. Guardar (`POST /eventos`)

Multipart: campo `data` con el JSON **ya corregido** (misma forma que `scan` devolvió, sin `texto_crudo_ocr` obligatorio) como texto, y campo `archivo` con el mismo PDF/imagen para guardarlo como evidencia.

```bash
curl -X POST "$BASE/asistencia-eventos/eventos" \
  -H "Authorization: Token $TOKEN" \
  -F "data=</tmp/datos_corregidos.json" \
  -F "archivo=@hoja_asistencia.pdf"
```

`data` debe tener esta forma:

```json
{
  "tema": "...",
  "responsable": "...",
  "lugar": "...",
  "fecha": "2026-08-28",
  "hora_inicio": "08:30",
  "hora_final": "12:30",
  "asistentes": [
    {
      "nombre": "...",
      "tipo_documento": "CC",
      "numero_documento": "1081806419",
      "municipio": "Fundación",
      "telefono": "3051035950",
      "edad": 17,
      "genero": "F",
      "pertenencia_etnica": "ninguno"
    }
  ]
}
```

- `numero_documento` es el único campo obligatorio por asistente. Dos filas con el mismo documento en la misma carga se rechazan (`422`).
- Cada persona se guarda por **upsert de número de documento** (`PersonaAsistente`, tabla `personas_asistentes`) — si el documento ya existe, se actualizan sus datos (nombre, género, etnia) en vez de crear un duplicado; una misma persona puede aparecer en muchos eventos con un solo registro maestro.
- El evento (`Evento`, tabla `eventos_asistencia`) y cada fila de asistencia (`RegistroAsistencia`, tabla `registros_asistencia`, con `municipio`/`telefono`/`edad` — datos que sí cambian de un evento a otro) son independientes de otros módulos.
- El PDF/imagen se guarda en `MEDIA_ROOT/asistencia_eventos/` (igual que las fotos de `hub_cgsm`) y su ruta relativa queda en `Evento.documento_escaneado`.

## Listado y detalle

- `GET /asistencia-eventos/eventos` — lista de eventos con conteo de asistentes.
- `GET /asistencia-eventos/eventos/<id>` — detalle completo, incluye la URL del PDF/imagen original.

## Dashboard

- `GET /asistencia-eventos/dashboard/resumen` → `{"total_personas", "total_eventos", "total_asistencias"}` (personas = individuos únicos por documento; asistencias = participaciones, una persona en 3 eventos cuenta 3 veces).
- `GET /asistencia-eventos/dashboard/estadisticas` (opcional `?evento_id=<id>` para un solo evento) → tabla Municipio × Género × rango de edad (0-14 / 15-19 / 20-59 / mayor de 60), con columna y fila de totales — mismo formato del reporte de estadísticas del proyecto.
- `GET /asistencia-eventos/dashboard/excel` (opcional `?evento_id=<id>`) → descarga un `.xlsx` con todo el dashboard en 4 hojas: **Resumen** (los 3 totales), **Estadisticas** (la misma tabla Municipio × Género × edad, con encabezado y fila Total en negrita), **Eventos** (listado con conteo de asistentes) y **Asistentes** (el detalle completo, una fila por persona por evento). Encabezados con fondo de color, fila superior congelada y columnas autoajustadas.

**Importante sobre `municipio` en el dashboard de estadísticas:** el valor viene tal cual lo escribió/corrigió el usuario en el paso de revisión — no hay una lista fija de municipios validada contra catálogo. Si dos cargas escriben el mismo municipio con ortografía distinta ("Fundación" vs "fundacion"), el dashboard las cuenta como filas separadas. Si esto importa para el reporte, conviene que el frontend use un desplegable con los municipios reales de Magdalena en el paso de corrección, en vez de un campo de texto libre — el backend no impone esa restricción todavía.

## Limitaciones conocidas del OCR

Probado contra una hoja real (`CamScanner 03-09-2026 10.07.pdf` del repo, letra manuscrita, 10 asistentes):

- 9 de 10 filas detectadas (una fila se perdió porque dos renglones muy pegados verticalmente se agruparon como uno solo — el agrupador de filas usa la altura de línea para decidir dónde empieza cada renglón, y en ese punto de la hoja el margen entre filas fue más chico de lo normal).
- Números de documento: 9/9 correctos en las filas detectadas — es el campo más confiable, que es lo que importa para la unicidad.
- Nombres: legibles pero con errores de transcripción típicos de OCR sobre manuscrita (ej. "Isabela" leído como "Sobela") — se espera que se corrijan en la revisión.
- Casillas de género/etnia (marca X dentro de una columna angosta): las más propensas a error — es la razón principal por la que existe el paso de revisión antes de guardar.
