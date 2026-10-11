# Plan: identidad y roles unificados de AgroHub

Estado: **borrador para validar**. No hay nada implementado. Los puntos marcados **[por definir]**
los confirma Alexander a medida que da el contexto.

## 1. Punto de partida (verificado en el servidor)

| | `agrohub_backend` (este repo) | AgroHub red social / marketplace |
|---|---|---|
| Ruta | `/api/agrohub/` (:8001) | `/api/agrohub-rs/` (:8005) |
| Código | este repo | `github.com/josefcc96/agrohub` (`backend_stacks/agrohub`) |
| BD | MySQL `agrohub_v2` | Postgres 18 (Docker), + Redis, Celery |
| Usuarios | 16 | 85 (84 activos) |
| Clave primaria | entero | UUID |
| Identificador | teléfono y cédula únicos; correo opcional y **no único** | correo y username únicos |
| Sesión | token opaco en tabla `Session` (`Token <x>`) | JWT SimpleJWT (`Bearer`, 15 min / 7 días) |
| Roles | un texto: `user` / `admin` / `superadmin` (+ tabla `Role` de catálogo) | sin rol global (`is_staff`/`is_superuser`); rol por comunidad en `HubMembership` (MEMBER, MODERATOR, PLATFORM_MODERATOR, ADMIN) |

Los dos siguen siendo **backends separados**. En el servidor no hay ningún frontend desplegado, así
que la compatibilidad se cuida solo para los clientes externos.

## 2. Decisiones ya tomadas

1. Roles nuevos: `enlace`, `comunicaciones` e `investigador` (además de `user` y `admin`;
   `administrador` = `admin`). Dentro de `user` habrá **`user_lider`** y **`user_miembro`**.
2. Además de un admin global, debe poder haber **admins de ciertos módulos** únicamente.
3. **Una persona puede tener varios roles** a la vez.
4. **Inicio de sesión con correo, teléfono o cédula** (cualquiera de los tres).
5. La migración/unificación de bases de datos se hace **cuando Alexander dé la orden**. Los
   backends pueden seguir siendo distintos.
6. El código del otro AgroHub se puede modificar (con cuidado de no romperlo).
7. Alcance: **solo los dos AgroHub** (no kunsamu, aluna_propositos ni mida).
8. Lo existente debe seguir funcionando durante la transición.
9. **`admin` y `administrador` son el mismo rol** (acceso total). No se crea uno nuevo.
10. **Líder es de un AgroHub** (el sitio físico del geovisor). Se modela como pertenencia
    `Membership(user, agrohub, tipo)` con `tipo` = `lider` | `miembro`.
11. **Los usuarios nuevos nacen con rol `user`** (ya aplicado en el código, ver HU-T02).

## 3. Diseño propuesto

### 3.1 Roles en dos capas

- **Roles de la persona** (varios por usuario): tabla `UserRole(user, role)`. El catálogo `Role` ya
  existe y se amplía con los nuevos nombres.
- **Permiso por módulo** (admin parcial): `ModuleAccess(user, modulo, nivel)` con `nivel` en
  `lectura | edicion | admin`. Módulos de hoy: `asistencia`, `agrohubs` (geovisor),
  `encuesta_nutricional`, `hub_cgsm`, `data_characterization`, `riego_iot`, `user_activity`.
  Un `admin` global tiene `admin` en todos; un "admin de asistencia" solo en ese.
- **Líder / miembro** son un atributo de pertenencia a un **AgroHub**, no un rol global. Así
  alguien puede ser líder en un AgroHub y miembro en otro. `Membership(user, agrohub, tipo)`.
  **[por definir: quién asigna líderes y qué puede hacer cada tipo]**
- **Compatibilidad:** el campo actual `User.role` se conserva como "rol principal" calculado, para
  que las verificaciones de hoy (`IsAdminRole`, `IsAuthenticatedWithRole`) no cambien. Las nuevas
  verificaciones leen `UserRole` / `ModuleAccess`.
- Qué puede hacer cada rol **[por definir: Alexander lo da poco a poco]**. Hasta entonces solo
  existen en el catálogo, sin permisos nuevos.

### 3.2 Login con correo, teléfono o cédula

Un solo campo `identificador` + `password`; el backend detecta si es correo, teléfono o cédula
(normalizando espacios, `+57`, puntos de miles) y busca el usuario.

**Problema detectado antes de poder hacerlo:** el correo no es único en este backend. Hoy hay al
menos un correo repetido (usuarios 5 y 18 comparten `espinosaalexander09@gmail.com`; además hay
dos "Ricardo Pupo" con correos distintos). Hay que **depurar duplicados y volver el correo único**
(permitiendo vacío) antes de aceptarlo para iniciar sesión.

### 3.3 Una identidad, dos backends

Opción recomendada: **este backend es la fuente de identidad** y el otro la consulta.

1. El otro AgroHub guarda en su usuario un `identity_id` (id de esta base) y acepta el token de
   aquí **validándolo contra este backend** (consulta `GET /user-activity/users/me` con el token).
   Es la forma más simple y no obliga a compartir llaves de firma.
2. Sus roles por comunidad (`HubMembership`) se quedan allá; los roles globales vienen de aquí.
3. Alternativa si se prefiere: este backend emite JWT firmados que el otro valida localmente
   (más rápido, pero hay que compartir/rotar llaves).

La **unificación física de bases** (¿un solo Postgres? ¿mantener MySQL?) queda para cuando
Alexander lo ordene; el diseño de arriba funciona con las bases separadas.

## 4. Fases

| Fase | Qué | Riesgo |
|---|---|---|
| 0 | Depurar usuarios: duplicados de correo, normalizar teléfonos y cédulas; asignar rol a quien no tiene | bajo |
| 1 | Catálogo de roles ampliado + `UserRole` + `ModuleAccess`; `User.role` se mantiene | bajo (aditivo) |
| 2 | Login por correo / teléfono / cédula (campo `identificador`; el login actual sigue funcionando) | bajo |
| 3 | Aplicar `ModuleAccess` en los módulos (empezando por asistencia y geovisor); roles nuevos con sus permisos | medio |
| 4 | El otro AgroHub acepta la identidad de aquí (`identity_id` + validación de token) | medio |
| 5 | Migrar/unificar las bases de datos (cuando Alexander lo ordene), con respaldo previo | alto |

Cada fase es reversible y no cambia las respuestas de los endpoints actuales.

## 5. Pendiente de definir

- Permisos concretos de `enlace`, `comunicaciones` e `investigador`.
- Líder / miembro: quién los asigna y qué puede hacer cada uno dentro de su AgroHub.
- Si la identidad de referencia es este backend (recomendado) o el otro.
- Qué pasa con los 85 usuarios de la red social al migrar: ¿se cruzan por correo con los 16 de aquí?
