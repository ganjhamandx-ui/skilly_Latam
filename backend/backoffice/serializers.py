from decimal import Decimal

from rest_framework import serializers

from .models import (
    EventoTrazabilidad,
    HistorialParametro,
    ParametroSistema,
)


class EventoTrazabilidadSerializer(
    serializers.ModelSerializer
):
    responsable = serializers.SerializerMethodField()

    class Meta:
        model = EventoTrazabilidad

        fields = [
            "id_evento",
            "responsable",
            "entidad_tipo",
            "entidad_id",
            "accion",
            "detalle_resumido",
            "fecha_evento",
        ]

        read_only_fields = fields

    def get_responsable(
        self,
        evento,
    ):
        usuario = evento.id_usuario

        if usuario is None:
            return None

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class FiltroTrazabilidadSerializer(
    serializers.Serializer
):
    entidad_tipo = serializers.CharField(
        max_length=60,
        required=False,
        allow_blank=False,
    )

    entidad_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    accion = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=False,
    )


class ParametroSistemaSerializer(
    serializers.ModelSerializer
):
    responsable_actualizacion = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = ParametroSistema

        fields = [
            "id_parametro",
            "clave",
            "valor_actual",
            "tipo_dato",
            "descripcion",
            "responsable_actualizacion",
            "fecha_actualizacion",
        ]

        read_only_fields = fields

    def get_responsable_actualizacion(
        self,
        parametro,
    ):
        usuario = parametro.id_usuario_actualiza

        if usuario is None:
            return None

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class HistorialParametroSerializer(
    serializers.ModelSerializer
):
    responsable_skilly = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = HistorialParametro

        fields = [
            "id_historial_parametro",
            "id_parametro",
            "valor_anterior",
            "valor_nuevo",
            "responsable_skilly",
            "fecha_cambio",
        ]

        read_only_fields = fields

    def get_responsable_skilly(
        self,
        historial,
    ):
        usuario = historial.id_usuario_skilly

        if usuario is None:
            return None

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ActualizarComisionSerializer(
    serializers.Serializer
):
    valor_nuevo = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )