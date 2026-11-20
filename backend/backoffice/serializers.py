"""Valida la configuración administrativa y sus reglas monetarias."""

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
    """Presenta un evento auditable con la identidad legible del responsable."""

    responsable = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de EventoTrazabilidad y protege sus campos de solo lectura."""

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
        """Devuelve identificador, correo y rol del responsable de evento, o None si falta."""
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
    """Valida filtros opcionales usados para consultar la trazabilidad."""

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
    """Expone un parámetro vigente junto con su responsable administrativo."""

    responsable_actualizacion = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de ParametroSistema y protege sus campos de solo lectura."""

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
        """Devuelve identificador, correo y rol de quien actualizó parametro, o None si falta."""
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
    """Serializa una modificación histórica sin permitir su escritura."""

    responsable_skilly = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de HistorialParametro y protege sus campos de solo lectura."""

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
        """Devuelve identificador, correo y rol del responsable de historial, o None si falta."""
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
    """Valida el nuevo porcentaje de comisión antes de actualizarlo."""

    valor_nuevo = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
