# AgroHub — API de recuperación de contraseña (OTP por correo)

Historias de usuario, peticiones `curl` y respuestas **reales** (probadas en vivo contra producción) para el flujo de "olvidé mi contraseña".

**Base URL:** `https://backend.agroshub.online`

## Cómo funciona

- El usuario pide un código escribiendo su **correo** — no hace falta que esté logueado.
- Si el correo está registrado, le llega un **código de 6 dígitos** por email, válido por **10 minutos**.
- Con ese código + una contraseña nueva, confirma el cambio en un segundo paso.
- El código es de **un solo uso**: una vez usado (o vencido), hay que pedir uno nuevo.
- Al cambiar la contraseña, la sesión activa se cierra (el `token` que tuviera guardado deja de servir) — debe loguearse de nuevo con la contraseña nueva.
- Por seguridad, pedir el código **siempre responde el mismo mensaje**, exista o no una cuenta con ese correo (para que nadie use este endpoint para averiguar qué correos están registrados en la plataforma).

```
1. Usuario olvida su contraseña
   → POST /user-activity/users/forgot-password  {"email": "..."}
   → revisa su correo, recibe un código de 6 dígitos

2. Usuario ingresa el código + su nueva contraseña
   → POST /user-activity/users/reset-password  {"email": "...", "otp": "123456", "new_password": "..."}
   → queda con la contraseña nueva, debe loguearse otra vez
```

---

## 1. Solicitar el código

**Como** usuario que olvidó su contraseña, **quiero** pedir un código de verificación a mi correo para poder cambiarla.

`POST /user-activity/users/forgot-password` · público

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com"}'
```

### Response — `200 OK` (siempre, exista o no la cuenta)

```json
{
  "status": 200,
  "message": "Si el correo está registrado, se envió un código de verificación",
  "data": null
}
```

> El front **no debe** mostrar un error distinto si el correo "no existe" — la API nunca lo revela. Simplemente muestra este mensaje y pasa a la pantalla de "ingresa el código".

### Pediste otro código muy rápido — `429 Too Many Requests`

Si se pide un código nuevo antes de que pasen 60 segundos desde el anterior:

```json
{ "detail": "Espera un momento antes de solicitar otro código" }
```

El front debería deshabilitar el botón de "reenviar código" ~60 segundos después de cada solicitud, para no mostrarle este error al usuario innecesariamente.

---

## 2. Confirmar el código y establecer la nueva contraseña

**Como** usuario, **quiero** ingresar el código que recibí por correo junto con mi nueva contraseña para recuperar el acceso a mi cuenta.

`POST /user-activity/users/reset-password` · público

### Request

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "otp": "123456",
    "new_password": "MiClaveNueva2026!"
  }'
```

### Response — `200 OK`

```json
{
  "status": 200,
  "message": "contraseña actualizada",
  "data": null
}
```

Después de esto, cualquier token de sesión anterior de ese usuario queda invalidado — el front debe redirigirlo al login para que entre con la contraseña nueva.

### Código incorrecto, ya usado o vencido — `400 Bad Request`

```bash
curl -X POST "https://backend.agroshub.online/user-activity/users/reset-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "otp": "000000", "new_password": "x"}'
```

```json
{ "detail": "Código inválido o expirado" }
```

> Mismo mensaje tanto si el código está mal escrito, como si ya venció (pasaron más de 10 min), como si el correo no existe — no distingas estos casos en el front, solo muestra "código inválido o expirado" y deja reintentar o volver a pedir uno nuevo.

---

## Resumen de campos

| Endpoint | Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|---|
| `forgot-password` | `email` | string | Sí | El correo de la cuenta |
| `reset-password` | `email` | string | Sí | Mismo correo al que llegó el código |
| `reset-password` | `otp` | string | Sí | Los 6 dígitos recibidos por correo, tal cual (como texto, puede tener ceros a la izquierda) |
| `reset-password` | `new_password` | string | Sí | Sin restricciones de formato en el backend — valida en el front lo que consideres necesario (mínimo de caracteres, etc.) |

## Tabla resumen

| Método | Ruta | Auth | Para qué sirve |
|---|---|---|---|
| `POST` | `/user-activity/users/forgot-password` | Público | Envía el código OTP de 6 dígitos al correo |
| `POST` | `/user-activity/users/reset-password` | Público | Verifica el código y cambia la contraseña |

---

**Nota de UX sugerida para el front:** dos pantallas — (1) pedir el correo → mostrar mensaje genérico y pasar a (2) ingresar código de 6 dígitos + nueva contraseña. Si el usuario no recibe nada en unos minutos, dejar reintentar (respetando el cooldown de 60s) antes de asumir que escribió mal su correo.
