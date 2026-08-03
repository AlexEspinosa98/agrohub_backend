from django.conf import settings
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


class IsAuthenticatedWithRole(BasePermission):
    """Requires a valid token AND an assigned role — mirrors
    modules/user_activity/infrastructure/auth.py::get_current_user."""

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            raise NotAuthenticated("Falta header Authorization: Token <token>")
        if not request.user.role:
            raise PermissionDenied(
                "Tu cuenta aún no tiene un rol asignado. Contacta a un superadmin."
            )
        return True


class IsAdminRole(BasePermission):
    message = "Requiere rol admin"

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in ("admin", "superadmin")


class IsSuperadminRole(BasePermission):
    message = "Requiere rol superadmin"

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "superadmin"


class HasSuperadminServerToken(BasePermission):
    """Gate for bootstrapping the first superadmin — checked against the
    X-Superadmin-Token header, not a user session."""

    message = "Token de superadmin inválido"

    def has_permission(self, request, view):
        expected = settings.SUPERADMIN_TOKEN
        token = request.META.get("HTTP_X_SUPERADMIN_TOKEN")
        return bool(expected) and token == expected
