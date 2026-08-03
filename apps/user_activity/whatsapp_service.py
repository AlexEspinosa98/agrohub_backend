from typing import Optional

import requests as http_requests
from django.db.models import Q

from apps.user_activity.models import User

WA_API_URL = "https://graph.facebook.com/v19.0"
WA_NO_USER_MSG = (
    "No encontré tu número registrado en AgroHub. "
    "Por favor regístrate primero en la aplicación para poder usar el asistente."
)
WA_NO_TEXT_MSG = (
    "Solo puedo procesar mensajes de texto por ahora. "
    "Escríbeme qué actividad deseas registrar."
)


def send_whatsapp_message(phone_number_id: str, token: str, to: str, text: str) -> None:
    url = f"{WA_API_URL}/{phone_number_id}/messages"
    http_requests.post(
        url,
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )


def _find_by_phone_or_identification(value: str) -> Optional[User]:
    return User.objects.filter(
        Q(phone=value) | Q(identification=value) | Q(email=value)
    ).first()


def find_user_by_wa_phone(wa_phone: str) -> Optional[User]:
    """WhatsApp envía el número con código de país (ej: 573001234567).
    Intenta coincidencia exacta y luego sin el prefijo 57 de Colombia."""
    user = _find_by_phone_or_identification(wa_phone)
    if user:
        return user
    if wa_phone.startswith("57") and len(wa_phone) > 10:
        return _find_by_phone_or_identification(wa_phone[2:])
    return None


def extract_wa_payload(body: dict):
    """Extrae (wa_phone, text, phone_number_id) del payload de Meta. Retorna Nones si no aplica."""
    try:
        change_value = body["entry"][0]["changes"][0]["value"]
        phone_number_id = change_value["metadata"]["phone_number_id"]
        messages = change_value.get("messages")
        if not messages:
            return None, None, None
        msg = messages[0]
        wa_phone = msg["from"]
        text = msg["text"]["body"] if msg.get("type") == "text" else None
        return wa_phone, text, phone_number_id
    except (KeyError, IndexError):
        return None, None, None
