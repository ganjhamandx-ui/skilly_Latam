from django.db import models

from acceso.models import Usuario
from coordinacion.models import PrestacionServicio
from solicitudes.models import ContactoEmpresa


class AvanceServicio(models.Model):
    id_avance = models.BigAutoField(
        primary_key=True
    )

    id_prestacion = models.ForeignKey(
        PrestacionServicio,
        models.DO_NOTHING,
        db_column="id_prestacion",
    )

    estado = models.CharField(
        max_length=30
    )

    detalle = models.TextField(
        blank=True,
        null=True,
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "avance_servicio"


class Entrega(models.Model):
    id_entrega = models.BigAutoField(
        primary_key=True
    )

    id_prestacion = models.ForeignKey(
        PrestacionServicio,
        models.DO_NOTHING,
        db_column="id_prestacion",
    )

    version = models.IntegerField(
        default=1
    )

    descripcion = models.TextField()

    referencia_entrega = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )

    fecha_entrega = models.DateTimeField()

    estado = models.CharField(
        max_length=30
    )

    class Meta:
        managed = False
        db_table = "entrega"


class ObservacionEntrega(models.Model):
    id_observacion = models.BigAutoField(
        primary_key=True
    )

    id_entrega = models.ForeignKey(
        Entrega,
        models.DO_NOTHING,
        db_column="id_entrega",
    )

    id_contacto = models.ForeignKey(
        ContactoEmpresa,
        models.DO_NOTHING,
        db_column="id_contacto",
    )

    fecha = models.DateTimeField()

    detalle = models.TextField()

    estado = models.CharField(
        max_length=30
    )

    class Meta:
        managed = False
        db_table = "observacion_entrega"


class ReclamoPrestacion(models.Model):
    id_reclamo = models.BigAutoField(
        primary_key=True
    )

    id_prestacion = models.ForeignKey(
        PrestacionServicio,
        models.DO_NOTHING,
        db_column="id_prestacion",
    )

    id_contacto = models.ForeignKey(
        ContactoEmpresa,
        models.DO_NOTHING,
        db_column="id_contacto",
    )

    motivo = models.CharField(
        max_length=120
    )

    descripcion = models.TextField()

    estado = models.CharField(
        max_length=30
    )

    fecha_registro = models.DateTimeField()

    fecha_cierre = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "reclamo_prestacion"


class ResolucionReclamo(models.Model):
    id_resolucion = models.BigAutoField(
        primary_key=True
    )

    id_reclamo = models.OneToOneField(
        ReclamoPrestacion,
        models.DO_NOTHING,
        db_column="id_reclamo",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
    )

    decision = models.CharField(
        max_length=40
    )

    efecto_economico = models.CharField(
        max_length=40
    )

    monto_afectado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    observacion = models.TextField(
        blank=True,
        null=True,
    )

    fecha_resolucion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "resolucion_reclamo"