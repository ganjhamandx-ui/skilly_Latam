"""Valida datos de coordinación, agenda y contratación de prestaciones."""

from rest_framework import serializers

from solicitudes.models import (
    ReservaDisponibilidad,
    SolicitudServicio,
)

from .models import (
    AsignacionSolicitud,
    CoordinacionSolicitud,
    PrestacionServicio,
    ReunionSolicitud,
    SolicitudProfesional,
)


class SolicitudEmpresarialAdministracionSerializer(
    serializers.ModelSerializer
):
    empresa = serializers.SerializerMethodField()
    contacto = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de SolicitudServicio y protege sus campos de solo lectura."""

        model = SolicitudServicio

        fields = [
            "id_solicitud",
            "empresa",
            "contacto",
            "servicio",
            "objetivo",
            "descripcion_necesidad",
            "modalidad",
            "fecha_preferida",
            "referencia_presupuesto",
            "urgencia",
            "estado",
            "fecha_solicitud",
            "fecha_actualizacion",
        ]

        read_only_fields = fields

    def get_empresa(self, solicitud):
        empresa = solicitud.id_empresa

        return {
            "id_empresa": empresa.id_empresa,
            "nombre_organizacion": empresa.nombre_organizacion,
            "rut": empresa.rut,
            "rubro": empresa.rubro,
            "sitio_web": empresa.sitio_web,
        }

    def get_contacto(self, solicitud):
        contacto = solicitud.id_contacto

        return {
            "id_contacto": contacto.id_contacto,
            "nombre": contacto.nombre,
            "cargo": contacto.cargo,
            "correo": contacto.correo,
            "telefono": contacto.telefono,
        }

    def get_servicio(self, solicitud):
        servicio = solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "modalidad": servicio.modalidad,
        }


class AsignacionSolicitudAdministracionSerializer(
    serializers.ModelSerializer
):
    responsable = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de AsignacionSolicitud y protege sus campos de solo lectura."""

        model = AsignacionSolicitud

        fields = [
            "id_asignacion",
            "id_solicitud",
            "responsable",
            "tipo_asignacion",
            "fecha_asignacion",
            "fecha_fin",
            "estado",
        ]

        read_only_fields = fields

    def get_responsable(self, asignacion):
        usuario = asignacion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class AsociacionSolicitudProfesionalSerializer(
    serializers.ModelSerializer
):
    servicio = serializers.SerializerMethodField()
    profesional = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de SolicitudProfesional y protege sus campos de solo lectura."""

        model = SolicitudProfesional

        fields = [
            "id_solicitud",
            "servicio",
            "profesional",
            "tipo_asociacion",
            "estado",
            "fecha_asociacion",
        ]

        read_only_fields = fields

    def get_servicio(self, asociacion):
        servicio = asociacion.id_solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "modalidad": servicio.modalidad,
        }

    def get_profesional(self, asociacion):
        profesional = asociacion.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
            "titulo_profesional": profesional.titulo_profesional,
            "ubicacion": profesional.ubicacion,
            "estado_validacion": profesional.estado_validacion,
        }


class CoordinacionSolicitudAdministracionSerializer(
    serializers.ModelSerializer
):
    responsable = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de CoordinacionSolicitud y protege sus campos de solo lectura."""

        model = CoordinacionSolicitud

        fields = [
            "id_coordinacion",
            "id_solicitud",
            "responsable",
            "tipo",
            "detalle",
            "estado_resultante",
            "fecha_registro",
        ]

        read_only_fields = fields

    def get_responsable(self, coordinacion):
        usuario = coordinacion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ReservaDisponibilidadAdministracionSerializer(
    serializers.ModelSerializer
):
    disponibilidad = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de ReservaDisponibilidad y protege sus campos de solo lectura."""

        model = ReservaDisponibilidad

        fields = [
            "id_reserva",
            "id_solicitud",
            "disponibilidad",
            "estado",
            "fecha_reserva",
            "fecha_cambio",
            "motivo_cambio",
        ]

        read_only_fields = fields

    def get_disponibilidad(self, reserva):
        disponibilidad = reserva.id_disponibilidad

        return {
            "id_disponibilidad": (
                disponibilidad.id_disponibilidad
            ),
            "fecha": disponibilidad.fecha,
            "hora_inicio": disponibilidad.hora_inicio,
            "hora_fin": disponibilidad.hora_fin,
            "estado": disponibilidad.estado,
        }


class ReunionSolicitudAdministracionSerializer(
    serializers.ModelSerializer
):
    profesional = serializers.SerializerMethodField()
    responsable_skilly = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de ReunionSolicitud y protege sus campos de solo lectura."""

        model = ReunionSolicitud

        fields = [
            "id_reunion",
            "id_solicitud",
            "profesional",
            "responsable_skilly",
            "fecha_hora",
            "modalidad",
            "estado",
            "enlace_reunion",
        ]

        read_only_fields = fields

    def get_profesional(self, reunion):
        profesional = reunion.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
        }

    def get_responsable_skilly(self, reunion):
        usuario = reunion.id_usuario_skilly

        if usuario is None:
            return None

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ComunicarCondicionesPrestacionSerializer(
    serializers.Serializer
):
    condiciones_comunicadas = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )


class AgendarPrimeraReunionSerializer(
    serializers.Serializer
):
    fecha_hora = serializers.DateTimeField()

    modalidad = serializers.CharField(
        max_length=30,
        allow_blank=False,
        trim_whitespace=True,
    )

    enlace_reunion = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )


class PrestacionServicioAdministracionSerializer(
    serializers.ModelSerializer
):
    profesional = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de PrestacionServicio y protege sus campos de solo lectura."""

        model = PrestacionServicio

        fields = [
            "id_prestacion",
            "id_solicitud",
            "profesional",
            "condiciones_comunicadas",
            "estado",
            "fecha_confirmacion",
            "fecha_inicio",
            "fecha_fin",
            "fecha_cierre",
        ]

        read_only_fields = fields

    def get_profesional(self, prestacion):
        profesional = prestacion.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
        }


class OportunidadProfesionalSerializer(
    serializers.ModelSerializer
):
    necesidad = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()
    empresa = serializers.SerializerMethodField()
    estado_coordinacion = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de SolicitudProfesional y protege sus campos de solo lectura."""

        model = SolicitudProfesional

        fields = [
            "id_solicitud",
            "necesidad",
            "servicio",
            "empresa",
            "estado_coordinacion",
            "tipo_asociacion",
            "estado",
            "fecha_asociacion",
        ]

        read_only_fields = fields

    def get_necesidad(self, asociacion):
        solicitud = asociacion.id_solicitud

        return {
            "objetivo": solicitud.objetivo,
            "descripcion_necesidad": (
                solicitud.descripcion_necesidad
            ),
            "modalidad": solicitud.modalidad,
            "fecha_preferida": solicitud.fecha_preferida,
        }

    def get_servicio(self, asociacion):
        servicio = asociacion.id_solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "modalidad": servicio.modalidad,
        }

    def get_empresa(self, asociacion):
        empresa = asociacion.id_solicitud.id_empresa

        return {
            "nombre_organizacion": (
                empresa.nombre_organizacion
            ),
        }

    def get_estado_coordinacion(self, asociacion):
        coordinacion = (
            CoordinacionSolicitud.objects
            .filter(
                id_solicitud=asociacion.id_solicitud
            )
            .order_by(
                "-fecha_registro",
                "-id_coordinacion",
            )
            .first()
        )

        if coordinacion is None:
            return None

        return {
            "estado": coordinacion.estado_resultante,
            "fecha": coordinacion.fecha_registro,
        }


class ServicioCoordinadoProfesionalSerializer(
    serializers.ModelSerializer
):
    empresa = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()
    solicitud = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de PrestacionServicio y protege sus campos de solo lectura."""

        model = PrestacionServicio

        fields = [
            "id_prestacion",
            "id_solicitud",
            "empresa",
            "servicio",
            "solicitud",
            "condiciones_comunicadas",
            "estado",
            "fecha_confirmacion",
            "fecha_inicio",
            "fecha_fin",
            "fecha_cierre",
        ]

        read_only_fields = fields

    def get_empresa(self, prestacion):
        empresa = prestacion.id_solicitud.id_empresa

        return {
            "nombre_organizacion": (
                empresa.nombre_organizacion
            ),
        }

    def get_servicio(self, prestacion):
        servicio = prestacion.id_solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "descripcion": servicio.descripcion,
            "modalidad": servicio.modalidad,
            "alcance": servicio.alcance,
            "referencia_precio": (
                servicio.referencia_precio
            ),
        }

    def get_solicitud(self, prestacion):
        solicitud = prestacion.id_solicitud

        return {
            "objetivo": solicitud.objetivo,
            "modalidad": solicitud.modalidad,
            "fecha_preferida": solicitud.fecha_preferida,
        }
