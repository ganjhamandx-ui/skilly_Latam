"""Define la autenticación de sesión con protección CSRF para la API."""

from rest_framework.authentication import SessionAuthentication

from .models import Usuario
from .sesiones import _sesion_contrasena_vigente


class SesionSkillyAuthentication(SessionAuthentication):
    """Autentica la sesión propia de SKILLY y exige un usuario activo y vigente."""

    def authenticate(self, request):
        """Resuelve la identidad activa y valida CSRF antes de autenticarla.

        Args:
            request (Request): Petición DRF con la sesión de Django.

        Returns:
            tuple[Usuario, None] | None: Usuario y credencial vacía cuando la
            sesión es válida; ``None`` si no hay identidad autenticable. Una
            identidad inexistente, inactiva o con contraseña cambiada provoca
            además el vaciado de la sesión.

        Raises:
            PermissionDenied: Si la comprobación CSRF heredada de DRF rechaza
                una petición que requiere protección.
        """
        id_usuario = request.session.get("id_usuario")

        if not id_usuario:
            return None

        usuario = Usuario.objects.filter(
            id_usuario=id_usuario,
            estado="ACTIVO",
        ).first()

        if usuario is None or not _sesion_contrasena_vigente(request.session, usuario):
            request.session.flush()
            return None

        self.enforce_csrf(request)

        return (usuario, None)
