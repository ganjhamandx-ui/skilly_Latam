"""Implementa los endpoints de registro, autenticación y cuenta de usuario."""

from acceso.registro_completo import RegistroProfesionalCompletoSerializer
from django.middleware.csrf import get_token, rotate_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SesionSkillyAuthentication
from .sesiones import _vincular_sesion_con_contrasena
from .intentos import ProteccionIntentosMixin
from .models import Usuario
from .permissions import EsUsuarioSkillyAutenticado
from .recuperacion import (
    crear_recuperacion_acceso,
    restablecer_contrasena,
)
from .serializers import (
    InicioSesionSerializer,
    RegistroProfesionalSerializer,
    RestablecerContrasenaSerializer,
    SolicitarRecuperacionSerializer,
)
import logging
from smtplib import SMTPException
from django.db import transaction
from .recuperacion import enviar_correo_recuperacion


class CsrfTokenView(APIView):
    """Entrega el token CSRF inicial sin desactivar la protección de escrituras."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = get_token(request)

        return Response(
            {
                "csrfToken": token,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class RegistroProfesionalView(APIView):
    """Registra una cuenta profesional y establece su sesión autenticada."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegistroProfesionalCompletoSerializer(
            data=request.data
        )

        if serializer.is_valid():
            usuario = serializer.save()

            return Response(
                {
                    "mensaje": (
                        "Cuenta profesional creada correctamente."
                    ),
                    "usuario": {
                        "id_usuario": usuario.id_usuario,
                        "correo": usuario.correo,
                        "rol": usuario.rol,
                        "estado": usuario.estado,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(csrf_protect, name="dispatch")
class InicioSesionView(ProteccionIntentosMixin, APIView):
    """Inicia sesión con limitación por origen e identidad y rota la clave de sesión."""

    alcance_intentos = "iniciar_sesion"
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = InicioSesionSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = serializer.validated_data["usuario"]

        request.session.cycle_key()

        request.session["id_usuario"] = (
            usuario.id_usuario
        )

        request.session["rol"] = usuario.rol

        _vincular_sesion_con_contrasena(request.session, usuario)

        rotate_token(request)

        return Response(
            {
                "mensaje": (
                    "Inicio de sesión correcto."
                ),
                "usuario": {
                    "id_usuario": usuario.id_usuario,
                    "correo": usuario.correo,
                    "rol": usuario.rol,
                },
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class SolicitarRecuperacionView(ProteccionIntentosMixin, APIView):
    """Solicita recuperación con respuesta uniforme para evitar enumerar cuentas."""

    alcance_intentos = "recuperar"
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SolicitarRecuperacionSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        correo = serializer.validated_data["correo"]

        usuario = Usuario.objects.filter(
            correo__iexact=correo,
            estado="ACTIVO",
        ).first()

        if usuario is not None:
            try:
                with transaction.atomic():
                    token, recuperacion = crear_recuperacion_acceso(
                        usuario
                    )

                    enviados = enviar_correo_recuperacion(
                        usuario,
                        token,
                    )

                    if enviados != 1:
                        raise SMTPException(
                            "No se pudo enviar el correo."
                        )

            except (SMTPException, OSError):
                # La respuesta SMTP puede contener datos de la cuenta o del
                # mensaje. Registrar solo el evento, sin excepción ni traceback.
                logging.getLogger(__name__).warning(
                    "Fallo el envio del correo de recuperacion."
                )

        return Response(
            {
                "mensaje": (
                    "Si existe una cuenta disponible para "
                    "recuperación, se iniciará el mecanismo "
                    "correspondiente."
                ),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class RestablecerContrasenaView(ProteccionIntentosMixin, APIView):
    """Valida y consume el token antes de sustituir la contraseña del usuario."""

    alcance_intentos = "restablecer"
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RestablecerContrasenaSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data["token"]

        nueva_contrasena = (
            serializer.validated_data[
                "nueva_contrasena"
            ]
        )

        correcto, resultado = (
            restablecer_contrasena(
                token,
                nueva_contrasena,
            )
        )

        if not correcto:
            return Response(
                {
                    "mensaje": (
                        "El mecanismo de recuperación "
                        "no es válido o ya no está "
                        "disponible."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "mensaje": (
                    "Contraseña actualizada correctamente."
                ),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class CerrarSesionView(APIView):
    """Invalida la sesión autenticada y elimina su cookie del cliente."""

    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsUsuarioSkillyAutenticado
    ]

    def post(self, request):
        request.session.flush()
        rotate_token(request)

        return Response(
            {
                "mensaje": (
                    "Sesión cerrada correctamente."
                ),
            },
            status=status.HTTP_200_OK,
        )
