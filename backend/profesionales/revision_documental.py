"""Reglas compartidas de revisión documental: cada documento es individual.

REEMPLAZADA mantiene el vínculo histórico y excluye esa versión del
cómputo actual. Nunca inferimos versiones solo por tipo (puede haber
varios certificados independientes con el mismo tipo).
"""

from .models import ValidacionDocumento


def documentos_vigentes(solicitud, bloquear=False):
    qs = (ValidacionDocumento.objects
          .select_related("id_documento")
          .filter(id_validacion=solicitud)
          .exclude(estado_revision="REEMPLAZADA"))
    if bloquear:
        qs = qs.select_for_update()
    return list(qs.order_by("id_documento_id"))


def revision_completa(solicitud):
    vigentes = documentos_vigentes(solicitud)
    return bool(vigentes) and all(
        v.estado_revision == "APROBADA"
        and v.id_documento.id_profesional_id == solicitud.id_profesional_id
        for v in vigentes
    )
