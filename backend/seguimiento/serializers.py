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
    class Meta:
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
    class Meta:
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
    contacto_empresa = serializers.SerializerMethodField()

    class Meta:
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
    orientacion = serializers.SerializerMethodField()

    def get_orientacion(self, reclamo):
        return orientacion_reclamo(reclamo.motivo)

    class Meta:
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
    responsable_skilly = serializers.SerializerMethodField()

    class Meta:
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
        usuario = resolucion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ResolverReclamoSerializer(
    serializers.Serializer
):
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
    motivo = serializers.CharField(
        max_length=120,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )
