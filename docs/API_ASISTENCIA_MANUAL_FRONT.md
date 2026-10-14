# Formulario de asistencia (registro manual) — endpoints e historias para el front

Para **registrar a mano un evento y sus asistentes**, sin subir ni escanear una hoja. Base:
`https://back.alunaia.co/api/agrohub/asistencia-eventos`. Todo exige `Authorization: Token <token>` y funciona con
**cualquier rol con sesión** (`user`, `admin`, `superadmin`, `investigador`, `comunicaciones`): cada quien ve y edita **solo los
eventos que él registró** (el superadmin ve todos). Un evento ajeno responde `404`. Sin token, `401`; sin rol, `403`.

## Flujo del formulario manual

1. El usuario llena el **encabezado** (tema, responsable, lugar, fecha, horas) y **la lista de personas** → `POST /eventos` (HU-W33).
2. Si faltó alguien o se registró después → `POST /eventos/<id>/asistentes` (HU-W34).
3. Si luego se consigue la hoja física → `POST /eventos/<id>/documento` (HU-W35).
4. Corregir o retirar a alguien: `PUT`/`DELETE /eventos/<id>/asistentes/<documento>`; corregir el encabezado: `PUT /eventos/<id>`
   (ver `HU_ASISTENCIA_EVENTOS.md`, sección 5).

---

## HU-W33 — Registrar un evento manualmente (encabezado + asistentes)

**Roles:** cualquier rol con sesión (solo ve/edita lo propio).
**Como** responsable de un evento, **quiero** llenar el formulario con los datos del evento y de cada asistente,
**para** guardarlo sin depender del escaneo con OCR.

`POST /asistencia-eventos/eventos` · `Content-Type: application/json`

```json
{
  "tema": "Taller de compostaje",
  "responsable": "Ana Ruiz",
  "lugar": "Vereda Guachaca",
  "fecha": "2026-10-12",
  "hora_inicio": "09:00",
  "hora_final": "12:00",
  "asistentes": [
    {
      "nombre": "Luis Pérez",
      "tipo_documento": "CC",
      "numero_documento": "1081800111",
      "telefono": "3001112233",
      "edad": 45,
      "genero": "M",
      "pertenencia_etnica": "ninguno"
    }
  ]
}
```

Respuesta `201`:
```json
{
  "status": 201,
  "message": "evento guardado",
  "data": {
    "id": 1,
    "total_asistentes": 1
  }
}
```

Reglas:
1. **Obligatorios:** `tema` y **al menos un asistente**. Todo lo demás es opcional.
2. `fecha` en **`YYYY-MM-DD`** y horas en **`HH:MM`** (24 h). Es un formulario manual: el front manda ya ese formato.
3. Cada asistente se guarda por **upsert del documento**: si la persona ya existía se actualizan sus datos; una persona puede estar en muchos eventos.
4. Dos filas con el mismo documento en la misma carga → `422`.
5. Si el documento viene vacío se asigna uno provisional (`PROV-…`, ver HU-W26). Si no hay tipo de documento: 18 o más → `CC`, menos de 18 → `TI`.
6. Opcional: adjuntar la hoja desde el principio enviando `multipart/form-data` con el campo `data` (el JSON como texto) y `archivo`.

### Campos de cada asistente

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `nombre` | texto | no | |
| `tipo_documento` | texto (`CC`, `TI`, `CE`, `RC`, `PEP`, `PPT`, `PA`) | no | si falta se infiere por edad |
| `numero_documento` | texto | no | se guarda solo con dígitos (`1.081.800.111` → `1081800111`); vacío → provisional |
| `municipio` | texto | no | si falta se usa el **lugar del evento** |
| `telefono` | texto | no | |
| `edad` | entero | no | |
| `genero` | `F` \| `M` \| `O` | no | también acepta `Femenino`, `Masculino`, `Otro` |
| `pertenencia_etnica` | `ninguno` \| `indigena` \| `afro` \| `rom` \| `raizal` | no | vacío → `ninguno` |
| `comunidad` | texto (máx. 100) | no | **solo** si `pertenencia_etnica = indigena` |

Opciones de comunidad para el desplegable: `GET /asistencia-eventos/comunidades` (incluye "Otra" con texto libre).

---

## HU-W34 — Agregar personas a un evento ya registrado

**Roles:** cualquier rol con sesión (solo en eventos propios; el superadmin, en cualquiera).
**Como** responsable de un evento, **quiero** sumar asistentes que faltaron después de guardarlo, **para** no tener que volver a crearlo.

`POST /asistencia-eventos/eventos/<evento_id>/asistentes` · JSON · mismas reglas por persona que HU-W33:

```json
{
  "asistentes": [
    {
      "nombre": "María Gómez",
      "numero_documento": "1081800222",
      "telefono": "3004445566",
      "edad": 17,
      "genero": "F",
      "pertenencia_etnica": "indigena",
      "comunidad": "Kogui",
      "municipio": "Santa Marta"
    },
    {
      "nombre": "Sin Cédula",
      "edad": 30,
      "genero": "F"
    }
  ]
}
```

Respuesta `201` (`alerta` viene cuando el documento es provisional):
```json
{
  "status": 201,
  "message": "2 asistente(s) agregados",
  "data": {
    "evento_id": 1,
    "agregados": 2,
    "total_asistentes": 3,
    "asistentes": [
      {
        "numero_documento": "1081800222",
        "tipo_documento": "TI",
        "nombre": "María Gómez",
        "municipio": "Santa Marta",
        "alerta": null
      },
      {
        "numero_documento": "PROV-64EBE273CE",
        "tipo_documento": "PROV",
        "nombre": "Sin Cédula",
        "municipio": "Vereda Guachaca",
        "alerta": "Documento provisional: la persona no presentó cédula; pendiente de actualizar"
      }
    ]
  }
}
```

Errores `422` (usar `errores[].campo` para marcar la fila exacta; los índices cuentan desde 0):

| Caso | `campo` | `mensaje` |
|---|---|---|
| Persona ya registrada en ese evento | `asistentes.0.numero_documento` | La persona 1081800111 ya está registrada en este evento. |
| Comunidad con etnia no indígena | `asistentes.0.comunidad` | Solo aplica cuando pertenencia_etnica es 'indigena'. |
| Lista vacía | `asistentes` | Debe incluir al menos un asistente |
| Documento repetido dentro de la misma carga | `asistentes` | Documentos repetidos en la misma carga: … |

```json
{
  "status": 422,
  "message": "Datos inválidos en la solicitud",
  "total_errores": 1,
  "errores": [
    {
      "campo": "asistentes.0.numero_documento",
      "mensaje": "La persona 1081800111 ya está registrada en este evento.",
      "tipo_error": "invalid",
      "valor_recibido": "1.081.800.111"
    }
  ]
}
```

Para **corregir** a alguien que ya está en el evento no se vuelve a agregar: `PUT /eventos/<id>/asistentes/<documento>`.
`404` si el evento no existe o no es tuyo.

---

## HU-W35 — Adjuntar o reemplazar el documento de respaldo

**Roles:** cualquier rol con sesión (solo en eventos propios; el superadmin, en cualquiera).
**Como** responsable de un evento registrado a mano, **quiero** subir después la hoja física (PDF o foto), **para** que quede la evidencia.

`POST /asistencia-eventos/eventos/<evento_id>/documento` · `multipart/form-data` · campo **`archivo`**.
Reemplaza el anterior (lo borra del disco). Respuesta `200`:

```json
{
  "status": 200,
  "message": "documento guardado",
  "data": {
    "evento_id": 1,
    "documento_escaneado": "/api/agrohub/media/asistencia_eventos/efb1555e-aacd-4aaa-9619-12bf077218c7_hoja.pdf"
  }
}
```

`documento_escaneado` es una ruta relativa al dominio (`https://back.alunaia.co` + la ruta). Aparece también en `GET /eventos/<id>`.

---

## Checklist del front (formulario manual)

1. Cargar las comunidades de `GET /comunidades`; mostrar `comunidad` solo con etnia indígena y vaciarla si cambia.
2. Mandar `fecha` como `YYYY-MM-DD` y horas como `HH:MM`.
3. Permitir **agregar filas** de asistentes (botón "+ persona"): al guardar por primera vez, `POST /eventos`; después, `POST /eventos/<id>/asistentes`.
4. Marcar cada error 422 con `errores[].campo`; resaltar las filas con `alerta` (documento provisional).
5. Tras guardar, `GET /eventos/<id>` devuelve el evento completo con todos sus asistentes.
6. Ofrecer "Adjuntar hoja" cuando `documento_escaneado` sea `null`.
