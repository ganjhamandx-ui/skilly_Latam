from django.db import models

from acceso.models import Usuario
from coordinacion.models import PrestacionServicio


class Pago(models.Model):
    id_pago = models.BigAutoField(
        primary_key=True
    )

    id_prestacion = models.OneToOneField(
        PrestacionServicio,
        models.DO_NOTHING,
        db_column="id_prestacion",
    )

    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    moneda = models.CharField(
        max_length=10
    )

    porcentaje_comision_aplicado = models.DecimalField(
        max_digits=7,
        decimal_places=4,
    )

    monto_comision = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    monto_neto_profesional = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    estado_pago = models.CharField(
        max_length=30
    )

    metodo_pago = models.CharField(
        max_length=30
    )

    proveedor_pago = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    estado_verificacion = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    comprobante_transferencia = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    fecha_pago = models.DateTimeField(
        blank=True,
        null=True,
    )

    fecha_retencion = models.DateTimeField(
        blank=True,
        null=True,
    )

    fecha_liberacion = models.DateTimeField(
        blank=True,
        null=True,
    )

    referencia_transaccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "pago"


class HistorialEstadoPago(models.Model):
    id_historial_pago = models.BigAutoField(
        primary_key=True
    )

    id_pago = models.ForeignKey(
        Pago,
        models.DO_NOTHING,
        db_column="id_pago",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
        blank=True,
        null=True,
    )

    estado_anterior = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    estado_nuevo = models.CharField(
        max_length=30
    )

    fecha_cambio = models.DateTimeField()

    observacion = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "historial_estado_pago"


class ReversaPago(models.Model):
    id_reversa = models.BigAutoField(
        primary_key=True
    )

    id_pago = models.ForeignKey(
        Pago,
        models.DO_NOTHING,
        db_column="id_pago",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
        blank=True,
        null=True,
    )

    id_resolucion_reclamo = models.ForeignKey(
        "seguimiento.ResolucionReclamo",
        models.DO_NOTHING,
        db_column="id_resolucion_reclamo",
        blank=True,
        null=True,
    )

    monto_reversa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    estado_reversa = models.CharField(
        max_length=30
    )

    motivo = models.TextField(
        blank=True,
        null=True,
    )

    referencia_externa = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    fecha_solicitud = models.DateTimeField()

    fecha_resolucion = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "reversa_pago"