"""Construye la respuesta segura que describe la sesión autenticada actual."""

from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SesionSkillyAuthentication
from .permissions import EsUsuarioSkillyAutenticado


class SesionActualView(APIView):
    """Devuelve la identidad activa asociada a la sesión autenticada."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsUsuarioSkillyAutenticado]

    def get(self, request):
        """Entrega los identificadores públicos de la sesión autenticada.

        Args:
            request (Request): Petición autorizada para un usuario activo.

        Returns:
            Response: HTTP 200 con identificador, correo y rol del usuario.
            La autenticación y el permiso rechazan el acceso antes del método
            si no existe una sesión válida; no se exponen hashes ni tokens.
        """
        usuario = request.user
        return Response({
            "usuario": {
                "id_usuario": usuario.id_usuario,
                "correo": usuario.correo,
                "rol": usuario.rol,
            }
        })
