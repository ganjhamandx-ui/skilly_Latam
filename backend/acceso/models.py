"""Modela usuarios, sesiones y datos necesarios para el acceso a SKILLY."""

from django.db import models


class Usuario(models.Model):
    """Representa la identidad autenticable y su rol operativo dentro de SKILLY."""

    id_usuario = models.BigAutoField(primary_key=True)
    correo = models.CharField(unique=True, max_length=150)
    password_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=30)
    estado = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `usuario`."""

        managed = False
        db_table = "usuario"

    def __str__(self):
        return self.correo


class RecuperacionAcceso(models.Model):
    """Conserva un token hash de recuperación con expiración y uso único."""

    id_recuperacion = models.BigAutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario",
    )

    token_hash = models.CharField(max_length=255)
    fecha_solicitud = models.DateTimeField()
    fecha_expiracion = models.DateTimeField()
    usado = models.BooleanField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `recuperacion_acceso`."""

        managed = False
        db_table = "recuperacion_acceso"

    def __str__(self):
        return f"Recuperación {self.id_recuperacion}"
