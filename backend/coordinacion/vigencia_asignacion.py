"""Criterio único de vigencia de las asignaciones de solicitudes."""

from .models import AsignacionSolicitud


def asignaciones_vigentes(id_solicitud):
    """Selecciona asignaciones activas sin fecha de finalización.

    Args:
        id_solicitud (int): Identificador de la solicitud consultada.

    Returns:
        QuerySet[AsignacionSolicitud]: Consulta sin evaluar. No impone unicidad,
        orden ni bloqueos; cada operación debe resolver esas condiciones.
    """
    return AsignacionSolicitud.objects.filter(
        id_solicitud_id=id_solicitud,
        estado="ACTIVA",
        fecha_fin__isnull=True,
    )
