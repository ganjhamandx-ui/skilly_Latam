"""Criterio único de vigencia de las asignaciones de solicitudes."""

from .models import AsignacionSolicitud


def asignaciones_vigentes(id_solicitud):
    """Solo asignaciones activas sin fecha de finalización."""
    return AsignacionSolicitud.objects.filter(
        id_solicitud_id=id_solicitud,
        estado="ACTIVA",
        fecha_fin__isnull=True,
    )
