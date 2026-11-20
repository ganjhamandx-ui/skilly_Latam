
"""Asigna responsables con bloqueo transaccional para evitar carreras."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import serializers, status
from rest_framework.response import Response

from acceso.models import Usuario
from solicitudes.models import SolicitudServicio

from .models import AsignacionSolicitud
from .vigencia_asignacion import asignaciones_vigentes
from .views import (
    AsignacionSolicitudAdministracionView,
    AsignacionSolicitudAdministracionSerializer,
    registrar_evento_trazabilidad,
)


def error_asignacion(mensaje, codigo):
    """Devuelve un error controlado de asignación.

    Args:
        mensaje (str): Explicación del rechazo sin datos privados.
        codigo (int): Estado HTTP correspondiente.

    Returns:
        Response: Objeto con ``mensaje`` y el estado indicado.
    """

    return Response(
        {"mensaje": mensaje},
        status=codigo,
    )


@method_decorator(csrf_protect, name="dispatch")
class AsignacionSolicitudSeguraAdministracionView(
    AsignacionSolicitudAdministracionView
):
    """Serializa asignaciones administrativas y evita responsables duplicados."""

    # Conserva el GET y los permisos existentes.

    def post(self, request, id_solicitud):
        """Asigna un administrador activo sin reemplazar responsables vigentes.

        Args:
            request (Request): Sesión administrativa con CSRF. El cuerpo admite
                solo ``modo`` e ``id_usuario_skilly``; AUTOASIGNAR usa al usuario
                actual y prohíbe destino explícito, ASIGNAR exige un id positivo.
            id_solicitud (int): Solicitud que se bloqueará antes de validar vigencia.

        Returns:
            Response: HTTP 201 con asignación ACTIVA de tipo MANUAL; HTTP 400 por
            entrada o administrador inválidos y 409 si ya está coordinada o asignada.
            La trazabilidad distingue el modo aunque ambos guarden tipo MANUAL.

        Raises:
            Http404: Si la solicitud no existe; DRF responde HTTP 404.
        """
        datos = request.data

        if not hasattr(datos, "get") or not hasattr(
            datos, "keys"
        ):
            return error_asignacion(
                "Debe enviar un objeto con los datos "
                "de asignacion.",
                status.HTTP_400_BAD_REQUEST,
            )

        campos_permitidos = {
            "modo",
            "id_usuario_skilly",
        }

        desconocidos = (
            set(datos.keys()) - campos_permitidos
        )

        if desconocidos:
            return error_asignacion(
                "La solicitud contiene campos "
                "no permitidos.",
                status.HTTP_400_BAD_REQUEST,
            )

        modo = str(
            datos.get("modo", "")
        ).strip().upper()

        if modo not in {
            "AUTOASIGNAR",
            "ASIGNAR",
        }:
            return error_asignacion(
                "El modo debe ser AUTOASIGNAR "
                "o ASIGNAR.",
                status.HTTP_400_BAD_REQUEST,
            )

        id_destino = None

        if modo == "AUTOASIGNAR":
            if "id_usuario_skilly" in datos:
                return error_asignacion(
                    "No debe indicar un usuario "
                    "destino en la autoasignacion.",
                    status.HTTP_400_BAD_REQUEST,
                )

            id_destino = request.user.pk

        else:
            campo_usuario = (
                serializers.IntegerField(
                    min_value=1
                )
            )

            try:
                id_destino = (
                    campo_usuario.run_validation(
                        datos.get("id_usuario_skilly")
                    )
                )

            except serializers.ValidationError:
                return error_asignacion(
                    "Debe indicar un "
                    "id_usuario_skilly valido.",
                    status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            # Bloquea la solicitud antes de comprobar
            # si ya tiene un responsable activo.
            solicitud = get_object_or_404(
                SolicitudServicio.objects
                .select_for_update(),
                pk=id_solicitud,
            )

            # No reabrir automáticamente coordinaciones históricas.
            # La reasignación de casos ya coordinados requiere un flujo
            # explícito que hoy no está implementado.
            if solicitud.estado == "COORDINADA":
                return error_asignacion(
                    "La solicitud ya está coordinada; no puede "
                    "volver a asignarse desde la bandeja inicial.",
                    status.HTTP_409_CONFLICT,
                )

            asignacion_activa = asignaciones_vigentes(solicitud.pk).exists()

            if asignacion_activa:
                return error_asignacion(
                    "La solicitud ya tiene un "
                    "responsable interno asignado. "
                    "No se permite reemplazarlo "
                    "automaticamente.",
                    status.HTTP_409_CONFLICT,
                )

            # El bloqueo del destinatario mantiene estable su estado durante el alta.
            usuario_destino = (
                Usuario.objects
                .select_for_update()
                .filter(
                    pk=id_destino,
                    rol="ADMIN_SKILLY",
                    estado="ACTIVO",
                )
                .first()
            )

            if usuario_destino is None:
                return error_asignacion(
                    "El usuario indicado no es un "
                    "administrador Skilly activo.",
                    status.HTTP_400_BAD_REQUEST,
                )

            asignacion = (
                AsignacionSolicitud.objects.create(
                    id_solicitud=solicitud,
                    id_usuario_skilly=usuario_destino,
                    tipo_asignacion="MANUAL",
                    fecha_asignacion=timezone.now(),
                    fecha_fin=None,
                    estado="ACTIVA",
                )
            )

            # El evento distingue autoasignación de asignación a otra persona.
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="asignacion_solicitud",
                entidad_id=asignacion.pk,
                accion=modo,
                detalle_resumido=(
                    f"Solicitud {solicitud.pk} "
                    f"asignada al usuario interno "
                    f"{usuario_destino.pk}. "
                    f"Modo: {modo}."
                )[:255],
            )

            resultado = (
                AsignacionSolicitudAdministracionSerializer(
                    asignacion
                ).data
            )

        return Response(
            {
                "mensaje": (
                    "Solicitud asignada "
                    "correctamente."
                ),
                "asignacion": resultado,
            },
            status=status.HTTP_201_CREATED,
        )
