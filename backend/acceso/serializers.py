"""Valida credenciales, registro y cambios de acceso expuestos por la API."""

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import serializers

from .models import Usuario


class RegistroProfesionalSerializer(serializers.Serializer):
    """Valida correo y contraseña antes de crear una identidad profesional única."""

    correo = serializers.EmailField(max_length=150)

    contrasena = serializers.CharField(
        write_only=True,
        min_length=15,
        max_length=128,
    )

    confirmar_contrasena = serializers.CharField(
        write_only=True,
        min_length=15,
        max_length=128,
    )

    def validate_correo(self, value):
        """Normaliza el correo y comprueba duplicados sin distinguir mayúsculas.

        Args:
            value (str): Correo previamente validado por ``EmailField``.

        Returns:
            str: Correo sin espacios exteriores y en minúsculas.

        Raises:
            serializers.ValidationError: Si ya existe una cuenta con ese correo.
        """
        correo = value.strip().lower()

        if Usuario.objects.filter(
            correo__iexact=correo
        ).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta registrada con este correo."
            )

        return correo

    def validate(self, data):
        """Comprueba confirmación y validadores de contraseña de Django.

        Args:
            data (dict): Campos válidos del registro, incluidas ambas contraseñas.

        Returns:
            dict: Los datos originales si las contraseñas coinciden y son válidas.

        Raises:
            serializers.ValidationError: Si falla la confirmación o la política
                configurada; el error se asocia al campo correspondiente.
        """
        contrasena = data["contrasena"]
        confirmar_contrasena = data[
            "confirmar_contrasena"
        ]

        if contrasena != confirmar_contrasena:
            raise serializers.ValidationError(
                {
                    "confirmar_contrasena": (
                        "Las contraseñas no coinciden."
                    )
                }
            )

        try:
            validate_password(contrasena)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "contrasena": list(
                        error.messages
                    )
                }
            )

        return data

    def create(self, validated_data):
        """Guarda una cuenta profesional activa con contraseña cifrada por hash.

        Args:
            validated_data (dict): Correo normalizado y contraseña ya validados.

        Returns:
            Usuario: Identidad creada, sin crear perfil ni iniciar sesión.

        Raises:
            serializers.ValidationError: Si un registro concurrente ocupa el correo.
            IntegrityError: Si falla otra restricción de persistencia.
        """
        ahora = timezone.now()

        try:
            # La validación previa no serializa registros concurrentes. El
            # savepoint permite consultar el conflicto sin romper la transacción
            # exterior que crea conjuntamente la cuenta y su perfil.
            with transaction.atomic():
                usuario = Usuario.objects.create(
                    correo=validated_data["correo"],
                    password_hash=make_password(
                        validated_data["contrasena"]
                    ),
                    rol="PROFESIONAL",
                    estado="ACTIVO",
                    fecha_creacion=ahora,
                    fecha_actualizacion=ahora,
                )
        except IntegrityError:
            if Usuario.objects.filter(
                correo__iexact=validated_data["correo"]
            ).exists():
                raise serializers.ValidationError({
                    "correo": ["Ya existe una cuenta registrada con este correo."]
                }) from None
            raise

        return usuario


class InicioSesionSerializer(serializers.Serializer):
    """Autentica sin revelar si una cuenta existe, está inactiva o usa otra clave."""

    correo = serializers.EmailField(
        max_length=150
    )

    contrasena = serializers.CharField(
        write_only=True,
        max_length=128,
    )

    def validate(self, data):
        """Verifica contraseña y estado activo con un error común de credenciales.

        Args:
            data (dict): Correo y contraseña validados por los campos de DRF.

        Returns:
            dict: Los mismos datos con correo normalizado y ``usuario`` resuelto.

        Raises:
            serializers.ValidationError: Si no existe la cuenta, la contraseña
                no coincide o el estado no es ``ACTIVO``.
        """
        correo = data["correo"].strip().lower()
        contrasena = data["contrasena"]

        usuario = Usuario.objects.filter(
            correo__iexact=correo
        ).first()

        if usuario is None:
            # Mismo trabajo de hash que una clave fallida con el algoritmo
            # actual; no revelar la ausencia de la cuenta por omitir ese coste.
            make_password(contrasena)
            raise serializers.ValidationError(
                "Credenciales inválidas o cuenta no disponible."
            )

        if not check_password(
            contrasena,
            usuario.password_hash,
        ):
            raise serializers.ValidationError(
                "Credenciales inválidas o cuenta no disponible."
            )

        if usuario.estado != "ACTIVO":
            raise serializers.ValidationError(
                "Credenciales inválidas o cuenta no disponible."
            )

        data["correo"] = correo
        data["usuario"] = usuario

        return data


class SolicitarRecuperacionSerializer(
    serializers.Serializer
):
    """Normaliza el correo utilizado para solicitar recuperación de acceso."""

    correo = serializers.EmailField(
        max_length=150
    )

    def validate_correo(self, value):
        """Devuelve el correo sin espacios exteriores y en minúsculas.

        Args:
            value (str): Correo cuya sintaxis ya validó DRF.

        Returns:
            str: Dirección normalizada sin consultar la existencia de la cuenta.
        """
        return value.strip().lower()


class RestablecerContrasenaSerializer(
    serializers.Serializer
):
    """Valida token, confirmación y política de la nueva contraseña."""

    token = serializers.CharField(
        write_only=True,
        max_length=255,
    )

    nueva_contrasena = serializers.CharField(
        write_only=True,
        min_length=15,
        max_length=128,
    )

    confirmar_contrasena = serializers.CharField(
        write_only=True,
        min_length=15,
        max_length=128,
    )

    def validate(self, data):
        """Comprueba la nueva contraseña sin consumir ni verificar el token.

        Args:
            data (dict): Token, nueva contraseña y confirmación validados por DRF.

        Returns:
            dict: Datos originales si coinciden las contraseñas y cumplen la política.

        Raises:
            serializers.ValidationError: Si la confirmación difiere o Django
                rechaza la nueva contraseña.
        """
        nueva_contrasena = data[
            "nueva_contrasena"
        ]

        confirmar_contrasena = data[
            "confirmar_contrasena"
        ]

        if (
            nueva_contrasena
            != confirmar_contrasena
        ):
            raise serializers.ValidationError(
                {
                    "confirmar_contrasena": (
                        "Las contraseñas no coinciden."
                    )
                }
            )

        try:
            validate_password(
                nueva_contrasena
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "nueva_contrasena": list(
                        error.messages
                    )
                }
            )

        return data
