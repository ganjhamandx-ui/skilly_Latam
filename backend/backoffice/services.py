"""Centraliza la creación de eventos de trazabilidad usados por los módulos de SKILLY."""

from django.utils import timezone

from .models import EventoTrazabilidad


def registrar_evento_trazabilidad(
    usuario,
    entidad_tipo,
    entidad_id,
    accion,
    detalle_resumido=None,
):
    """Persiste un evento de trazabilidad con la fecha actual de Django.

    Args:
        usuario (Usuario | None): Autor autenticado, o ``None`` para eventos sin sesión.
        entidad_tipo (str): Tipo de entidad que permitirá agrupar el historial.
        entidad_id (int): Identificador de la entidad afectada.
        accion (str): Operación o transición que se registra.
        detalle_resumido (str | None): Texto opcional, ya acotado y depurado por el llamador.

    Returns:
        EventoTrazabilidad: Evento creado en la transacción activa, si la hay.

    Note:
        No recorta el detalle ni elimina secretos automáticamente. Cada llamador
        debe respetar la longitud del modelo y excluir datos sensibles antes de invocarlo.
    """

    return EventoTrazabilidad.objects.create(
        id_usuario=usuario,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        detalle_resumido=detalle_resumido,
        fecha_evento=timezone.now(),
    )
