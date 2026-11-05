from django.db import models

from acceso.models import Usuario
from profesionales.models import Profesional
from solicitudes.models import SolicitudServicio


class SolicitudProfesional(models.Model):
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
        managed = False
        db_table = "solicitud_profesional"


class AsignacionSolicitud(models.Model):
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
        managed = False
        db_table = "asignacion_solicitud"


class CoordinacionSolicitud(models.Model):
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
        managed = False
        db_table = "coordinacion_solicitud"


class ReunionSolicitud(models.Model):
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
        managed = False
        db_table = "reunion_solicitud"


class PrestacionServicio(models.Model):
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
        managed = False
        db_table = "prestacion_servicio"