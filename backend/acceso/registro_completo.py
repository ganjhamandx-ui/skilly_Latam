
"""Coordina el registro transaccional de una cuenta y su perfil profesional."""

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from acceso.serializers import RegistroProfesionalSerializer
from profesionales.models import Profesional


class RegistroProfesionalCompletoSerializer(
    RegistroProfesionalSerializer
):
    """Crea cuenta y perfil profesional en una sola transacción consistente."""

    nombres = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
    )

    apellidos = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
    )

    telefono = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=30,
    )

    titulo_profesional = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
    )

    resumen = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    ubicacion = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
    )

    @transaction.atomic
    def create(self, validated_data):
        datos = dict(validated_data)

        perfil = {
            "nombres": datos.pop("nombres").strip(),
            "apellidos": datos.pop("apellidos").strip(),
            "telefono": datos.pop("telefono", "").strip() or None,
            "titulo_profesional": (
                datos.pop("titulo_profesional", "").strip() or None
            ),
            "resumen": datos.pop("resumen", "").strip() or None,
            "ubicacion": datos.pop("ubicacion", "").strip() or None,
        }

        usuario = super().create(datos)

        Profesional.objects.create(
            id_usuario=usuario,
            nombres=perfil["nombres"],
            apellidos=perfil["apellidos"],
            telefono=perfil["telefono"],
            titulo_profesional=perfil["titulo_profesional"],
            resumen=perfil["resumen"],
            ubicacion=perfil["ubicacion"],
            estado_validacion="PENDIENTE",
            fecha_registro=timezone.now(),
        )

        return usuario
