"""Control transaccional del responsable para escrituras administrativas.

No altera las bandejas de lectura ni el procedimiento de asignación.
"""
from functools import wraps

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from solicitudes.models import SolicitudServicio
from .models import PrestacionServicio
from .vigencia_asignacion import asignaciones_vigentes


def _denegacion(mensaje, codigo):
    return Response({"mensaje": mensaje}, status=codigo)


def _verificar_responsable(request, id_solicitud):
    # Bloquear la misma fila que utiliza el procedimiento de asignación,
    # de modo que asignación y operación administrativa se serialicen.
    existe = (SolicitudServicio.objects.select_for_update(of=("self",))
              .filter(pk=id_solicitud).exists())
    if not existe:
        return _denegacion("La solicitud no existe.", status.HTTP_404_NOT_FOUND)

    responsables = list(
        asignaciones_vigentes(id_solicitud).values_list("id_usuario_skilly_id", flat=True)[:2]
    )
    if not responsables:
        return _denegacion(
            "La solicitud debe asignarse antes de gestionarla.",
            status.HTTP_409_CONFLICT,
        )
    if len(responsables) != 1:
        return _denegacion(
            "La solicitud tiene asignaciones activas inconsistentes.",
            status.HTTP_409_CONFLICT,
        )
    if responsables[0] != request.user.pk:
        return _denegacion(
            "La solicitud está asignada a otra persona de administración.",
            status.HTTP_403_FORBIDDEN,
        )
    return None


def requiere_responsable_solicitud(funcion):
    @wraps(funcion)
    def protegido(self, request, id_solicitud, *args, **kwargs):
        with transaction.atomic():
            rechazo = _verificar_responsable(request, id_solicitud)
            if rechazo is not None:
                return rechazo
            return funcion(self, request, id_solicitud, *args, **kwargs)
    return protegido


def requiere_responsable_prestacion(funcion):
    @wraps(funcion)
    def protegido(self, request, id_prestacion, *args, **kwargs):
        with transaction.atomic():
            id_solicitud = (PrestacionServicio.objects.filter(pk=id_prestacion)
                            .values_list("id_solicitud_id", flat=True).first())
            if id_solicitud is None:
                return _denegacion(
                    "La prestación no existe.", status.HTTP_404_NOT_FOUND,
                )
            rechazo = _verificar_responsable(request, id_solicitud)
            if rechazo is not None:
                return rechazo
            return funcion(self, request, id_prestacion, *args, **kwargs)
    return protegido
