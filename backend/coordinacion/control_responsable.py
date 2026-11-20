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
    """Construye una respuesta de denegación para el control de responsable.

    Args:
        mensaje (str): Explicación que puede mostrarse al administrador.
        codigo (int): Estado HTTP de la denegación.

    Returns:
        Response: Cuerpo con la clave ``mensaje`` y el estado recibido.
    """

    return Response({"mensaje": mensaje}, status=codigo)


def _verificar_responsable(request, id_solicitud):
    """Bloquea la solicitud y comprueba la responsabilidad administrativa única.

    Args:
        request (Request): Petición ya autenticada y autorizada por rol.
        id_solicitud (int): Solicitud que se pretende modificar.

    Returns:
        Response | None: ``None`` si el único responsable vigente es el usuario;
        HTTP 404 si falta la solicitud, 409 si no tiene una asignación única y
        403 si está asignada a otra persona.

    Note:
        Debe llamarse dentro de una transacción activa. El bloqueo se conserva
        hasta su cierre para serializar la operación con nuevas asignaciones.
    """

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
    """Decora una operación de solicitud con control de responsable y transacción.

    Args:
        funcion (Callable): Método con ``self``, ``request`` e ``id_solicitud``.

    Returns:
        Callable: Método que devuelve la denegación del control o el resultado
        original. Los argumentos adicionales y las excepciones se propagan.
    """

    @wraps(funcion)
    def protegido(self, request, id_solicitud, *args, **kwargs):
        """Ejecuta el método solo después de validar y bloquear su solicitud."""
        with transaction.atomic():
            rechazo = _verificar_responsable(request, id_solicitud)
            if rechazo is not None:
                return rechazo
            return funcion(self, request, id_solicitud, *args, **kwargs)
    return protegido


def requiere_responsable_prestacion(funcion):
    """Decora una operación de prestación con control de su solicitud asociada.

    Args:
        funcion (Callable): Método con ``self``, ``request`` e ``id_prestacion``.

    Returns:
        Callable: Método transaccional que devuelve HTTP 404 si falta la prestación,
        la denegación del responsable o el resultado original. No sustituye los
        permisos por rol de la vista ni captura excepciones del método decorado.
    """

    @wraps(funcion)
    def protegido(self, request, id_prestacion, *args, **kwargs):
        """Resuelve la solicitud y conserva su bloqueo durante el método protegido."""
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
