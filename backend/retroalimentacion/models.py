"""Modela retroalimentación privada y recomendaciones de desarrollo."""

from django.db import models

from acceso.models import Usuario
from coordinacion.models import PrestacionServicio
from profesionales.models import Profesional
from solicitudes.models import ContactoEmpresa


class Retroalimentacion(models.Model):
    """Registra la evaluación privada de una prestación finalizada."""

    id_feedback = models.BigAutoField(
        primary_key=True
    )

    id_prestacion = models.ForeignKey(
        PrestacionServicio,
        on_delete=models.DO_NOTHING,
        db_column="id_prestacion",
    )

    id_contacto = models.ForeignKey(
        ContactoEmpresa,
        on_delete=models.DO_NOTHING,
        db_column="id_contacto",
    )

    contenido = models.TextField()

    visibilidad = models.CharField(
        max_length=20,
        default="PRIVADA",
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `retroalimentacion`."""

        managed = False
        db_table = "retroalimentacion"


class RecomendacionDesarrollo(models.Model):
    """Conserva una recomendación administrativa comunicable al profesional."""

    class Estado(models.TextChoices):
        """Enumera los estados de registro y comunicación de la recomendación."""

        REGISTRADA = (
            "REGISTRADA",
            "Registrada",
        )

        COMUNICADA = (
            "COMUNICADA",
            "Comunicada",
        )

    id_recomendacion = models.BigAutoField(
        primary_key=True
    )

    id_profesional = models.ForeignKey(
        Profesional,
        on_delete=models.DO_NOTHING,
        db_column="id_profesional",
    )

    id_feedback = models.ForeignKey(
        Retroalimentacion,
        on_delete=models.DO_NOTHING,
        db_column="id_feedback",
        null=True,
        blank=True,
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        on_delete=models.DO_NOTHING,
        db_column="id_usuario_skilly",
    )

    titulo = models.CharField(
        max_length=150
    )

    descripcion = models.TextField()

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.REGISTRADA,
    )

    fecha_creacion = models.DateTimeField()

    fecha_comunicacion = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `recomendacion_desarrollo`."""

        managed = False
        db_table = "recomendacion_desarrollo"
