# AgroHub SAN — API de login y dashboard

Historias de usuario, peticiones `curl` y respuestas **reales** (probadas en vivo contra producción) para el flujo de login por token y los endpoints del dashboard de la Encuesta Nutricional SAN.

**Base URL:** `https://backend.agroshub.online`

## Cómo funciona la autenticación

Token opaco tipo `Token <valor>` (no es JWT) — el mismo sistema de login que ya usa `user-activity`. Se pide una sola vez y se reutiliza en el header `Authorization` de cada endpoint protegido.

Solo **`/dashboard/veredas`** y **`/dashboard/municipios/{municipio}`** exigen token. **`/dashboard/municipios`** es público, y el resto del CRUD de `encuesta-nutricional` (registro y consulta de encuestas) también sigue público, sin tocar.

```
1. Registro (una vez)  →  POST /user-activity/users/register
2. Login               →  POST /user-activity/users/login   → devuelve el token
3. Guardar el token     →  no expira solo; se reemplaza en el próximo login (una sesión por usuario)
4. Usar en cada llamada →  header  Authorization: Token <valor>
```

---

## 1. Registro

**Como** persona nueva del equipo, **quiero** crear mi cuenta para poder loguearme después.

Registro público. El usuario queda **sin rol asignado** hasta que un superadmin se lo asigne (`PUT /users/{user_id}/role`). Necesita el `id` de una asociación existente — se consulta en `GET /user-activity/associations`.

`POST /user-activity/users/register` · público

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Usuario Demo Dashboard",
    "phone": "3000000099",
    "identification": "9999999999",
    "email": "demo.dashboard@agrohub.test",
    "password": "DemoDashboard2026!",
    "association_id": 1
  }'
```

### Response — `201 Created`

```json
{
  "status": 201,
  "message": "usuario creado",
  "data": null
}
```

> `phone` e `identification` son únicos — repetir cualquiera de los dos en un segundo registro devuelve error, no un usuario duplicado.

---

## 2. Login

**Como** usuario ya registrado, **quiero** loguearme para obtener mi token.

Acepta teléfono **o** número de identificación indistintamente en `phone_or_identification`.

`POST /user-activity/users/login` · público

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_or_identification": "3000000099",
    "password": "DemoDashboard2026!"
  }'
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "login ok",
  "data": {
    "token": "672b50ce-4c3a-45ed-b081-9c5d084749f1",
    "role": "user",
    "name": "Usuario Demo Dashboard",
    "email": "demo.dashboard@agrohub.test"
  }
}
```

De aquí en adelante, todas las llamadas protegidas usan:
`Authorization: Token 672b50ce-4c3a-45ed-b081-9c5d084749f1`

---

## 3. Resumen por municipio

**Como** cualquier persona del equipo (sin loguearse), **quiero** ver cuántas encuestas hay por municipio.

Vista general para abrir el dashboard. Cuenta encuestas activas y miembros de hogar, agrupado por municipio, de mayor a menor.

`GET /encuesta-nutricional/dashboard/municipios` · público

### Request

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/municipios"
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "resumen generado",
  "data": [
    { "municipio": "Algarrobo", "total_encuestas": 64, "total_miembros": 146 },
    { "municipio": "Fundación", "total_encuestas": 47, "total_miembros": 111 },
    { "municipio": "Aracataca", "total_encuestas": 25, "total_miembros": 108 },
    { "municipio": "El Retén", "total_encuestas": 16, "total_miembros": 56 }
  ]
}
```

---

## 4. Resumen por vereda/comunidad

**Como** usuario autenticado, **quiero** desglosar un municipio por vereda o comunidad.

Mismo conteo que el anterior, pero agrupado también por `vereda_comunidad`. El filtro `?municipio=` es opcional — sin él trae las veredas de los cuatro municipios juntas.

`GET /encuesta-nutricional/dashboard/veredas` · **requiere token**

### Request

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/veredas?municipio=Algarrobo" \
  -H "Authorization: Token 672b50ce-4c3a-45ed-b081-9c5d084749f1"
```

### Response — `200 OK` (16 veredas reales de Algarrobo)

```json
{
  "status": 200,
  "message": "resumen generado",
  "data": [
    { "municipio": "Algarrobo", "vereda_comunidad": "Bellavista", "total_encuestas": 11, "total_miembros": 30 },
    { "municipio": "Algarrobo", "vereda_comunidad": "26 de julio", "total_encuestas": 10, "total_miembros": 22 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Félix Vega", "total_encuestas": 9, "total_miembros": 17 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Granja de los abuelos", "total_encuestas": 8, "total_miembros": 21 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Estación del ferrocarril", "total_encuestas": 5, "total_miembros": 8 },
    { "municipio": "Algarrobo", "vereda_comunidad": "El Carmen", "total_encuestas": 4, "total_miembros": 8 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Bella vista", "total_encuestas": 3, "total_miembros": 13 },
    { "municipio": "Algarrobo", "vereda_comunidad": "El ciruelo", "total_encuestas": 3, "total_miembros": 3 },
    { "municipio": "Algarrobo", "vereda_comunidad": "La granja de los abuelos", "total_encuestas": 3, "total_miembros": 9 },
    { "municipio": "Algarrobo", "vereda_comunidad": "26 julio", "total_encuestas": 2, "total_miembros": 4 },
    { "municipio": "Algarrobo", "vereda_comunidad": "26", "total_encuestas": 1, "total_miembros": 5 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Alex Reservado Campestre", "total_encuestas": 1, "total_miembros": 2 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Divino Niño", "total_encuestas": 1, "total_miembros": 1 },
    { "municipio": "Algarrobo", "vereda_comunidad": "El Espinon", "total_encuestas": 1, "total_miembros": 1 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Fundación", "total_encuestas": 1, "total_miembros": 1 },
    { "municipio": "Algarrobo", "vereda_comunidad": "Loma del Bálsamo", "total_encuestas": 1, "total_miembros": 1 }
  ]
}
```

> **Dato de calidad:** hay variantes de escritura de la misma vereda ("26 de julio" / "26 julio" / "26", "Bellavista" / "Bella vista"). El endpoint agrupa por texto exacto, así que quedan como filas separadas — vale la pena normalizar `vereda_comunidad` en el formulario de captura para un conteo más limpio.

---

## 5. Detalle estadístico por municipio

**Como** usuario autenticado, **quiero** el detalle nutricional de un municipio puntual.

Promedios antropométricos (edad, peso, talla, circunferencia de cintura, IMC), promedio de diversidad dietética e inseguridad alimentaria (ELCSA), y tres distribuciones listas para graficar: por clasificación de seguridad alimentaria, por sexo y **por rango de edad**.

`GET /encuesta-nutricional/dashboard/municipios/{municipio}` · **requiere token**

### Request

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/municipios/Algarrobo" \
  -H "Authorization: Token 672b50ce-4c3a-45ed-b081-9c5d084749f1"
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "detalle generado",
  "data": {
    "municipio": "Algarrobo",
    "total_encuestas": 64,
    "total_miembros": 146,
    "promedio_edad_anios": 35.04,
    "promedio_peso_kg": 60.32,
    "promedio_talla_cm": 156.83,
    "promedio_circunferencia_cintura_cm": 84.75,
    "promedio_imc": 44.42,
    "promedio_diversidad_dietetica": 7.83,
    "promedio_inseguridad_alimentaria": 3.66,
    "distribucion_seguridad_alimentaria": {
      "Inseguridad severa": 48,
      "Inseguridad leve": 5,
      "Inseguridad moderada": 11
    },
    "distribucion_sexo": {
      "Mujer": 74,
      "Hombre": 63
    },
    "distribucion_edad": {
      "0-5": 5,
      "6-12": 15,
      "13-17": 13,
      "18-29": 36,
      "30-44": 30,
      "45-59": 25,
      "60+": 20
    }
  }
}
```

`distribucion_edad` siempre trae los 7 rangos fijos (`0-5, 6-12, 13-17, 18-29, 30-44, 45-59, 60+`), aunque algún rango tenga 0 personas — así el front puede pintar el histograma completo sin tener que rellenar huecos.

> **Ojo con `promedio_imc: 44.42`:** está inflado por errores de digitación en la encuesta de origen (tallas cargadas mal, ej. `talla_cm: 55` para un adulto). El endpoint promedia lo que hay en la base tal cual — vale la pena limpiar esos registros antes de mostrar el promedio como un hallazgo real.

### Municipio sin encuestas activas — `404 Not Found`

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/municipios/MunicipioQueNoExiste" \
  -H "Authorization: Token 672b50ce-4c3a-45ed-b081-9c5d084749f1"
```

```json
{ "detail": "No hay encuestas activas para ese municipio" }
```

---

## 6. Exportar a Excel (una hoja por municipio)

**Como** usuario autenticado, **quiero** descargar todos los datos en un solo Excel para analizarlos fuera del dashboard.

Genera un archivo `.xlsx` con **una hoja por municipio**. Cada fila es un miembro del hogar, con todos los campos de la encuesta (secciones A, C y D/ELCSA) repetidos por fila, más sus datos antropométricos (sección B) y de persona (cédula, nombre, edad, sexo, etc.).

`GET /encuesta-nutricional/export/excel` · **requiere token**

### Request

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/export/excel" \
  -H "Authorization: Token 672b50ce-4c3a-45ed-b081-9c5d084749f1" \
  -o encuestas_nutricionales.xlsx
```

### Response — `200 OK`

Devuelve el binario del archivo (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename=encuestas_nutricionales.xlsx`). Al abrirlo en Excel/Sheets vas a ver una pestaña por cada municipio (`Algarrobo`, `Fundación`, `Aracataca`, `El Retén`), cada una con sus propias filas de encuestas.

> `alimentos_preferidos` (lista de hasta 5 alimentos) se exporta como texto separado por `; ` en una sola celda, ya que Excel no admite listas dentro de una celda.

### Sin encuestas activas — `404 Not Found`

```json
{ "detail": "No hay encuestas activas para exportar" }
```

---

## 7. Casos de error de autenticación

**Como** cliente del API, **quiero** saber qué pasa si el token falta o es inválido.

Aplica a `/dashboard/veredas` y `/dashboard/municipios/{municipio}` — no a `/dashboard/municipios`, que es público.

### Sin header `Authorization` — `401 Unauthorized`

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/municipios/Algarrobo"
```

```json
{ "detail": "Falta header Authorization: Token <token>" }
```

### Token inválido o expirado (reemplazado por otro login) — `401 Unauthorized`

```bash
curl "https://backend.agroshub.online/encuesta-nutricional/dashboard/municipios/Algarrobo" \
  -H "Authorization: Token token-falso-12345"
```

```json
{ "detail": "Token inválido" }
```

> El login es de sesión única — si otro dispositivo loguea el mismo usuario, el token anterior deja de servir de inmediato (mismo 401 "Token inválido").

---

## Tabla resumen

| Método | Ruta | Auth | Para qué sirve |
|---|---|---|---|
| `POST` | `/user-activity/users/register` | Público | Crear cuenta (rol `user`) |
| `POST` | `/user-activity/users/login` | Público | Obtener el token |
| `GET` | `/encuesta-nutricional/dashboard/municipios` | Público | Total encuestas + miembros por municipio |
| `GET` | `/encuesta-nutricional/dashboard/veredas` | Token | Igual, desglosado por vereda/comunidad |
| `GET` | `/encuesta-nutricional/dashboard/municipios/{municipio}` | Token | Promedios antropométricos + ELCSA + distribuciones (seguridad alimentaria, sexo, edad) de un municipio |
| `GET` | `/encuesta-nutricional/export/excel` | Token | Descarga un `.xlsx` con una hoja por municipio y todos los campos de encuesta + miembros |

---

**Cuenta de prueba usada en todos los ejemplos:** teléfono `3000000099`, contraseña `DemoDashboard2026!`, rol `user`. Se creó en producción solo para generar estas respuestas reales y verificables — bórrala o cámbiale la contraseña cuando ya no la necesites para pruebas.
