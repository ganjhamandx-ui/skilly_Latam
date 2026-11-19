"""Valida y representa avances, entregas y reclamos de seguimiento."""

from rest_framework import serializers

from .politicas_incidentes import orientacion_reclamo

from .models import (
    AvanceServicio,
    Entrega,
    ObservacionEntrega,
    ReclamoPrestacion,
    ResolucionReclamo,
)


class AvanceServicioSerializer(
    serializers.ModelSerializer
):
    """Representa avances visibles para los actores de la prestación."""

    class Meta:
        """Define la representación de AvanceServicio y protege sus campos de solo lectura."""

        model = AvanceServicio

        fields = [
            "id_avance",
            "id_prestacion",
            "estado",
            "detalle",
            "fecha_registro",
        ]

        read_only_fields = fields


class RegistrarAvanceServicioSerializer(
    serializers.Serializer
):
    """Valida tipo, detalle y estado de un nuevo avance profesional."""

    estado = serializers.CharField(
        max_length=30
    )

    detalle = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class EntregaSerializer(
    serializers.ModelSerializer
):
    """Serializa una entrega y su versión sin incluir archivos privados."""

    class Meta:
        """Define la representación de Entrega y protege sus campos de solo lectura."""

        model = Entrega

        fields = [
            "id_entrega",
            "id_prestacion",
            "version",
            "descripcion",
            "referencia_entrega",
            "fecha_entrega",
            "estado",
        ]

        read_only_fields = fields


class RegistrarEntregaSerializer(
    serializers.Serializer
):
    """Valida descripción y referencia antes de crear una entrega."""

    descripcion = serializers.CharField()

    referencia_entrega = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class RevisarEntregaEmpresaSerializer(
    serializers.Serializer
):
    """Valida la decisión empresarial y su observación sobre una entrega."""

    accion = serializers.ChoiceField(
        choices=[
            "ACEPTAR",
            "OBSERVAR",
        ]
    )

    detalle = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    def validate(self, datos):
        """Exige observación al objetar y limpia el detalle al aceptar una entrega."""
        accion = datos["accion"]

        detalle = datos.get(
            "detalle"
        )

        if accion == "OBSERVAR":
            if (
                detalle is None
                or not detalle.strip()
            ):
                raise serializers.ValidationError(
                    {
                        "detalle": (
                            "Debe registrar una "
                            "observacion para la entrega."
                        )
                    }
                )

        if accion == "ACEPTAR":
            datos["detalle"] = None

        return datos


class ObservacionEntregaSerializer(
    serializers.ModelSerializer
):
    """Presenta observaciones asociadas a una versión de entrega."""

    contacto_empresa = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de ObservacionEntrega y protege sus campos de solo lectura."""

        model = ObservacionEntrega

        fields = [
            "id_observacion",
            "id_entrega",
            "contacto_empresa",
            "fecha",
            "detalle",
            "estado",
        ]

        read_only_fields = fields

    def get_contacto_empresa(
        self,
        observacion,
    ):
        """Presenta la identidad empresarial asociada a la observación."""
        contacto = observacion.id_contacto

        if contacto is None:
            return None

        return {
            "id_contacto": contacto.id_contacto,
            "nombre": contacto.nombre,
            "correo": contacto.correo,
        }


class ReclamoPrestacionSerializer(
    serializers.ModelSerializer
):
    """Representa el reclamo con datos de prestación pertinentes al actor."""

    orientacion = serializers.SerializerMethodField()

    def get_orientacion(self, reclamo):
        """Calcula la orientación visible según el motivo del reclamo."""
        return orientacion_reclamo(reclamo.motivo)

    class Meta:
        """Define la representación de ReclamoPrestacion y protege sus campos de solo lectura."""

        model = ReclamoPrestacion

        fields = [
            "id_reclamo",
            "id_prestacion",
            "id_contacto",
            "motivo",
            "descripcion",
            "estado",
            "fecha_registro",
            "fecha_cierre",
            "orientacion",
        ]

        read_only_fields = fields


class ResolucionReclamoSerializer(
    serializers.ModelSerializer
):
    """Presenta la resolución administrativa de un reclamo."""

    responsable_skilly = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de ResolucionReclamo y protege sus campos de solo lectura."""

        model = ResolucionReclamo

        fields = [
            "id_resolucion",
            "id_reclamo",
            "responsable_skilly",
            "decision",
            "efecto_economico",
            "monto_afectado",
            "observacion",
            "fecha_resolucion",
        ]

        read_only_fields = fields

    def get_responsable_skilly(
        self,
        resolucion,
    ):
        """Presenta la identidad administrativa responsable de la resolución."""
        usuario = resolucion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ResolverReclamoSerializer(
    serializers.Serializer
):
    """Valida decisión, fundamento y medidas antes de cerrar un reclamo."""

    decision = serializers.CharField(
        max_length=40
    )

    efecto_economico = serializers.ChoiceField(
        choices=[
            "LIBERACION",
            "RETENCION",
            "REVERSA",
        ]
    )

    monto_afectado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    
class RegistrarReclamoEmpresaSerializer(
    serializers.Serializer
):
    """Valida motivo y detalle del reclamo enviado por la empresa."""

    motivo = serializers.CharField(
        max_length=120,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )
