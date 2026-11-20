"""Mapea organizaciones, contactos, solicitudes y reservas en tablas SQL existentes.

Las competencias de cada solicitud conservan la selección del servicio al enviarla.
Las reuniones y prestaciones se modelan en coordinación, no en este módulo.
"""

from django.db import models

from marketplace.models import Servicio
from profesionales.models import (
    Competencia,
    Profesional,
)


class Disponibilidad(models.Model):
    """Representa un bloque horario publicable de un profesional."""

    id_disponibilidad = models.BigAutoField(
        primary_key=True
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    fecha = models.DateField()

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    estado = models.CharField(
        max_length=20
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `disponibilidad`."""

        managed = False
        db_table = "disponibilidad"


class EmpresaSolicitante(models.Model):
    """Almacena la organización que contrata servicios en SKILLY."""

    id_empresa = models.BigAutoField(
        primary_key=True
    )

    nombre_organizacion = models.CharField(
        max_length=180
    )

    rut = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    rubro = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    sitio_web = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=20
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `empresa_solicitante`."""

        managed = False
        db_table = "empresa_solicitante"

    def __str__(self):
        """Devuelve el nombre de la organización para representaciones legibles."""
        return self.nombre_organizacion


class ContactoEmpresa(models.Model):
    """Conserva datos de un contacto empresarial sin crear una identidad autenticable."""

    id_contacto = models.BigAutoField(
        primary_key=True
    )

    id_empresa = models.ForeignKey(
        EmpresaSolicitante,
        models.DO_NOTHING,
        db_column="id_empresa",
    )

    nombre = models.CharField(
        max_length=150
    )

    cargo = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    correo = models.CharField(
        max_length=150
    )

    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `contacto_empresa`."""

        managed = False
        db_table = "contacto_empresa"

    def __str__(self):
        """Devuelve el nombre del contacto para representaciones legibles."""
        return self.nombre


class SolicitudServicio(models.Model):
    """Registra la necesidad empresarial enviada a un servicio publicado."""

    id_solicitud = models.BigAutoField(
        primary_key=True
    )

    id_empresa = models.ForeignKey(
        EmpresaSolicitante,
        models.DO_NOTHING,
        db_column="id_empresa",
    )

    id_contacto = models.ForeignKey(
        ContactoEmpresa,
        models.DO_NOTHING,
        db_column="id_contacto",
    )

    id_servicio = models.ForeignKey(
        Servicio,
        models.DO_NOTHING,
        db_column="id_servicio",
        blank=True,
        null=True,
    )

    objetivo = models.CharField(
        max_length=250
    )

    descripcion_necesidad = models.TextField()

    modalidad = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    fecha_preferida = models.DateField(
        blank=True,
        null=True,
    )

    referencia_presupuesto = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    urgencia = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_solicitud = models.DateTimeField()

    fecha_actualizacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `solicitud_servicio`."""

        managed = False
        db_table = "solicitud_servicio"


class ReservaDisponibilidad(models.Model):
    """Conserva la selección de un bloque y su evolución para una solicitud.

    PENDIENTE_PAGO no confirma contratación. ACTIVA representa reserva confirmada;
    los estados históricos permiten conservar cancelaciones y reagendamientos.
    """

    id_reserva = models.BigAutoField(
        primary_key=True
    )

    id_disponibilidad = models.ForeignKey(
        Disponibilidad,
        models.DO_NOTHING,
        db_column="id_disponibilidad",
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_reserva = models.DateTimeField()

    fecha_cambio = models.DateTimeField(
        blank=True,
        null=True,
    )

    motivo_cambio = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `reserva_disponibilidad`."""

        managed = False
        db_table = "reserva_disponibilidad"


class SolicitudCompetencia(models.Model):
    """Relaciona una solicitud con las competencias profesionales requeridas."""

    pk = models.CompositePrimaryKey(
        "id_solicitud",
        "id_competencia",
    )

    id_solicitud = models.ForeignKey(
        SolicitudServicio,
        models.DO_NOTHING,
        db_column="id_solicitud",
    )

    id_competencia = models.ForeignKey(
        Competencia,
        models.DO_NOTHING,
        db_column="id_competencia",
    )

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `solicitud_competencia`."""

        managed = False
        db_table = "solicitud_competencia"
