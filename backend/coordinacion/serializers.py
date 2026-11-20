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
    """Expone solicitudes a administración con organización, contacto y servicio.

    Todos los campos son de lectura. Los datos de contacto pertenecen a la vista
    administrativa; esta representación no debe reutilizarse en listados públicos.
    """
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
        """Devuelve identificación fiscal y datos organizacionales de la solicitud.

        Args:
            solicitud (SolicitudServicio): Solicitud con empresa asociada.

        Returns:
            dict: Id, nombre, RUT, rubro y sitio web de la organización.
        """
        empresa = solicitud.id_empresa

        return {
            "id_empresa": empresa.id_empresa,
            "nombre_organizacion": empresa.nombre_organizacion,
            "rut": empresa.rut,
            "rubro": empresa.rubro,
            "sitio_web": empresa.sitio_web,
        }

    def get_contacto(self, solicitud):
        """Obtiene el contacto empresarial para la gestión interna.

        Args:
            solicitud (SolicitudServicio): Solicitud con contacto asociado.

        Returns:
            dict: Id, nombre, cargo, correo y teléfono del contacto.
        """
        contacto = solicitud.id_contacto

        return {
            "id_contacto": contacto.id_contacto,
            "nombre": contacto.nombre,
            "cargo": contacto.cargo,
            "correo": contacto.correo,
            "telefono": contacto.telefono,
        }

    def get_servicio(self, solicitud):
        """Resume el servicio elegido o conserva su ausencia.

        Args:
            solicitud (SolicitudServicio): Solicitud cuyo servicio puede ser nulo.

        Returns:
            dict | None: Id, nombre y modalidad; ``None`` si no hay servicio.
        """
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
    """Expone la asignación y su responsable sin permitir cambios por serialización."""
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
        """Resume la identidad interna vinculada a la asignación.

        Args:
            asignacion (AsignacionSolicitud): Registro con usuario responsable.

        Returns:
            dict: Identificador, correo y rol; omite credenciales de autenticación.
        """
        usuario = asignacion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class AsociacionSolicitudProfesionalSerializer(
    serializers.ModelSerializer
):
    """Presenta una asociación con servicio y perfil para evaluación administrativa."""
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
        """Obtiene el servicio de la solicitud asociada.

        Args:
            asociacion (SolicitudProfesional): Relación entre solicitud y profesional.

        Returns:
            dict | None: Id, nombre y modalidad, o ``None`` si no hay servicio.
        """
        servicio = asociacion.id_solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "modalidad": servicio.modalidad,
        }

    def get_profesional(self, asociacion):
        """Resume el perfil asociado y su estado de validación.

        Args:
            asociacion (SolicitudProfesional): Relación cuyo profesional se presenta.

        Returns:
            dict: Identidad, nombres, título, ubicación y estado de validación.
        """
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
    """Presenta gestiones históricas con la identidad del administrador que las registró."""
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
        """Resume al autor de la gestión, no al responsable vigente de la solicitud.

        Args:
            coordinacion (CoordinacionSolicitud): Gestión histórica consultada.

        Returns:
            dict: Id, correo y rol del usuario relacionado.
        """
        usuario = coordinacion.id_usuario_skilly

        return {
            "id_usuario": usuario.id_usuario,
            "correo": usuario.correo,
            "rol": usuario.rol,
        }


class ReservaDisponibilidadAdministracionSerializer(
    serializers.ModelSerializer
):
    """Expone una reserva y el horario actual de su bloque para revisar consistencia."""
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
        """Presenta el bloque relacionado con la reserva, sin recalcular disponibilidad.

        Args:
            reserva (ReservaDisponibilidad): Reserva con bloque asociado.

        Returns:
            dict: Id, fecha, horas de inicio y fin, y estado persistido del bloque.
        """
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
    """Presenta reuniones, participantes y enlace para administración, en solo lectura."""
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
        """Devuelve id, nombres y apellidos del profesional de la reunión recibida."""
        profesional = reunion.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
        }

    def get_responsable_skilly(self, reunion):
        """Resume el responsable interno opcional de una reunión.

        Args:
            reunion (ReunionSolicitud): Reunión que puede carecer de administrador.

        Returns:
            dict | None: Id, correo y rol del usuario, o ``None`` si no se asignó.
        """
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
    """Exige condiciones textuales no vacías y elimina sus espacios exteriores."""
    condiciones_comunicadas = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )


class AgendarPrimeraReunionSerializer(
    serializers.Serializer
):
    """Valida fecha, modalidad y enlace opcional de la primera reunión.

    Valida tipos y longitudes. La vista obtiene la fecha del bloque y verifica
    pago, reserva y futuro antes de crear la reunión.
    """
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
    """Presenta condiciones, estado, fechas y profesional de la prestación en solo lectura."""
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
        """Devuelve id, nombres y apellidos del profesional de la prestación recibida."""
        profesional = prestacion.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
        }


class OportunidadProfesionalSerializer(
    serializers.ModelSerializer
):
    """Presenta oportunidades al profesional sin exponer contactos empresariales.

    La vista debe filtrar las asociaciones por el profesional autenticado; el
    serializador solo limita los campos y no aplica autorización por objeto.
    """
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
        """Resume objetivo, necesidad, modalidad y fecha preferida de la solicitud asociada."""
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
        """Obtiene id, nombre y modalidad del servicio, o ``None`` si no fue seleccionado."""
        servicio = asociacion.id_solicitud.id_servicio

        if servicio is None:
            return None

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "modalidad": servicio.modalidad,
        }

    def get_empresa(self, asociacion):
        """Devuelve solo el nombre de la organización para proteger sus datos de contacto."""
        empresa = asociacion.id_solicitud.id_empresa

        return {
            "nombre_organizacion": (
                empresa.nombre_organizacion
            ),
        }

    def get_estado_coordinacion(self, asociacion):
        """Consulta el último estado registrado en el historial de coordinación.

        Args:
            asociacion (SolicitudProfesional): Relación cuya solicitud se consulta.

        Returns:
            dict | None: Estado y fecha de la gestión más reciente, desempatada por id;
            ``None`` si no hay historial. No equivale al estado actual de la prestación.
        """
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
    """Presenta prestaciones al profesional con condiciones y datos acotados de empresa.

    Omite el contacto empresarial y deja el filtro de pertenencia a la vista.
    """
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
        """Devuelve únicamente el nombre de la organización de la prestación recibida."""
        empresa = prestacion.id_solicitud.id_empresa

        return {
            "nombre_organizacion": (
                empresa.nombre_organizacion
            ),
        }

    def get_servicio(self, prestacion):
        """Describe el servicio contratado con su referencia de precio.

        Args:
            prestacion (PrestacionServicio): Prestación con solicitud relacionada.

        Returns:
            dict | None: Id, nombre, descripción, modalidad, alcance y precio
            de referencia, o ``None`` si la solicitud no tiene servicio.
        """
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
        """Resume objetivo, modalidad y fecha preferida de la solicitud de la prestación."""
        solicitud = prestacion.id_solicitud

        return {
            "objetivo": solicitud.objetivo,
            "modalidad": solicitud.modalidad,
            "fecha_preferida": solicitud.fecha_preferida,
        }
