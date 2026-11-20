"""Modela servicios, categorías y competencias publicadas en el marketplace."""

from django.db import models

from acceso.models import Usuario
from profesionales.models import (
    Competencia,
    Profesional,
)


class CategoriaServicio(models.Model):
    """Clasifica servicios mediante un nombre único y un estado de catálogo."""
    id_categoria = models.BigAutoField(
        primary_key=True
    )

    nombre = models.CharField(
        max_length=120,
        unique=True,
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=20
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `categoria_servicio`."""

        managed = False
        db_table = "categoria_servicio"

    def __str__(self):
        """Devuelve el nombre de la categoría para representaciones legibles."""
        return self.nombre


class Servicio(models.Model):
    """Conserva la oferta actual de un profesional y su estado de publicación.

    Las versiones comerciales se guardan en RevisionServicio; el visto bueno
    profesional aplica sus datos antes de permitir la publicación.
    """
    id_servicio = models.BigAutoField(
        primary_key=True
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    id_categoria = models.ForeignKey(
        CategoriaServicio,
        models.DO_NOTHING,
        db_column="id_categoria",
    )

    nombre = models.CharField(
        max_length=150
    )

    descripcion = models.TextField()

    modalidad = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    alcance = models.TextField(
        blank=True,
        null=True,
    )

    referencia_precio = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    estado_publicacion = models.CharField(
        max_length=30
    )

    fecha_publicacion = models.DateTimeField(
        blank=True,
        null=True,
    )

    fecha_actualizacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `servicio`."""

        managed = False
        db_table = "servicio"

    def __str__(self):
        """Devuelve el nombre comercial del servicio."""
        return self.nombre


class ServicioCompetencia(models.Model):
    """Relaciona servicio y competencia con clave primaria compuesta, sin duplicados."""
    pk = models.CompositePrimaryKey(
        "id_servicio",
        "id_competencia",
    )

    id_servicio = models.ForeignKey(
        Servicio,
        models.DO_NOTHING,
        db_column="id_servicio",
    )

    id_competencia = models.ForeignKey(
        Competencia,
        models.DO_NOTHING,
        db_column="id_competencia",
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `servicio_competencia`."""

        managed = False
        db_table = "servicio_competencia"


class RevisionServicio(models.Model):
    """Conserva versiones de revisión y decisiones comerciales del servicio.

    contenido_revisado admite texto heredado o JSON estructurado. El autor
    administrativo es opcional en decisiones profesionales. La fecha de
    aprobación profesional acredita el visto bueno previo a publicar.
    """
    id_revision_servicio = models.BigAutoField(
        primary_key=True
    )

    id_servicio = models.ForeignKey(
        Servicio,
        models.DO_NOTHING,
        db_column="id_servicio",
    )

    id_usuario_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_skilly",
        blank=True,
        null=True,
    )

    numero_version = models.IntegerField()

    contenido_revisado = models.TextField()

    observacion = models.TextField(
        blank=True,
        null=True,
    )

    estado_revision = models.CharField(
        max_length=30
    )

    fecha_revision = models.DateTimeField()

    fecha_aprobacion_profesional = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `revision_servicio`."""

        managed = False
        db_table = "revision_servicio"
