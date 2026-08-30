from django.conf import settings
from rest_framework.permissions import BasePermission


class TieneApiKeyRiego(BasePermission):
    """Header X-API-Key — misma credencial única para el puñado de operadores internos que
    administran gateways, no pensada para usuarios finales (ver apps.user_activity para el
    esquema de usuarios "de verdad" del resto del proyecto, deliberadamente no reusado aquí:
    este es un panel de operación de infraestructura, no una cuenta de encuestador)."""
    message = "API key inválida o ausente (header X-API-Key)."

    def has_permission(self, request, view):
        api_key = getattr(settings, "RIEGO_IOT_API_KEY", None)
        return bool(api_key) and request.META.get("HTTP_X_API_KEY") == api_key
