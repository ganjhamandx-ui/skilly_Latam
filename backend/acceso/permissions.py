"""Expone permisos reutilizables basados en los roles de la sesión activa."""

from rest_framework.permissions import BasePermission


class EsUsuarioSkillyAutenticado(BasePermission):
    """Autoriza únicamente identidades activas autenticadas por la sesión de SKILLY."""

    message = "Debe iniciar sesión para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return getattr(usuario, "estado", None) == "ACTIVO"


class EsProfesional(BasePermission):
    """Restringe el recurso a una identidad activa con rol profesional."""

    message = "No tiene permisos para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return (
            getattr(usuario, "estado", None) == "ACTIVO"
            and getattr(usuario, "rol", None) == "PROFESIONAL"
        )


class EsAdministracionSkilly(BasePermission):
    """Restringe el recurso al personal activo de administración SKILLY."""

    message = "No tiene permisos para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return (
            getattr(usuario, "estado", None) == "ACTIVO"
            and getattr(usuario, "rol", None) == "ADMIN_SKILLY"
        )
