from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.user_activity.models import Session


class AnonymousUser:
    """Stand-in for DRF's REST_FRAMEWORK['UNAUTHENTICATED_USER'] — our User
    model isn't django.contrib.auth based, so we need our own anonymous type."""

    is_authenticated = False
    role = None
    id = None


class TokenHeaderAuthentication(BaseAuthentication):
    """`Authorization: Token <token>` — the same opaque token scheme the
    FastAPI backend used (not DRF's built-in TokenAuthentication app/table).
    Tokens live in the `Session` table (one row per user+platform), so the
    same account can hold a separate app token and web token at once.
    Malformed/missing headers are left for permission classes to reject so
    the 401/403 split matches the original behavior; an unrecognized token
    fails fast here with 401."""

    keyword = "token"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header or not auth_header.lower().startswith(f"{self.keyword} "):
            return None
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None
        session = Session.objects.select_related("user").filter(token=token).first()
        if not session:
            raise AuthenticationFailed("Token inválido")
        Session.objects.filter(pk=session.pk).update(last_used_at=timezone.now())
        return (session.user, token)

    def authenticate_header(self, request):
        return "Token"
