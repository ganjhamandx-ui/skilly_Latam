from django.db import models

from marketplace.models import Servicio
from profesionales.models import (
    Competencia,
    Profesional,
)


class Disponibilidad(models.Model):
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
        managed = False
        db_table = "disponibilidad"


class EmpresaSolicitante(models.Model):
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
        managed = False
        db_table = "empresa_solicitante"

    def __str__(self):
        return self.nombre_organizacion


class ContactoEmpresa(models.Model):
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
        managed = False
        db_table = "contacto_empresa"

    def __str__(self):
        return self.nombre


class SolicitudServicio(models.Model):
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
        managed = False
        db_table = "solicitud_servicio"


class ReservaDisponibilidad(models.Model):
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
        managed = False
        db_table = "reserva_disponibilidad"


class SolicitudCompetencia(models.Model):
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
        managed = False
        db_table = "solicitud_competencia"