"""Modela parámetros e historiales gestionados por el backoffice."""

from django.db import models

from acceso.models import Usuario


class EventoTrazabilidad(models.Model):
    """Registra quién ejecutó una acción relevante sobre una entidad operativa."""

    id_evento = models.BigAutoField(
        primary_key=True
    )

    id_usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario",
        blank=True,
        null=True,
    )

    entidad_tipo = models.CharField(
        max_length=60
    )

    entidad_id = models.BigIntegerField(
        blank=True,
        null=True,
    )

    accion = models.CharField(
        max_length=80
    )

    detalle_resumido = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    fecha_evento = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `evento_trazabilidad`."""

        managed = False
        db_table = "evento_trazabilidad"


class ParametroSistema(models.Model):
    """Mantiene un parámetro administrativo vigente y su responsable de actualización."""

    id_parametro = models.BigAutoField(
        primary_key=True
    )

    clave = models.CharField(
        max_length=100,
        unique=True,
    )

    valor_actual = models.CharField(
        max_length=500
    )

    tipo_dato = models.CharField(
        max_length=30
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    id_usuario_actualiza = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_actualiza",
        blank=True,
        null=True,
    )

    fecha_actualizacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `parametro_sistema`."""

        managed = False
        db_table = "parametro_sistema"


class HistorialParametro(models.Model):
    """Conserva valores anteriores y nuevos de cada parámetro modificado."""

    id_historial_parametro = models.BigAutoField(
        primary_key=True
    )

    id_parametro = models.ForeignKey(
        ParametroSistema,
        models.DO_NOTHING,
        db_column="id_parametro",
    )

    valor_anterior = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )

    valor_nuevo = models.CharField(
        max_length=500
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
        blank=True,
        null=True,
    )

    fecha_cambio = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `historial_parametro`."""

        managed = False
        db_table = "historial_parametro"
