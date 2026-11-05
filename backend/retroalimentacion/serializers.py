from rest_framework import serializers

from .models import (
    RecomendacionDesarrollo,
    Retroalimentacion,
)


class RetroalimentacionSerializer(
    serializers.ModelSerializer
):
    class Meta:
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
    class Meta:
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
    contenido = serializers.CharField(
        trim_whitespace=True
    )


class RecomendacionDesarrolloSerializer(
    serializers.ModelSerializer
):
    class Meta:
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
    class Meta:
        model = RecomendacionDesarrollo

        fields = [
            "id_recomendacion",
            "titulo",
            "descripcion",
            "estado",
            "fecha_comunicacion",
        ]

        read_only_fields = fields