"""Modela asignaciones, prestaciones, reservas y reuniones coordinadas."""

from django.db import models

from acceso.models import Usuario
from profesionales.models import Profesional
from solicitudes.models import SolicitudServicio


class SolicitudProfesional(models.Model):
    """Asocia una solicitud y un profesional mediante una clave primaria compuesta.

    Conserva tipo, estado y fecha de la propuesta. La aceptación de esta relación
    no crea por sí misma una prestación ni confirma el pago.
    """
    pk = models.CompositePrimaryKey(
        "id_solicitud",
        "id_profesional",
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    tipo_asociacion = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_asociacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `solicitud_profesional`."""

        managed = False
        db_table = "solicitud_profesional"


class AsignacionSolicitud(models.Model):
    """Registra la responsabilidad de un usuario interno sobre una solicitud.

    La vigencia exige estado ACTIVA y fecha_fin nula. Este modelo no declara una
    restricción de responsable único; las operaciones serializan la asignación
    bloqueando la solicitud en la tabla preexistente.
    """
    id_asignacion = models.BigAutoField(
        primary_key=True
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
    )

    tipo_asignacion = models.CharField(
        max_length=30
    )

    fecha_asignacion = models.DateTimeField()

    fecha_fin = models.DateTimeField(
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `asignacion_solicitud`."""

        managed = False
        db_table = "asignacion_solicitud"


class CoordinacionSolicitud(models.Model):
    """Conserva cada gestión administrativa, su responsable y el estado resultante.

    Es un historial de la solicitud; no sustituye los estados actuales de reserva,
    reunión o prestación ni los eventos generales de trazabilidad.
    """
    id_coordinacion = models.BigAutoField(
        primary_key=True
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
    )

    tipo = models.CharField(
        max_length=40
    )

    detalle = models.TextField(
        blank=True,
        null=True,
    )

    estado_resultante = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `coordinacion_solicitud`."""

        managed = False
        db_table = "coordinacion_solicitud"


class ReunionSolicitud(models.Model):
    """Vincula una reunión fechada con solicitud, profesional y responsable opcional.

    Las operaciones de agenda mantienen coherencia con el bloque reservado y
    preservan la fecha histórica cuando cancelan o postergan sin nuevo horario.
    """
    id_reunion = models.BigAutoField(
        primary_key=True
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
        blank=True,
        null=True,
    )

    fecha_hora = models.DateTimeField()

    modalidad = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    enlace_reunion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `reunion_solicitud`."""

        managed = False
        db_table = "reunion_solicitud"


class PrestacionServicio(models.Model):
    """Representa la prestación única de una solicitud y su profesional asignado.

    Guarda condiciones comunicadas, estado y fechas del ciclo de contratación.
    Pagos, reservas y reuniones tienen persistencia separada; las vistas comprueban
    sus estados antes de formalizar o modificar la contratación.
    """
    id_prestacion = models.BigAutoField(
        primary_key=True
    )

    id_solicitud = models.OneToOneField(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    condiciones_comunicadas = models.TextField(
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_confirmacion = models.DateTimeField(
        blank=True,
        null=True,
    )

    fecha_inicio = models.DateField(
        blank=True,
        null=True,
    )

    fecha_fin = models.DateField(
        blank=True,
        null=True,
    )

    fecha_cierre = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `prestacion_servicio`."""

        managed = False
        db_table = "prestacion_servicio"
