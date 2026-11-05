from rest_framework.authentication import BaseAuthentication

from .models import Usuario


class SesionSkillyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        id_usuario = request.session.get("id_usuario")

        if not id_usuario:
            return None

        usuario = Usuario.objects.filter(
            id_usuario=id_usuario,
            estado="ACTIVO",
        ).first()

        if usuario is None:
            request.session.flush()
            return None

        return (usuario, None)