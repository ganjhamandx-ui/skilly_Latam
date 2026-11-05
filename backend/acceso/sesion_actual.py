from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SesionSkillyAuthentication
from .permissions import EsUsuarioSkillyAutenticado


class SesionActualView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsUsuarioSkillyAutenticado]

    def get(self, request):
        usuario = request.user
        return Response({
            "usuario": {
                "id_usuario": usuario.id_usuario,
                "correo": usuario.correo,
                "rol": usuario.rol,
            }
        })
