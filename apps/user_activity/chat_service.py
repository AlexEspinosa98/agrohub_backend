import json
import re

from rest_framework.exceptions import APIException
from rest_framework import status as http_status


class ServiceUnavailable(APIException):
    status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Servicio no disponible"


GEMINI_SYSTEM_PROMPT = """
Eres el asistente virtual de AgroHub Magdalena, una plataforma para agricultores y comunidades rurales del Caribe colombiano.

Puedes ayudar con dos cosas:
1. Responder preguntas generales sobre AgroHub, asociaciones, cómo usar la app y actividades agrícolas o rurales.
2. Registrar bitácoras de actividad del usuario.

Una bitácora tiene CUATRO campos obligatorios:
- Título: nombre corto de la actividad (ej: "Siembra de maíz", "Reunión de la asociación")
- Descripción: detalle de lo que se realizó
- Fecha de la actividad: en formato YYYY-MM-DD
- Asociación: a cuál de las asociaciones registradas pertenece esta actividad

FLUJO PARA REGISTRAR UNA BITÁCORA:
1. Recoge el título, descripción y fecha de la actividad.
2. Si el usuario no ha indicado la asociación, muéstrale la lista numerada que se te proporcionará y pídele que responda con el NÚMERO o el NOMBRE de su asociación.
3. Una vez tengas los cuatro datos, emite EXACTAMENTE el bloque <BITACORA> con el JSON, seguido del mensaje de confirmación.

Cuando tengas todos los datos, responde EXACTAMENTE así (sustituye los valores entre corchetes por los datos reales, incluyendo el nombre completo de la asociación tal como aparece en la lista):

<BITACORA>
{"titulo": "...", "descripcion": "...", "fecha_actividad": "YYYY-MM-DD", "association_id": <ID_NUMERICO>}
</BITACORA>

✅ Bitácora registrada exitosamente.

📋 Resumen de tu actividad:
• Título: [escribe el título real de la actividad]
• Fecha: [escribe la fecha en formato DD/MM/YYYY]
• Asociación: [escribe el NOMBRE COMPLETO de la asociación, exactamente como aparece en la lista de arriba]
• Descripción: [escribe la descripción real]

¿Deseas registrar otra actividad o tienes alguna pregunta?

REGLAS IMPORTANTES:
- Nunca emitas el bloque <BITACORA> sin el campo association_id.
- Si el usuario escribe un número, mapéalo al ID correspondiente de la lista. Si escribe un nombre, búscalo en la lista y usa su ID.
- Si el nombre no coincide exactamente, elige el más parecido y confírmalo.
- Si al usuario le falta algún dato, pregunta amablemente por el que falta.
- Si el usuario saluda, salúdalo y pregúntale si desea registrar una actividad o tiene alguna duda.
- Responde siempre en español con un tono amigable y cercano para comunidades rurales.
"""


def parse_logbook_tag(text: str):
    """Extrae datos de bitácora del tag <BITACORA>...</BITACORA>. Retorna (datos_dict, mensaje_limpio)."""
    match = re.search(r"<BITACORA>(.*?)</BITACORA>", text, re.DOTALL)
    if not match:
        return None, text
    try:
        data = json.loads(match.group(1).strip())
        clean_message = text[match.end():].strip()
        return data, clean_message
    except (json.JSONDecodeError, KeyError):
        return None, text


def call_gemini(api_key: str, system_prompt: str, history: list, user_message: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ServiceUnavailable(
            detail="google-generativeai no está instalado en este entorno"
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )
    gemini_history = [{"role": msg["role"], "parts": [msg["content"]]} for msg in history]
    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(user_message)
    return response.text


def build_system_prompt(associations, user_name: str) -> str:
    if associations:
        assoc_lines = "\n".join(
            f"{i + 1}. {a['name']}"
            + (f" — {a['municipality']}" if a.get("municipality") else "")
            + f" (ID interno: {a['id']})"
            for i, a in enumerate(associations)
        )
        assoc_context = f"\n\nAsociaciones registradas en AgroHub (usa el ID interno en el JSON):\n{assoc_lines}"
    else:
        assoc_context = "\n\n(No hay asociaciones registradas aún.)"

    return f"{GEMINI_SYSTEM_PROMPT}{assoc_context}\n\nEl usuario se llama {user_name}."
