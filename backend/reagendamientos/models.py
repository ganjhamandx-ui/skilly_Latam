from django.db import models
from django.db.models import Q


ESTADOS_ABIERTOS = (
    "PENDIENTE_ADMIN",
    "PENDIENTE_PROFESIONAL",
    "ESPERANDO_NUEVO_BLOQUE",
    "PENDIENTE_ORGANIZACION",
    "ESPERANDO_SELECCION",
    "LISTO_CONFIRMAR",
)


class SolicitudReagendamiento(models.Model):
    # Se declara explícitamente para conservar el estado de la migración 0001.
    id = models.BigAutoField(primary_key=True)
    prestacion_id = models.BigIntegerField(db_index=True)
    solicitud_id = models.BigIntegerField(db_index=True)
    profesional_id = models.BigIntegerField(db_index=True)
    bloque_original_id = models.BigIntegerField()
    bloque_propuesto_id = models.BigIntegerField(null=True, blank=True)
    iniciador = models.CharField(max_length=20, default="ORGANIZACION", db_index=True)
    motivo_organizacion = models.TextField(blank=True, default="")
    motivo_profesional = models.TextField(blank=True)
    estado = models.CharField(max_length=40, default="PENDIENTE_ADMIN", db_index=True)
    requiere_confirmacion_organizacion = models.BooleanField(default=False)
    organizacion_autorizo_cambio = models.BooleanField(default=False)
    profesional_confirmo_bloque = models.BooleanField(default=False)
    contrapropuesta_profesional_usada = models.BooleanField(default=False)
    politica_version = models.CharField(max_length=40, default="LEGACY_NO_REGISTRADA")
    politica_actor = models.CharField(max_length=20, blank=True, default="")
    politica_aceptada_en = models.DateTimeField(null=True, blank=True)
    evidencia_nombre = models.CharField(max_length=150, null=True, blank=True)
    evidencia_mime = models.CharField(max_length=40, null=True, blank=True)
    evidencia_sha256 = models.CharField(max_length=64, null=True, blank=True)
    evidencia_contenido = models.BinaryField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "solicitud_reagendamiento"
        constraints = [
            models.UniqueConstraint(
                fields=["prestacion_id"],
                condition=Q(estado__in=ESTADOS_ABIERTOS),
                name="skilly_reag_una_abierta_prestacion",
            )
        ]


class AlternativaReagendamiento(models.Model):
    reagendamiento = models.ForeignKey(
        SolicitudReagendamiento,
        on_delete=models.PROTECT,
        related_name="alternativas",
    )
    bloque_id = models.BigIntegerField()
    origen = models.CharField(max_length=30)
    estado = models.CharField(max_length=25, default="HABILITADA", db_index=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alternativa_reagendamiento"
        ordering = ["fecha_creacion", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["reagendamiento", "bloque_id"],
                name="skilly_reag_alternativa_unica",
            )
        ]


class EventoReagendamiento(models.Model):
    # Se declara explícitamente para conservar el estado de la migración 0001.
    id = models.BigAutoField(primary_key=True)
    reagendamiento = models.ForeignKey(
        SolicitudReagendamiento, on_delete=models.PROTECT, related_name="eventos"
    )
    actor = models.CharField(max_length=25)
    accion = models.CharField(max_length=55)
    detalle = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evento_reagendamiento"
        ordering = ["fecha", "id"]
