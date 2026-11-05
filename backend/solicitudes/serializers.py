import re

from django.utils import timezone

from rest_framework import serializers

from .models import (
    Disponibilidad,
    ReservaDisponibilidad,
    SolicitudServicio,
)
from .referencias import crear_referencia_seguimiento


class GuardarDisponibilidadProfesionalSerializer(
    serializers.Serializer
):
    fecha = serializers.DateField(
        required=True
    )

    hora_inicio = serializers.TimeField(
        required=True
    )

    hora_fin = serializers.TimeField(
        required=True
    )

    def validate(self, attrs):
        bloque_actual = self.context.get(
            "bloque_actual"
        )

        fecha = attrs.get(
            "fecha",
            getattr(
                bloque_actual,
                "fecha",
                None,
            ),
        )

        hora_inicio = attrs.get(
            "hora_inicio",
            getattr(
                bloque_actual,
                "hora_inicio",
                None,
            ),
        )

        hora_fin = attrs.get(
            "hora_fin",
            getattr(
                bloque_actual,
                "hora_fin",
                None,
            ),
        )

        if (
            fecha is None
            or hora_inicio is None
            or hora_fin is None
        ):
            raise serializers.ValidationError(
                "Debe indicar fecha, hora de inicio "
                "y hora de término."
            )

        if fecha < timezone.localdate():
            raise serializers.ValidationError(
                {
                    "fecha": (
                        "No puede registrar disponibilidad "
                        "en una fecha pasada."
                    )
                }
            )

        if hora_inicio >= hora_fin:
            raise serializers.ValidationError(
                {
                    "hora_fin": (
                        "La hora de término debe ser "
                        "posterior a la hora de inicio."
                    )
                }
            )

        return attrs


class DisponibilidadProfesionalSerializer(
    serializers.ModelSerializer
):
    reserva_actual = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Disponibilidad

        fields = [
            "id_disponibilidad",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "estado",
            "reserva_actual",
        ]

        read_only_fields = fields

    def get_reserva_actual(
        self,
        disponibilidad,
    ):
        reserva = (
            ReservaDisponibilidad.objects
            .filter(
                id_disponibilidad=disponibilidad
            )
            .order_by(
                "-fecha_reserva",
                "-id_reserva",
            )
            .first()
        )

        if reserva is None:
            return None

        return {
            "id_reserva": reserva.id_reserva,
            "estado": reserva.estado,
            "confirmada": (
                reserva.estado == "ACTIVA"
            ),
            "fecha_reserva": (
                reserva.fecha_reserva
            ),
            "fecha_cambio": (
                reserva.fecha_cambio
            ),
        }


class EnviarSolicitudServicioSerializer(
    serializers.Serializer
):
    id_servicio = serializers.IntegerField(
        min_value=1
    )

    id_disponibilidad = (
        serializers.IntegerField(
            min_value=1
        )
    )

    nombre_organizacion = (
        serializers.CharField(
            max_length=180,
            allow_blank=False,
            trim_whitespace=True,
        )
    )

    rut = serializers.CharField(
        max_length=20,
        required=True,
        allow_blank=False,
        allow_null=False,
        trim_whitespace=True,
    )

    def validate_rut(self, valor):
        # Validacion del modulo 11 chileno; normaliza antes de buscar empresa.
        rut = valor.upper().replace(".", "").replace("-", "").replace(" ", "")
        if not re.fullmatch(r"[0-9]{1,8}[0-9K]", rut):
            raise serializers.ValidationError("Ingresa un RUT chileno valido.")

        cuerpo, verificador = rut[:-1], rut[-1]
        suma = sum(int(digito) * (2 + indice % 6)
                   for indice, digito in enumerate(reversed(cuerpo)))
        resto = 11 - (suma % 11)
        esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
        if verificador != esperado:
            raise serializers.ValidationError("El digito verificador del RUT es incorrecto.")
        return f"{int(cuerpo)}-{verificador}"

    rubro = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    sitio_web = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    nombre_contacto = (
        serializers.CharField(
            max_length=150,
            allow_blank=False,
            trim_whitespace=True,
        )
    )

    cargo_contacto = (
        serializers.CharField(
            max_length=120,
            required=False,
            allow_blank=True,
            allow_null=True,
            trim_whitespace=True,
        )
    )

    correo_contacto = (
        serializers.EmailField(
            max_length=150
        )
    )

    telefono_contacto = (
        serializers.CharField(
            max_length=30,
            required=False,
            allow_blank=True,
            allow_null=True,
            trim_whitespace=True,
        )
    )

    objetivo = serializers.CharField(
        max_length=250,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion_necesidad = (
        serializers.CharField(
            allow_blank=False,
            trim_whitespace=True,
        )
    )



    urgencia = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if "referencia_presupuesto" in self.initial_data:
            raise serializers.ValidationError({
                "referencia_presupuesto": (
                    "El precio es el aprobado y publicado por Skilly; "
                    "la organizacion no puede proponer ni modificarlo."
                )
            })
        campos_opcionales = [
            "rubro",
            "sitio_web",
            "cargo_contacto",
            "telefono_contacto",
            "urgencia",
        ]

        for campo in campos_opcionales:
            if attrs.get(campo) == "":
                attrs[campo] = None

        return attrs


class SolicitudServicioPublicaSerializer(
    serializers.ModelSerializer
):
    empresa = serializers.SerializerMethodField()
    contacto = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()
    reserva = serializers.SerializerMethodField()

    referencia_seguimiento = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = SolicitudServicio

        fields = [
            "id_solicitud",
            "referencia_seguimiento",
            "objetivo",
            "descripcion_necesidad",
            "modalidad",
            "fecha_preferida",
            "referencia_presupuesto",
            "urgencia",
            "estado",
            "fecha_solicitud",
            "fecha_actualizacion",
            "empresa",
            "contacto",
            "servicio",
            "reserva",
        ]

        read_only_fields = fields

    def get_referencia_seguimiento(
        self,
        solicitud,
    ):
        return crear_referencia_seguimiento(
            solicitud
        )

    def get_empresa(
        self,
        solicitud,
    ):
        empresa = solicitud.id_empresa

        return {
            "id_empresa": empresa.id_empresa,
            "nombre_organizacion": (
                empresa.nombre_organizacion
            ),
        }

    def get_contacto(
        self,
        solicitud,
    ):
        contacto = solicitud.id_contacto

        return {
            "id_contacto": (
                contacto.id_contacto
            ),
            "nombre": contacto.nombre,
            "correo": contacto.correo,
        }

    def get_servicio(
        self,
        solicitud,
    ):
        servicio = solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": (
                servicio.id_servicio
            ),
            "nombre": servicio.nombre,
        }

    def get_reserva(
        self,
        solicitud,
    ):
        reserva = (
            ReservaDisponibilidad.objects
            .select_related(
                "id_disponibilidad"
            )
            .filter(
                id_solicitud=solicitud,
                estado__in=[
                    "PENDIENTE_PAGO",
                    "ACTIVA",
                ],
            )
            .order_by(
                "-fecha_reserva",
                "-id_reserva",
            )
            .first()
        )

        if reserva is None:
            return None

        bloque = reserva.id_disponibilidad

        return {
            "id_reserva": (
                reserva.id_reserva
            ),
            "estado": reserva.estado,
            "confirmada": (
                reserva.estado == "ACTIVA"
            ),
            "id_disponibilidad": (
                bloque.id_disponibilidad
            ),
            "fecha": bloque.fecha,
            "hora_inicio": (
                bloque.hora_inicio
            ),
            "hora_fin": bloque.hora_fin,
        }


class SeguimientoSolicitudServicioSerializer(
    serializers.ModelSerializer
):
    empresa = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()
    reserva = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudServicio

        fields = [
            "id_solicitud",
            "estado",
            "objetivo",
            "modalidad",
            "fecha_preferida",
            "fecha_solicitud",
            "fecha_actualizacion",
            "empresa",
            "servicio",
            "reserva",
        ]

        read_only_fields = fields

    def get_empresa(
        self,
        solicitud,
    ):
        return {
            "nombre_organizacion": (
                solicitud
                .id_empresa
                .nombre_organizacion
            ),
        }

    def get_servicio(
        self,
        solicitud,
    ):
        servicio = solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": (
                servicio.id_servicio
            ),
            "nombre": servicio.nombre,
        }

    def get_reserva(
        self,
        solicitud,
    ):
        reserva = (
            ReservaDisponibilidad.objects
            .select_related(
                "id_disponibilidad"
            )
            .filter(
                id_solicitud=solicitud,
                estado__in=[
                    "PENDIENTE_PAGO",
                    "ACTIVA",
                ],
            )
            .order_by(
                "-fecha_reserva",
                "-id_reserva",
            )
            .first()
        )

        if reserva is None:
            return None

        bloque = reserva.id_disponibilidad

        return {
            "id_reserva": (
                reserva.id_reserva
            ),
            "id_disponibilidad": (
                bloque.id_disponibilidad
            ),
            "fecha": bloque.fecha,
            "hora_inicio": (
                bloque.hora_inicio
            ),
            "hora_fin": bloque.hora_fin,
            "estado": reserva.estado,
            "confirmada": (
                reserva.estado == "ACTIVA"
            ),
        }