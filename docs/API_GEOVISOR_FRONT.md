# API del geovisor — contrato para el frontend

Todo bajo `https://back.alunaia.co/api/agrohub`. **Los tres endpoints del geovisor son públicos: no llevan
`Authorization`.** Los ejemplos son respuestas reales del código (con datos de ejemplo).

| Para qué | Método y URL | Token |
|---|---|---|
| Pintar el mapa (todos los puntos) | `GET /agrohubs/puntos` | **no** |
| Ficha completa al tocar un punto | `GET /agrohubs/<id>` | **no** |
| Temperatura/humedad actual del lugar | `GET /agrohubs/<id>/datos` | **no** |

Flujo: 1) `/puntos` al abrir el mapa → 2) al tocar un marcador `/agrohubs/<id>` → 3) si
`tiene_dispositivo` es `true`, pedir `/agrohubs/<id>/datos` (y refrescar cada 60 s).

## 1. Puntos para el mapa — `GET /agrohubs/puntos`

Sin paginación, liviano. Filtros opcionales (combinables, sin importar mayúsculas):
`?departamento=Magdalena` · `?municipio=Santa Marta` · `?cultivo=cacao` · `?grupo_etnico=indigena`.

```json
{
  "status": 200,
  "message": "puntos",
  "data": [
    {
      "id": 1,
      "numero": "AH-014",
      "nombre": "Guachaca Centro",
      "latitud": 11.2681,
      "longitud": -73.9872,
      "municipio": "Santa Marta",
      "departamento": "Magdalena",
      "tiene_dispositivo": true
    },
    {
      "id": 2,
      "numero": "AH-015",
      "nombre": "Ciénaga Centro",
      "latitud": 11.0067,
      "longitud": -74.2478,
      "municipio": "Ciénaga",
      "departamento": "Magdalena",
      "tiene_dispositivo": false
    }
  ]
}
```

- `latitud` y `longitud` son números (grados decimales). `tiene_dispositivo`: ¿tiene sensores?
- Con filtros que no coinciden devuelve `"data": []` (200, no error).
- Ejemplo filtrado: `GET /agrohubs/puntos?municipio=Santa Marta&cultivo=cacao` →

```json
{
  "status": 200,
  "message": "puntos",
  "data": [
    {
      "id": 1,
      "numero": "AH-014",
      "nombre": "Guachaca Centro",
      "latitud": 11.2681,
      "longitud": -73.9872,
      "municipio": "Santa Marta",
      "departamento": "Magdalena",
      "tiene_dispositivo": true
    }
  ]
}
```

## 2. Detalle (ficha completa) — `GET /agrohubs/<id>`

```json
{
  "status": 200,
  "message": "agrohub",
  "data": {
    "id": 1,
    "numero": "AH-014",
    "nombre": "Guachaca Centro",
    "familias": [
      "Familia Pérez Mejía",
      "Familia Torres"
    ],
    "lugar": {
      "departamento": "Magdalena",
      "municipio": "Santa Marta",
      "es_cabecera_municipal": false,
      "vereda": "Guachaca"
    },
    "asociaciones": [
      "Asociación de Productores de Guachaca"
    ],
    "grupo_etnico": "indigena",
    "comunidad": "Kogui",
    "cultivos": [
      "Cacao",
      "Plátano"
    ],
    "coordenadas": {
      "latitud": 11.2681,
      "longitud": -73.9872
    },
    "video": "/api/agrohub/media/agrohubs/3ac865b6-6833-4565-94a5-8090e60d99f2_video.mp4",
    "dispositivo": {
      "device_id": "device0014",
      "nombre": "KIT 14 Loma del Bálsamo"
    }
  }
}
```

Un AgroHub **sin** video, sin dispositivo y en cabecera municipal:

```json
{
  "status": 200,
  "message": "agrohub",
  "data": {
    "id": 2,
    "numero": "AH-015",
    "nombre": "Ciénaga Centro",
    "familias": [
      "Familia Gómez"
    ],
    "lugar": {
      "departamento": "Magdalena",
      "municipio": "Ciénaga",
      "es_cabecera_municipal": true,
      "vereda": null
    },
    "asociaciones": [],
    "grupo_etnico": null,
    "comunidad": null,
    "cultivos": [
      "Yuca"
    ],
    "coordenadas": {
      "latitud": 11.0067,
      "longitud": -74.2478
    },
    "video": null,
    "dispositivo": null
  }
}
```

Notas:
- `lugar.vereda` es `null` cuando `es_cabecera_municipal` es `true`.
- `grupo_etnico`: `null` | `ninguno` | `indigena` | `afro` | `rom` | `raizal`. `comunidad` solo viene con `indigena`.
- `familias`, `asociaciones` y `cultivos` son listas de texto (pueden estar vacías, también `familias`)
- `nombre` es el nombre público del punto (puede ser `null`): usarlo como título del marcador/ficha y `numero` como código.
- `video` es una ruta relativa al dominio: reproducir con `https://back.alunaia.co` + `video` (ej. `<video src=…>`), o `null`.
- `dispositivo`: `{device_id, nombre}` o `null` (`nombre` puede ser `null`).
- El detalle público **no** trae quién lo creó ni fechas de auditoría.
- No existe → `404`: `{"detail": "AgroHub no encontrado"}`

## 3. Datos abiertos del lugar — `GET /agrohubs/<id>/datos`

Última lectura del gateway asociado. Solo datos ambientales (nunca válvulas, configuración ni credenciales).

```json
{
  "status": 200,
  "message": "datos",
  "data": {
    "agrohub_id": 1,
    "numero": "AH-014",
    "ultima_lectura": "2026-10-13T15:42:10Z",
    "en_linea": true,
    "ambiente": {
      "medido_en": "2026-10-13T15:42:10Z",
      "temperatura": 29.1,
      "humedad": 70.0
    },
    "suelo": {
      "medido_en": "2026-10-13T15:41:58Z",
      "humedad_suelo": 41.2,
      "temperatura_suelo": 27.5,
      "conductividad": 310.0
    }
  }
}
```

- `en_linea`: `true` si hubo una lectura en los últimos 3 minutos. Si `false`, mostrar "sin conexión" y la hora de `ultima_lectura`.
- `ambiente` o `suelo` pueden ser `null` si el gateway aún no ha enviado ese tipo de lectura; `ultima_lectura` también.
- Fechas en ISO 8601 UTC (convertir a hora local de Colombia para mostrar).
- Sin dispositivo asociado → `404`: `{"detail": "Este AgroHub no tiene un dispositivo IoT asociado"}`. No lo pidas si `tiene_dispositivo` es `false`.

## 4. Errores y detalles de integración

| Caso | Respuesta |
|---|---|
| AgroHub inexistente | `404` `{"detail": "AgroHub no encontrado"}` |
| Sin dispositivo en `/datos` | `404` `{"detail": "Este AgroHub no tiene un dispositivo IoT asociado"}` |
| Aún no hay AgroHubs | `200` con `"data": []` |

- Los endpoints funcionan **con y sin barra final** (`/agrohubs/puntos`, `/agrohubs/1`).
- CORS: abiertos para el front; no se necesita cookie ni token.
- Los datos de gestión (`tipologia`, `responsable`, `celular`, `tipo_fuente`, `punto_captacion`) **no** existen en estos endpoints públicos: no los busques aquí.

## 5. cURL de prueba

```bash
curl "https://back.alunaia.co/api/agrohub/agrohubs/puntos"
curl "https://back.alunaia.co/api/agrohub/agrohubs/1"
curl "https://back.alunaia.co/api/agrohub/agrohubs/1/datos"
```

## 6. Para el panel de administración (con token)

Crear, editar, borrar, subir video y asociar el dispositivo (roles `admin`, `superadmin`, `investigador`):
ver `HU_AGROHUBS_GEOVISOR.md`. Listado del panel: `GET /agrohubs/?page=1&page_size=20&q=` (con token), que devuelve
`{total, page, page_size, total_pages, results:[ficha + creado_por, editado_por, created_at, updated_at]}`.
