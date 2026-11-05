from rest_framework.permissions import BasePermission


class EsUsuarioSkillyAutenticado(BasePermission):
    message = "Debe iniciar sesión para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return getattr(usuario, "estado", None) == "ACTIVO"


class EsProfesional(BasePermission):
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
    message = "No tiene permisos para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)

        if usuario is None:
            return False

        return (
            getattr(usuario, "estado", None) == "ACTIVO"
            and getattr(usuario, "rol", None) == "ADMIN_SKILLY"
        )