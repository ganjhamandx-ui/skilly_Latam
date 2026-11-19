"""Centraliza servicios de configuración vigentes para el backoffice."""

from django.utils import timezone

from .models import EventoTrazabilidad


def registrar_evento_trazabilidad(
    usuario,
    entidad_tipo,
    entidad_id,
    accion,
    detalle_resumido=None,
):
    """Crea un evento auditable con un detalle resumido y sin datos sensibles."""

    return EventoTrazabilidad.objects.create(
        id_usuario=usuario,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        detalle_resumido=detalle_resumido,
        fecha_evento=timezone.now(),
    )
