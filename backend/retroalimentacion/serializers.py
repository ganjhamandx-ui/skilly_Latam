"""Valida y representa evaluaciones y recomendaciones de servicio."""

from rest_framework import serializers

from .models import (
    RecomendacionDesarrollo,
    Retroalimentacion,
)


class RetroalimentacionSerializer(
    serializers.ModelSerializer
):
    """Serializa la retroalimentación visible para su organización propietaria."""

    class Meta:
        """Define la representación de Retroalimentacion y protege sus campos de solo lectura."""

        model = Retroalimentacion

        fields = [
            "id_feedback",
            "id_prestacion",
            "contenido",
            "visibilidad",
            "estado",
            "fecha_registro",
        ]

        read_only_fields = fields


class RetroalimentacionAdministracionSerializer(
    serializers.ModelSerializer
):
    """Añade a la retroalimentación los datos requeridos por administración."""

    class Meta:
        """Define la representación de Retroalimentacion y protege sus campos de solo lectura."""

        model = Retroalimentacion

        fields = [
            "id_feedback",
            "id_prestacion",
            "id_contacto",
            "contenido",
            "visibilidad",
            "estado",
            "fecha_registro",
        ]

        read_only_fields = fields


class RegistrarRetroalimentacionSerializer(
    serializers.Serializer
):
    """Valida calificación y comentario antes de registrar una evaluación."""

    contenido = serializers.CharField(
        trim_whitespace=True
    )


class RecomendacionDesarrolloSerializer(
    serializers.ModelSerializer
):
    """Representa recomendaciones en las vistas administrativas."""

    class Meta:
        """Define la representación de RecomendacionDesarrollo y protege sus campos de solo lectura."""

        model = RecomendacionDesarrollo

        fields = [
            "id_recomendacion",
            "id_profesional",
            "id_feedback",
            "id_usuario_skilly",
            "titulo",
            "descripcion",
            "estado",
            "fecha_creacion",
            "fecha_comunicacion",
        ]

        read_only_fields = fields


class RegistrarRecomendacionDesarrolloSerializer(
    serializers.Serializer
):
    """Valida el contenido de una recomendación creada por administración."""

    titulo = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        trim_whitespace=True
    )


class RecomendacionDesarrolloProfesionalSerializer(
    serializers.ModelSerializer
):
    """Limita la recomendación a los campos comunicados al profesional."""

    class Meta:
        """Define la representación de RecomendacionDesarrollo y protege sus campos de solo lectura."""

        model = RecomendacionDesarrollo

        fields = [
            "id_recomendacion",
            "titulo",
            "descripcion",
            "estado",
            "fecha_comunicacion",
        ]

        read_only_fields = fields
