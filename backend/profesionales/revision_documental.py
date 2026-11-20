"""Reglas compartidas de revisión documental: cada documento es individual.

REEMPLAZADA mantiene el vínculo histórico y excluye esa versión del
cómputo actual. Nunca inferimos versiones solo por tipo (puede haber
varios certificados independientes con el mismo tipo).
"""

from .models import ValidacionDocumento


def documentos_vigentes(solicitud, bloquear=False):
    """Obtiene las revisiones que no fueron sustituidas por otra versión.

    Args:
        solicitud: SolicitudValidacion cuyas revisiones se consultan.
        bloquear (bool): Solicita select_for_update; el llamador debe mantener
            una transacción cuando el motor requiera ese contexto.

    Returns:
        list[ValidacionDocumento]: Revisiones con su documento relacionado,
        ordenadas por identificador de documento y sin estado REEMPLAZADA.
    """
    qs = (ValidacionDocumento.objects
          .select_related("id_documento")
          .filter(id_validacion=solicitud)
          .exclude(estado_revision="REEMPLAZADA"))
    if bloquear:
        qs = qs.select_for_update()
    return list(qs.order_by("id_documento_id"))


def revision_completa(solicitud):
    """Comprueba que exista al menos un documento vigente y todos estén aprobados.

    Args:
        solicitud: Solicitud de validación y profesional esperado.

    Returns:
        bool: True si cada revisión vigente está APROBADA y pertenece al mismo
        profesional de la solicitud. Una colección vacía devuelve False.
    """
    vigentes = documentos_vigentes(solicitud)
    return bool(vigentes) and all(
        v.estado_revision == "APROBADA"
        and v.id_documento.id_profesional_id == solicitud.id_profesional_id
        for v in vigentes
    )
