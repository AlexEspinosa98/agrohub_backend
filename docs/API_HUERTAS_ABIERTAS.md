# API · Huertas abiertas (integración con el front)

Backend de la rama `feature/huertas-abiertas` del front (`HU_HUERTAS_ABIERTAS.md`, HB01–HB08).
App Django `apps.huertas`. Base: `https://<host>/api/agrohub` (en el front, vía `/api/panel`).

- Sobre de respuesta: `{status, message, data}`. Errores de validación: **422** con
  `{status, message, total_errores, errores: [{campo, mensaje, tipo_error, valor_recibido}]}`.
- Sesión: `Authorization: Token <token>` (el de `POST /user-activity/users/login`). Lo público
  funciona sin token; si se manda, la respuesta se ajusta a la sesión (permisos, datos técnicos).
- `<ref>` = id del AgroHub **o** su número: `/agrohubs/AH-002/…` o `/agrohubs/ah-002/…` (el slug
  de la web sirve tal cual).

## 1. Quién puede qué

| Acción | Sin sesión | Cuidador de ESA huerta | Equipo (admin, superadmin, investigador) |
|---|---|---|---|
| Ver plan, lecturas, reportes, bitácora pública, movimientos, recomendaciones, seguimiento | sí | sí | sí |
| Mandar reportes | sí (con límite) | sí | sí |
| Cambiar plan, intercambiar, calibrar, regar, escribir bitácora de la huerta, moderar reportes | no | sí | sí |
| Configurar camas (zona del gateway, válvula, sensor), asignar cuidadores, editar biblioteca, reenviar umbrales | no | no | sí |

El front no debe adivinarlo: `GET /agrohubs/<ref>/permisos` devuelve los flags
(`cambiar_plan`, `regar`, `calibrar`, `escribir_bitacora`, `moderar_reportes`, `configurar_camas`,
`asignar_cuidadores`, `editar_biblioteca`, `es_cuidador`, `es_equipo`, `sesion`). Con eso se quita
el selector «Solo mirar / Cuido esta huerta» (HF03).

## 2. Endpoints

| Método y ruta | Acceso | Para qué (HU) |
|---|---|---|
| `GET /agrohubs/huertas` | público | Todas las huertas con sus camas (mapa y boletín) |
| `GET /agrohubs/<ref>/huerta` | público | Todo en una llamada: agrohub, permisos, plan, reportes, movimientos, recomendaciones, seguimiento |
| `GET /cultivos/` · `GET /cultivos/<id>` | público | Biblioteca (HB01) |
| `POST /cultivos/` · `PUT/PATCH /cultivos/<id>` · `GET /cultivos/<id>/cambios` | equipo | Editar la biblioteca con registro de cambios |
| `GET /agrohubs/<ref>/plan` | público | Plan de siembra (HB02) |
| `PUT /agrohubs/<ref>/plan/camas/<zona>` | cuidador | Sembrar, descanso, cosecha, fecha, calibración |
| `POST /agrohubs/<ref>/plan/intercambiar` | cuidador | `{"zonas": ["A","B"]}` |
| `POST /agrohubs/<ref>/plan/reenviar` | equipo | Reenviar todos los umbrales al gateway |
| `GET /agrohubs/<ref>/lecturas?desde=&hasta=` | público | Lecturas por cama cada 30 min (HB03) |
| `GET/POST /agrohubs/<ref>/reportes` | público | Reportes de la comunidad (HB04) |
| `PUT /agrohubs/<ref>/reportes/<id>/moderacion` | cuidador | `{"moderacion": "visible" \| "pendiente" \| "oculto"}` |
| `GET /agrohubs/<ref>/bitacora` | público / cuidador | Bitácora de la huerta (HB05) |
| `POST /user-activity/logbooks` con `agrohub_id` | cuidador | Escribir en la bitácora de la huerta |
| `GET /agrohubs/<ref>/movimientos` | público | «Lo que ha pasado» |
| `GET /agrohubs/<ref>/recomendaciones` | público | Reglas + propuestas de calibración (HB08) |
| `POST /agrohubs/<ref>/calibracion/aceptar` | cuidador | `{"zona": "A", "puntos": 3}` |
| `GET /agrohubs/<ref>/seguimiento` | público | Último seguimiento + `hay_novedades` (no llama al modelo) (HB06) |
| `POST /agrohubs/<ref>/seguimiento` | público | Genera solo si hay novedades |
| `POST /agrohubs/<ref>/camas/<zona>/regar` | cuidador | `{"accion": "abrir" \| "cerrar"}` |
| `GET /agrohubs/<ref>/permisos` | público | Qué mostrar (HB07) |
| `GET/POST /agrohubs/<ref>/cuidadores` · `DELETE …/cuidadores/<usuario_id>` | equipo | Asignar quién cuida |
| `GET/POST /agrohubs/<ref>/camas` · `PUT/DELETE …/camas/<zona>` | equipo | Configuración técnica de las camas |
| `GET /agrohubs/<ref>/sensores` | equipo | Sondas y válvulas que reporta el gateway, para armar las camas |

## 3. Formas de los datos

### Cultivo (`/cultivos`)
Los campos de `Cultivo` de `biblioteca.ts` **en snake_case** (`secar_al_final`, `calor_fuerte`,
`cosecha_dias`), más `fuentes` (de dónde sale cada número), `validado` (false hasta que AGROSAVIA
lo revise) y `updated_at`. `etapas: [{tipo, nombre, desde}]`. Los 18 de la demo ya están cargados
con los mismos `id` (`tomate`, `aji`…).

```json
{"id": "tomate", "nombre": "Tomate", "familia": "solanaceas", "forma": "mata", "fruto": "#d6453a",
 "sed": 1, "abrir": 30, "cerrar": 42, "kc": [0.6, 1.15, 0.8], "agotable": 0.4, "raiz": [0.7, 1.5],
 "secar_al_final": false, "optimo": [20, 27], "calor_fuerte": 34, "siembra": "trasplante",
 "etapas": [{"tipo": "inicio", "nombre": "Prende", "desde": 0}, …], "cosecha_dias": 45, "perenne": false,
 "distancia": "40 cm entre matas y 1 m entre surcos", "luz": "sol", "amigas": ["cilantro", …],
 "evitar": ["col", "maiz"], "plagas": […], "senal": "…", "consejo": "…",
 "fuentes": {"kc": "FAO-56, tabla 12", …}, "validado": false}
```

### Plan (`/plan`)
```json
{"agrohub": {"id": 24, "numero": "AH-002", "nombre": "Algarrobo Los Abuelos"},
 "envio_automatico": false,
 "camas": [{
   "zona": "A", "orden": 0, "libre": false, "cultivo_id": "tomate", "cultivo_nombre": "Tomate",
   "sembrado_el": "2026-11-05", "dias": 20, "edad": "3 semanas",
   "momento": {"dias": 20, "etapa": {"tipo": "crecimiento", "nombre": "Crece", "desde": 14}, "indice": 1,
               "avance": 0.286, "crecimiento": 0.55, "faltan": 60, "terminado": false},
   "cosechando": false, "cosechando_marcado": false, "ajuste": 0,
   "umbral": {"abrir": 30, "cerrar": 42, "sed": 0.761, "etapa": "crecimiento"},
   "anteriores": [{"cultivo_id": "aji", "sembrado_el": "2026-07-01", "hasta": "2026-11-05"}],
   "riego": {"conectada": true, "con_sensor": true,
             "ultimo_envio": {"resultado": "aplicada", "en": "…", "detalle": []}}
 }]}
```
- Equivale a `EraPlan` + `Era`: `sembrado_el` es fecha (`AAAA-MM-DD`); para `sembradoEl` en ms
  usar medianoche de Colombia (UTC−5).
- Con sesión de equipo cada cama trae además `tecnico: {gateway_zona, valvula, sensor, umbral_enviado}`.
- `momento`, `umbral`, `edad` salen de las mismas reglas que `biblioteca.ts`/`plan.ts` (porte
  verificado caso por caso contra el TypeScript).

### Cambiar una cama (`PUT /plan/camas/<zona>`), campos opcionales
| Campo | Efecto |
|---|---|
| `cultivo_id: "tomate"` (+ `sembrado_el`, por defecto hoy) | Sembrar o cambiar (lo anterior pasa a `anteriores`) |
| `cultivo_id: null` | Dejar en descanso |
| `sembrado_el: "2026-11-01"` | Corregir la fecha (no puede ser futura) |
| `cosechando: true` | «Ya está dando» |
| `ajuste: 3` | Calibración absoluta (±6; más allá → 422 «avisa al equipo técnico») |

La respuesta es el plan completo + `envio` + `movimientos_nuevos`. `envio.camas.<zona>.resultado`:

| resultado | Qué mostrar |
|---|---|
| `aplicada` | El gateway confirmó el nuevo umbral |
| `sin_respuesta` | **Pendiente**: el gateway no confirmó en 20 s (no es «aplicada»; se reintenta en la revisión diaria) |
| `rechazada` / `invalida` | El gateway no lo aceptó (`errores`) |
| `error` | No se pudo hablar con el broker |
| `desactivado` | El envío automático está apagado (`HUERTAS_ENVIAR_UMBRALES`): el plan se guardó, el gateway sigue con su umbral |
| `sin_gateway` | La cama no está conectada a una válvula |
| `descanso` / `sin_cambios` | Nada que mandar |

### Lecturas (`/lecturas`) — reemplazo de `simular()`
```json
{"agrohub_id": 24, "numero": "AH-002", "paso_minutos": 30, "desde": "…", "hasta": "…", "sin_gateway": false,
 "camas": [{"zona": "A", "con_sensor": true, "con_valvula": true}],
 "lecturas": [{"t": 1764021600000, "temperatura": 31.2, "humedadAire": 70.4, "temperaturaSuelo": 29.3,
               "enLinea": true, "eras": [{"zona": "A", "humedad": 21.5, "riego": true, "auto": true}]}]}
```
- Misma forma que `Lectura` (`simulacion.ts`), con `zona` en cada era.
- **Zona rural:** si la estación mandó datos hace menos de `tolerancia_minutos` (180 por
  defecto, `HUERTAS_TOLERANCIA_MINUTOS`), un paso sin lectura repite el último valor medido y sale
  `enLinea: true`, `relleno: true` y `minutosSinDato`. `ultimoDatoReal` (ms) dice cuándo llegó la
  última medición de verdad: úsalo para «Datos de hace…».
- **Pasada la tolerancia, sin dato es null**: `enLinea: false` y todo en null; cama sin sensor →
  `humedad: null`; sin eventos de válvula → `riego: null`. Nada se interpola.
- `desde`/`hasta`: ISO, `AAAA-MM-DD` o milisegundos. Por defecto los últimos 2 días; máximo 8.
- Caché de 60 s y 120 consultas/min por IP. Nunca salen `device_id`, sensores ni temas MQTT.

### Reporte (`POST /reportes`)
```json
{"zona": "A", "matas": "bonitas", "tierra": "seca", "plaga": "no", "riego_mano": "no", "cosecha": "no",
 "nota": "…", "autoria": "rol", "autor_rol": "Una vecina", "autor_nombre": ""}
```
- `zona` opcional (null = toda la huerta). `autoria`: `nombre` | `rol` | `anonimo` (CARE).
- Multipart con `foto` (≤ 5 MB): se guarda reducida y **sin metadatos** (quita la ubicación GPS).
- Header opcional `X-Dispositivo: <id propio del navegador>` para el límite por dispositivo
  (4/hora); por IP 12/hora → 429.
- Una nota con enlaces queda `moderacion: "pendiente"` hasta que alguien que cuida la publique.
- El backend anota `sensor` (estado de la tierra en ese momento: `seca`, `pidiendo`, `regando`,
  `bien`, `encharcada` o null): es la base de la calibración.
- En la lista: `{id, fecha (ms), autor, zona, matas, tierra, plaga, riegoMano, cosecha, nota, foto, sensor}`.

### Bitácora de la huerta
- Escribir: `POST /user-activity/logbooks` con `agrohub_id`, `activity_type`, `moon_phase` y
  `publica` (por defecto true). Requiere cuidar esa huerta.
- Leer: `GET /agrohubs/<ref>/bitacora` → `{id, title, description, activity_date, activity_type,
  moon_phase, autor (solo el primer nombre), publica, created_at (ms)}` = `Nota` de `cuaderno.ts`.
- De paso: la bitácora personal (`/bitacora`) ya **guarda** `activity_type` y `moon_phase`, que
  el front mandaba y el backend descartaba.

### Seguimiento
- `GET` → `{seguimiento | null, huella_actual, hay_novedades, se_puede_generar_desde}`.
  Mostrar «Hay novedades: actualizar» solo con `hay_novedades`.
- `POST` → 201 con `{seguimiento, nuevo: true}`; 200 si no había novedades; 429 si pasaron menos de
  6 h o se llegó al tope mensual (se devuelve el anterior en `data.seguimiento`); 503 sin llave.
- `seguimiento` = `Seguimiento` de `cuaderno.ts` (`resumen, vaBien, cuidar, pasos, pregunta,
  generadoEn (ms), modelo, reportes, notas`).
- El contexto lo arma el backend: el front ya no manda nada. Se puede borrar
  `app/api/huertas-abiertas/seguimiento/route.ts` (y la llave `GEM_API_CLA` del front).

### Recomendaciones
`[{id, nivel, titulo, texto, porque, accion?}]`; `accion` = `{tipo: "calibrar", zona, puntos,
ajuste_resultante}` | `{tipo: "liberar"|"cosechar", zona}` | `{tipo: "reportar"}`. Si una calibración
pasaría de ±6 no trae `accion` y sí `avisar_equipo: true`.

## 4. Configurar una huerta real (equipo técnico)

1. `GET /agrohubs/AH-002/sensores` → sondas (`sensor` = dev_eui, `equipo` = SE01-01…) y válvulas por zona.
2. `POST /agrohubs/AH-002/camas` por cada cama: `{"zona": "A", "gateway_zona": "z1", "valvula": "RO1", "sensor": "a840411dc861cc48"}`.
3. `POST /agrohubs/AH-002/cuidadores` `{"usuario_id": 31}`.
4. Quien cuida siembra desde la web. Mientras `HUERTAS_ENVIAR_UMBRALES=false` (por defecto) el
   gateway conserva sus umbrales; al activarlo, cada cambio del plan se envía y la revisión diaria
   (`huertas_revisar_etapas`, 5:30 a. m.) ajusta las camas que cambian de etapa.

## 5. Tareas programadas (cron del servidor)

| Cuándo | Comando |
|---|---|
| Todos los días 5:30 | `manage.py huertas_revisar_etapas` (sin envío si está desactivado) |
| Lunes 5:00 | `manage.py huertas_seguimiento_semanal` (solo huertas con novedades) |

## 6. Variables de entorno

| Variable | Por defecto | Uso |
|---|---|---|
| `HUERTAS_ENVIAR_UMBRALES` | `false` | Mandar al gateway los umbrales del plan |
| `HUERTAS_LLM_PROVEEDOR` | (openai si hay `OPENAI_API_KEY`) | `openai` o `gemini` |
| `HUERTAS_LLM_MODELO` | `gpt-4o-mini` / `gemini-2.5-flash` | Modelo del seguimiento |
| `HUERTAS_LLM_TOPE_USD_MES` | `5` | Tope de gasto mensual |
