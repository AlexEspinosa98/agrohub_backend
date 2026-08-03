# AgroHub — API de roles y superadmin

Historias de usuario, peticiones `curl` y respuestas **reales** (probadas en vivo contra producción, salvo donde se indique) para el flujo de gestión de usuarios y roles: bootstrap del superadmin, asignación de roles y CRUD de roles.

**Base URL:** `https://backend.agroshub.online`

## Cómo funciona

- Un usuario que se registra por `POST /user-activity/users/register` **no tiene rol** (`role: null`) hasta que un superadmin se lo asigna.
- Mientras no tenga rol, el usuario **puede loguearse** (obtiene su token) pero **no puede usar ningún endpoint protegido** — el sistema lo trata como inactivo.
- Solo un usuario con rol `superadmin` puede: listar usuarios, asignar roles, y crear/editar/eliminar roles.
- El **primer** superadmin no se crea con el flujo normal de registro — se crea con un endpoint especial protegido por un token de servidor (`SUPERADMIN_TOKEN`, variable de entorno), no por sesión de usuario.

```
1. Bootstrap (una vez)   →  POST /user-activity/users/superadmin   (header X-Superadmin-Token)
2. Login del superadmin  →  POST /user-activity/users/login        → devuelve el token de sesión
3. Con ese token, el superadmin puede:
   - listar usuarios          → GET  /user-activity/users
   - crear roles               → POST /user-activity/roles
   - listar roles               → GET  /user-activity/roles
   - editar un rol               → PUT  /user-activity/roles/{role_id}
   - eliminar un rol               → DELETE /user-activity/roles/{role_id}
   - asignar un rol a un usuario     → PUT  /user-activity/users/{user_id}/role
```

---

## 1. Crear el primer superadmin (bootstrap)

**Como** administrador del servidor, **quiero** crear la primera cuenta superadmin sin depender de que ya exista una, para poder arrancar el sistema de roles.

No requiere sesión previa — en su lugar exige el header `X-Superadmin-Token` con el valor configurado en la variable de entorno `SUPERADMIN_TOKEN` del servidor. Si el token no coincide (o la variable no está configurada), responde `403`.

`POST /user-activity/users/superadmin` · protegido por token de servidor

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/superadmin" \
  -H "Content-Type: application/json" \
  -H "X-Superadmin-Token: <valor de SUPERADMIN_TOKEN>" \
  -d '{
    "name": "Superadmin AgroHub",
    "phone": "3000000000",
    "identification": "0000000001",
    "email": "superadmin@agrohub.test",
    "password": "contra123"
  }'
```

### Response — `201 Created`

```json
{
  "status": 201,
  "message": "superadmin creado",
  "data": null
}
```

> Este endpoint es la única forma de obtener un usuario con rol `superadmin` sin que otro superadmin te lo asigne — por eso está gateado por un secreto de servidor y no por sesión.

---

## 2. Login (cualquier rol, incluido superadmin)

**Como** superadmin ya creado, **quiero** loguearme para obtener mi token de sesión.

Mismo endpoint de siempre — acepta teléfono, identificación **o correo** en `phone_or_identification`.

`POST /user-activity/users/login` · público

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_or_identification": "superadmin@agrohub.test",
    "password": "contra123"
  }'
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "login ok",
  "data": {
    "token": "029a5cab-844c-42fb-bb80-9feb4055c163",
    "role": "superadmin",
    "name": "Superadmin AgroHub",
    "email": "superadmin@agrohub.test"
  }
}
```

De aquí en adelante, todas las llamadas de esta sección usan:
`Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163`

> El login es de sesión única: cada login reemplaza el token anterior.

---

## 3. Usuario recién registrado: sin rol, sin acceso

**Como** superadmin, **quiero** entender qué le pasa a un usuario nuevo antes de asignarle un rol.

Al registrarse por `/users/register`, el usuario queda con `role: null`. Puede loguearse, pero cualquier endpoint protegido lo rechaza con `403` hasta que se le asigne un rol.

### Registro (público)

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Usuario Demo Roles",
    "phone": "3000000098",
    "identification": "9999999998",
    "email": "demo.roles@agrohub.test",
    "password": "DemoRoles2026!",
    "association_id": 1
  }'
```

```json
{ "status": 201, "message": "usuario creado", "data": null }
```

### Login del usuario sin rol

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/login" \
  -H "Content-Type: application/json" \
  -d '{"phone_or_identification": "3000000098", "password": "DemoRoles2026!"}'
```

```json
{
  "status": 200,
  "message": "login ok",
  "data": { "token": "2d4ec2a9-a61b-46fe-88ae-cd6e8a34e609", "role": null, "name": "Usuario Demo Roles", "email": "demo.roles@agrohub.test" }
}
```

### Intento de usar un endpoint protegido — `403 Forbidden`

```bash
curl "https://backend.agroshub.online/user-activity/logbooks/me" \
  -H "Authorization: Token 2d4ec2a9-a61b-46fe-88ae-cd6e8a34e609"
```

```json
{ "detail": "Tu cuenta aún no tiene un rol asignado. Contacta a un superadmin." }
```

---

## 4. Listar usuarios

**Como** superadmin, **quiero** ver todos los usuarios registrados para saber a quién le falta un rol.

`GET /user-activity/users` · **requiere rol superadmin**

### Request

```bash
curl "https://backend.agroshub.online/user-activity/users" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163"
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "usuarios",
  "data": [
    { "id": 11, "name": "Usuario Demo Roles", "phone": "3000000098", "identification": "9999999998", "email": "demo.roles@agrohub.test", "association_id": 1, "role": null, "created_at": "2026-07-21T21:58:03" },
    { "id": 8, "name": "Superadmin AgroHub", "phone": "3000000000", "identification": "0000000001", "email": "superadmin@agrohub.test", "association_id": null, "role": "superadmin", "created_at": "2026-07-21T21:41:08" }
  ]
}
```

---

## 5. Crear un rol

**Como** superadmin, **quiero** crear un rol nuevo (además de `user`, `admin`, `superadmin`, que ya vienen sembrados) para representar un perfil de permisos específico del equipo.

`POST /user-activity/roles` · **requiere rol superadmin**

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/roles" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163" \
  -H "Content-Type: application/json" \
  -d '{"name": "editor", "description": "Puede editar contenido pero no administrar usuarios"}'
```

### Response — `201 Created`

```json
{ "status": 201, "message": "rol creado", "data": null }
```

### Nombre de rol duplicado — `400 Bad Request`

```json
{ "detail": "Ya existe un rol con ese nombre" }
```

---

## 6. Listar roles

**Como** superadmin, **quiero** ver todos los roles disponibles antes de asignar uno.

`GET /user-activity/roles` · **requiere rol superadmin**

### Request

```bash
curl "https://backend.agroshub.online/user-activity/roles" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163"
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "roles",
  "data": [
    { "id": 2, "name": "admin", "description": "Administrador", "created_at": "2026-07-21T21:35:14" },
    { "id": 127, "name": "editor", "description": "Puede editar contenido pero no administrar usuarios", "created_at": "2026-07-21T22:04:00" },
    { "id": 3, "name": "superadmin", "description": "Super administrador", "created_at": "2026-07-21T21:35:14" },
    { "id": 1, "name": "user", "description": "Usuario estándar", "created_at": "2026-07-21T21:35:14" }
  ]
}
```

---

## 7. Asignar un rol a un usuario

**Como** superadmin, **quiero** asignarle un rol a un usuario para que deje de estar bloqueado y pueda usar la app con los permisos correspondientes.

El rol debe existir previamente en la tabla de roles (créalo primero con el endpoint de la sección 5 si no existe).

`PUT /user-activity/users/{user_id}/role` · **requiere rol superadmin**

### Request

```bash
curl -X PUT "https://backend.agroshub.online/user-activity/users/11/role" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163" \
  -H "Content-Type: application/json" \
  -d '{"role": "editor"}'
```

### Response — `200 OK`

```json
{ "status": 200, "message": "rol asignado", "data": null }
```

A partir de aquí, ese mismo token del usuario (sin necesidad de volver a loguearse) ya puede usar endpoints protegidos — el rol se lee de la base de datos en cada request.

### Rol inexistente — `404 Not Found`

```bash
curl -X PUT "https://backend.agroshub.online/user-activity/users/11/role" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163" \
  -H "Content-Type: application/json" \
  -d '{"role": "moderador"}'
```

```json
{ "detail": "El rol especificado no existe" }
```

### Usuario inexistente — `404 Not Found`

```json
{ "detail": "Usuario no encontrado" }
```

---

## 8. Editar un rol

**Como** superadmin, **quiero** corregir el nombre o la descripción de un rol ya creado.

`PUT /user-activity/roles/{role_id}` · **requiere rol superadmin**

### Request

```bash
curl -X PUT "https://backend.agroshub.online/user-activity/roles/127" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163" \
  -H "Content-Type: application/json" \
  -d '{"description": "Puede editar bitácoras y contenido, sin gestionar usuarios ni roles"}'
```

### Response — `200 OK`

```json
{ "status": 200, "message": "rol actualizado", "data": null }
```

Campos opcionales — se puede mandar solo `name`, solo `description`, o ambos. Si el nuevo `name` ya lo usa otro rol, responde `400` ("Ya existe un rol con ese nombre").

---

## 9. Eliminar un rol

**Como** superadmin, **quiero** eliminar un rol que ya no se usa, sin arriesgarme a dejar usuarios con un rol "fantasma".

El servidor **bloquea la eliminación** si hay al menos un usuario con ese rol asignado — hay que reasignarlos primero (sección 7, asignando otro rol) o dejarlos sin rol.

`DELETE /user-activity/roles/{role_id}` · **requiere rol superadmin**

> ⚠️ Implementado y probado contra la base de datos real, pero **pendiente del próximo despliegue** — si lo pruebas contra `backend.agroshub.online` ahora mismo puede devolver `405 Method Not Allowed` hasta que se publique.

### Rol todavía en uso — `400 Bad Request`

```bash
curl -X DELETE "https://backend.agroshub.online/user-activity/roles/127" \
  -H "Authorization: Token 029a5cab-844c-42fb-bb80-9feb4055c163"
```

```json
{ "detail": "No se puede eliminar: hay usuarios con este rol asignado" }
```

### Tras reasignar a los usuarios afectados — `200 OK`

```json
{ "status": 200, "message": "rol eliminado", "data": null }
```

### Rol inexistente — `404 Not Found`

```json
{ "detail": "Rol no encontrado" }
```

---

## 10. Solo superadmin puede administrar usuarios y roles

**Como** cliente del API, **quiero** saber qué pasa si un usuario autenticado pero sin rol `superadmin` intenta usar estos endpoints.

Aplica a `/users` (listar), `/users/{id}/role` (asignar) y todo `/roles` (listar, crear, editar, eliminar).

### Usuario con otro rol (ej. `editor`) — `403 Forbidden`

```bash
curl "https://backend.agroshub.online/user-activity/users" \
  -H "Authorization: Token 2d4ec2a9-a61b-46fe-88ae-cd6e8a34e609"
```

```json
{ "detail": "Requiere rol superadmin" }
```

> Nota: los endpoints de asociaciones y de creación/edición de usuario por administrador (`/users/admin-create`, `PUT /users/{id}`) siguen aceptando tanto `admin` como `superadmin` — el superadmin hereda los permisos de admin.

---

## Tabla resumen

| Método | Ruta | Auth | Para qué sirve |
|---|---|---|---|
| `POST` | `/user-activity/users/superadmin` | Token de servidor (`X-Superadmin-Token`) | Crear el primer superadmin (bootstrap) |
| `POST` | `/user-activity/users/login` | Público | Login (teléfono, identificación o correo) |
| `GET` | `/user-activity/users` | Rol superadmin | Listar todos los usuarios |
| `PUT` | `/user-activity/users/{user_id}/role` | Rol superadmin | Asignar un rol existente a un usuario |
| `GET` | `/user-activity/roles` | Rol superadmin | Listar roles disponibles |
| `POST` | `/user-activity/roles` | Rol superadmin | Crear un rol nuevo |
| `PUT` | `/user-activity/roles/{role_id}` | Rol superadmin | Editar nombre/descripción de un rol |
| `DELETE` | `/user-activity/roles/{role_id}` | Rol superadmin | Eliminar un rol sin usuarios asignados *(pendiente de desplegar)* |

---

**Cuentas de prueba usadas en estos ejemplos:**
- Superadmin: teléfono `3000000000` / correo `superadmin@agrohub.test`, contraseña `contra123`.
- Usuario demo sin rol → luego con rol `editor`: teléfono `3000000098`, contraseña `DemoRoles2026!`.

Se crearon en producción solo para generar estas respuestas reales y verificables — te recomiendo cambiar la contraseña del superadmin (y borrar o reasignar la cuenta demo) cuando ya no las necesites para pruebas.
