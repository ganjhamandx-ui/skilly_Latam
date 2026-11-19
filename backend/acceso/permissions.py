"""Expone permisos reutilizables basados en los roles de la sesión activa."""

from rest_framework.permissions import BasePermission


class EsUsuarioSkillyAutenticado(BasePermission):
    """Autoriza únicamente identidades activas autenticadas por la sesión de SKILLY."""

    message = "Debe iniciar sesión para acceder a este recurso."

    def has_permission(self, request, view):
        """Comprueba el estado de la identidad resuelta por autenticación.

        Args:
            request (Request): Petición cuyo ``user`` puede estar ausente.
            view (APIView): Vista evaluada por DRF; no interviene en la regla.

        Returns:
            bool: Si el usuario existe y su estado es ``ACTIVO``.
        """
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return getattr(usuario, "estado", None) == "ACTIVO"


class EsProfesional(BasePermission):
    """Restringe el recurso a una identidad activa con rol profesional."""

    message = "No tiene permisos para acceder a este recurso."

    def has_permission(self, request, view):
        """Exige una identidad activa con rol ``PROFESIONAL``.

        Args:
            request (Request): Petición con la identidad autenticada.
            view (APIView): Vista evaluada; no modifica el permiso.

        Returns:
            bool: Si se cumplen simultáneamente el estado y el rol exigidos.
        """
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
        """Exige una identidad activa con rol ``ADMIN_SKILLY``.

        Args:
            request (Request): Petición con la identidad autenticada.
            view (APIView): Vista evaluada; no modifica el permiso.

        Returns:
            bool: Si el usuario puede acceder al recurso administrativo.
        """
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return (
            getattr(usuario, "estado", None) == "ACTIVO"
            and getattr(usuario, "rol", None) == "ADMIN_SKILLY"
        )
