"""Valida y representa los recursos expuestos por la API de pagos."""

from rest_framework import serializers
from pathlib import Path

MAX_COMPROBANTE_BYTES = 5 * 1024 * 1024



from .models import (
    HistorialEstadoPago,
    Pago,
    ReversaPago,
)


class PagoEstadoComunicableSerializer(
    serializers.ModelSerializer
):
    class Meta:
        """Define la representación de Pago y protege sus campos de solo lectura."""

        model = Pago

        fields = [
            "id_pago",
            "id_prestacion",
            "monto_total",
            "moneda",
            "estado_pago",
            "fecha_pago",
            "fecha_retencion",
            "fecha_liberacion",
        ]

        read_only_fields = fields


class PagoResumenProfesionalSerializer(PagoEstadoComunicableSerializer):
    """Desglose historico de un pago accesible solo al profesional asociado."""

    class Meta(PagoEstadoComunicableSerializer.Meta):
        """Delimita los campos que procesa `PagoResumenProfesionalSerializer`."""

        fields = PagoEstadoComunicableSerializer.Meta.fields + [
            "porcentaje_comision_aplicado",
            "monto_comision",
            "monto_neto_profesional",
        ]
        read_only_fields = fields


class PagoAdministracionSerializer(
    serializers.ModelSerializer
):
    class Meta:
        """Define la representación de Pago y protege sus campos de solo lectura."""

        model = Pago

        fields = [
            "id_pago",
            "id_prestacion",
            "monto_total",
            "moneda",
            "porcentaje_comision_aplicado",
            "monto_comision",
            "monto_neto_profesional",
            "estado_pago",
            "metodo_pago",
            "proveedor_pago",
            "estado_verificacion",
            "comprobante_transferencia",
            "fecha_pago",
            "fecha_retencion",
            "fecha_liberacion",
            "referencia_transaccion",
        ]

        read_only_fields = fields


class IniciarPagoTransferenciaSerializer(
    serializers.Serializer
):
    metodo_pago = serializers.ChoiceField(
        choices=[
            "TRANSFERENCIA",
        ]
    )

    comprobante_transferencia = serializers.FileField(
        allow_empty_file=False,
    )

    def validate_comprobante_transferencia(self, archivo):
        if archivo.size > MAX_COMPROBANTE_BYTES:
            raise serializers.ValidationError("El comprobante no puede superar 5 MB.")
        extension = Path(archivo.name).suffix.lower().lstrip(".")
        if extension not in {"pdf", "jpg", "jpeg", "png"}:
            raise serializers.ValidationError("Se aceptan solo PDF, JPG y PNG.")
        cabecera = archivo.read(16)
        archivo.seek(0)
        firmas_validas = {
            "pdf": cabecera.startswith(b"%PDF-"),
            "jpg": cabecera.startswith(b"\xff\xd8\xff"),
            "jpeg": cabecera.startswith(b"\xff\xd8\xff"),
            "png": cabecera.startswith(b"\x89PNG\r\n\x1a\n"),
        }
        if not firmas_validas[extension]:
            raise serializers.ValidationError("El contenido no coincide con el tipo de archivo.")
        # Se usa para crear una ruta propia, nunca para confiar en el nombre recibido.
        self._extension_comprobante = "jpg" if extension == "jpeg" else extension
        return archivo

    def validate(self, attrs):
        attrs["extension_comprobante"] = getattr(self, "_extension_comprobante", None)
        return attrs

    referencia_transaccion = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )


class VerificarPagoTransferenciaSerializer(
    serializers.Serializer
):
    accion = serializers.ChoiceField(
        choices=[
            "VERIFICAR_TRANSFERENCIA",
        ]
    )

    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )


class LiberarPagoSerializer(
    serializers.Serializer
):
    accion = serializers.ChoiceField(
        choices=[
            "LIBERAR_PAGO",
        ]
    )

    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )


class HistorialEstadoPagoAdministracionSerializer(
    serializers.ModelSerializer
):
    responsable_skilly = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de HistorialEstadoPago y protege sus campos de solo lectura."""

        model = HistorialEstadoPago

        fields = [
            "id_historial_pago",
            "id_pago",
            "responsable_skilly",
            "estado_anterior",
            "estado_nuevo",
            "fecha_cambio",
            "observacion",
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


class ReversaPagoSerializer(
    serializers.ModelSerializer
):
    responsable_skilly = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de ReversaPago y protege sus campos de solo lectura."""

        model = ReversaPago

        fields = [
            "id_reversa",
            "id_pago",
            "responsable_skilly",
            "id_resolucion_reclamo",
            "monto_reversa",
            "estado_reversa",
            "motivo",
            "referencia_externa",
            "fecha_solicitud",
            "fecha_resolucion",
        ]

        read_only_fields = fields

    def get_responsable_skilly(
        self,
        reversa,
    ):
        usuario = reversa.id_usuario_skilly

        if usuario is None:
            return None

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class IniciarReversaPagoSerializer(
    serializers.Serializer
):
    motivo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
