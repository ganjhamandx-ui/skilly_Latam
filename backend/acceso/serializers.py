from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import serializers

from .models import Usuario


class RegistroProfesionalSerializer(serializers.Serializer):
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
        correo = value.strip().lower()

        if Usuario.objects.filter(
            correo__iexact=correo
        ).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta registrada con este correo."
            )

        return correo

    def validate(self, data):
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
    correo = serializers.EmailField(
        max_length=150
    )

    contrasena = serializers.CharField(
        write_only=True,
        max_length=128,
    )

    def validate(self, data):
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
    correo = serializers.EmailField(
        max_length=150
    )

    def validate_correo(self, value):
        return value.strip().lower()


class RestablecerContrasenaSerializer(
    serializers.Serializer
):
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
