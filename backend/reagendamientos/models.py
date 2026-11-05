from django.db import models
from django.db.models import Q


ESTADOS_ABIERTOS = (
    "PENDIENTE_ADMIN",
    "PENDIENTE_PROFESIONAL",
    "ESPERANDO_NUEVO_BLOQUE",
    "PENDIENTE_ORGANIZACION",
    "LISTO_CONFIRMAR",
)


class SolicitudReagendamiento(models.Model):
    prestacion_id = models.BigIntegerField(db_index=True)
    solicitud_id = models.BigIntegerField(db_index=True)
    profesional_id = models.BigIntegerField(db_index=True)
    bloque_original_id = models.BigIntegerField()
    bloque_propuesto_id = models.BigIntegerField(null=True, blank=True)
    motivo_organizacion = models.TextField()
    motivo_profesional = models.TextField(blank=True)
    estado = models.CharField(max_length=40, default="PENDIENTE_ADMIN", db_index=True)
    requiere_confirmacion_organizacion = models.BooleanField(default=False)
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


class EventoReagendamiento(models.Model):
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
