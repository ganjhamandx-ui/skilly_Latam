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
    """Expone estado, total, moneda y fechas sin comprobante ni referencia privada."""
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
    """Añade el desglose histórico de comisión y neto a la consulta profesional.

    La vista debe filtrar pertenencia al profesional; el serializador no autoriza objetos.
    """

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
    """Presenta el pago completo a administración, incluidos comprobante y referencia.

    Todos los campos son de lectura; no usar esta representación en respuestas públicas.
    """
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
    """Valida una transferencia informada y su comprobante, sin verificar fondos.

    No recibe el precio ni la comisión; la vista los obtiene de la oferta y los
    parámetros del servidor. Conserva una extensión validada para nombrar el archivo.
    """
    metodo_pago = serializers.ChoiceField(
        choices=[
            "TRANSFERENCIA",
        ]
    )

    comprobante_transferencia = serializers.FileField(
        allow_empty_file=False,
    )

    def validate_comprobante_transferencia(self, archivo):
        """Comprueba tamaño, extensión y firma inicial del comprobante subido.

        Args:
            archivo (UploadedFile): Archivo no vacío, de hasta 5 MiB, PDF/JPG/JPEG/PNG.

        Returns:
            UploadedFile: Mismo archivo con cursor al inicio y extensión normalizada
            guardada en el serializador. La firma no equivale a un análisis del documento.

        Raises:
            serializers.ValidationError: Si excede el tamaño o no coinciden tipo y firma.
        """
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
        """Añade a los datos validados la extensión comprobada para almacenamiento.

        Args:
            attrs (dict): Campos que superaron la validación individual de DRF.

        Returns:
            dict: Mismo diccionario con extension_comprobante, o ``None`` en esa
            clave si no se ejecutó previamente el validador de archivo.
        """
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
    """Exige VERIFICAR_TRANSFERENCIA y admite una observación administrativa opcional."""
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
    """Exige LIBERAR_PAGO y admite observación; las condiciones económicas las revisa la vista."""
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
    """Presenta transiciones históricas con autor opcional, sin permitir escrituras."""
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
        """Devuelve id, correo y rol del autor del historial, o ``None`` si no tiene autor."""
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
    """Expone la reversa, resolución vinculada y autor para la gestión administrativa."""
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
        """Devuelve id, correo y rol del autor de la reversa, o ``None`` si no está registrado."""
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
    """Admite el campo motivo; la vista exige que tenga contenido antes de crear la reversa."""
    motivo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
