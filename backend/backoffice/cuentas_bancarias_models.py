"""Modelos unmanaged. Requieren tablas verificadas; no se migran automáticamente."""
from django.db import models

class CuentaBancariaSkilly(models.Model):
    """Representa un destino bancario administrado y su condición de cuenta principal."""

    id_cuenta = models.BigAutoField(primary_key=True)
    titular = models.CharField(max_length=180)
    rut_titular = models.CharField(max_length=12)
    banco = models.CharField(max_length=120)
    tipo_cuenta = models.CharField(max_length=24)
    numero_cuenta = models.CharField(max_length=32)
    correo = models.CharField(max_length=254)
    activa = models.BooleanField(default=False)
    principal = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField()
    fecha_modificacion = models.DateTimeField()
    id_usuario_creacion = models.BigIntegerField(null=True)
    id_usuario_modificacion = models.BigIntegerField(null=True)

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `cuenta_bancaria_skilly`."""

        app_label = 'backoffice'
        managed = False
        db_table = 'cuenta_bancaria_skilly'

class HistorialCuentaBancariaSkilly(models.Model):
    """Conserva una instantánea auditable de cada modificación bancaria."""

    id_cambio = models.BigAutoField(primary_key=True)
    id_cuenta = models.ForeignKey(CuentaBancariaSkilly, models.DO_NOTHING, db_column='id_cuenta')
    accion = models.CharField(max_length=25)
    datos_anteriores = models.JSONField(null=True)
    datos_nuevos = models.JSONField()
    id_usuario_skilly = models.BigIntegerField(null=True)
    fecha_cambio = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `cuenta_bancaria_skilly_historial`."""

        app_label = 'backoffice'
        managed = False
        db_table = 'cuenta_bancaria_skilly_historial'
