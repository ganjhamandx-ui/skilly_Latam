"""Construye y consulta prestaciones derivadas de solicitudes aprobadas."""

from .control_responsable import requiere_responsable_solicitud
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from backoffice.services import registrar_evento_trazabilidad
from solicitudes.models import SolicitudServicio

from .models import (
    CoordinacionSolicitud,
    PrestacionServicio,
    SolicitudProfesional,
)
from .serializers import PrestacionServicioAdministracionSerializer


class PrepararPrestacionServicioAdministracionView(APIView):
    """Prepara la prestación desde una asociación aceptada sin formalizar el contrato."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    @requiere_responsable_solicitud
    def post(
        self,
        request,
        id_solicitud,
        id_profesional,
    ):
        """Crea la prestación pendiente o devuelve la existente del mismo profesional.

        Args:
            request (Request): Sesión administrativa responsable con CSRF válido.
            id_solicitud (int): Solicitud que se bloqueará junto con su asociación.
            id_profesional (int): Profesional cuya asociación debe estar ACEPTADO.

        Returns:
            Response: HTTP 201 con prestación PENDIENTE_CONTRATACION al crearla;
            HTTP 200 si ya existe para ese profesional; 404 si falta la solicitud
            y 409 si falta la asociación aceptada o la prestación pertenece a otro.
            Solo una creación registra la coordinación y actualiza la solicitud.

        Raises:
            PrestacionServicio.DoesNotExist: Si desaparece el registro antes
                de recargarlo para serializar la respuesta.
        """
        ahora = timezone.now()

        with transaction.atomic():
            solicitud = (
                SolicitudServicio.objects
                .select_for_update()
                .filter(
                    id_solicitud=id_solicitud
                )
                .first()
            )

            if solicitud is None:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud indicada no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            asociacion = (
                SolicitudProfesional.objects
                .select_for_update()
                .filter(
                    id_solicitud_id=id_solicitud,
                    id_profesional_id=id_profesional,
                    estado="ACEPTADO",
                )
                .first()
            )

            if asociacion is None:
                return Response(
                    {
                        "mensaje": (
                            "El profesional indicado no posee "
                            "una asociación confirmada con "
                            "esta solicitud."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            prestacion_existente = (
                PrestacionServicio.objects
                .select_for_update()
                .filter(
                    id_solicitud_id=id_solicitud
                )
                .first()
            )

            if prestacion_existente is not None:
                if (
                    prestacion_existente.id_profesional_id
                    != id_profesional
                ):
                    return Response(
                        {
                            "mensaje": (
                                "La solicitud ya posee una "
                                "prestación asociada a otro "
                                "profesional."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                prestacion = prestacion_existente

                creada = False

            else:
                prestacion = (
                    PrestacionServicio.objects.create(
                        id_solicitud=solicitud,
                        id_profesional_id=id_profesional,
                        condiciones_comunicadas=None,
                        estado="PENDIENTE_CONTRATACION",
                        fecha_confirmacion=None,
                        fecha_inicio=None,
                        fecha_fin=None,
                        fecha_cierre=None,
                    )
                )

                CoordinacionSolicitud.objects.create(
                    id_solicitud=solicitud,
                    id_usuario_skilly=request.user,
                    tipo="PREPARAR_PRESTACION",
                    detalle=(
                        f"Prestación "
                        f"{prestacion.id_prestacion} creada "
                        f"para el profesional "
                        f"{id_profesional} antes de la "
                        f"contratación formal."
                    ),
                    estado_resultante=solicitud.estado,
                    fecha_registro=ahora,
                )

                solicitud.fecha_actualizacion = ahora

                solicitud.save(
                    update_fields=[
                        "fecha_actualizacion",
                    ]
                )

                registrar_evento_trazabilidad(
                    usuario=request.user,
                    entidad_tipo="prestacion_servicio",
                    entidad_id=prestacion.id_prestacion,
                    accion="PREPARAR_PRESTACION",
                    detalle_resumido=(
                        f"Prestación creada para solicitud "
                        f"{id_solicitud} y profesional "
                        f"{id_profesional}. "
                        f"Estado inicial: "
                        f"PENDIENTE_CONTRATACION."
                    )[:255],
                )

                creada = True

        prestacion = (
            PrestacionServicio.objects
            .select_related(
                "id_profesional"
            )
            .get(
                id_prestacion=prestacion.id_prestacion
            )
        )

        serializer = (
            PrestacionServicioAdministracionSerializer(
                prestacion
            )
        )

        if creada:
            return Response(
                {
                    "mensaje": (
                        "Prestación preparada correctamente. "
                        "Permanece pendiente de contratación "
                        "hasta que exista pago realizado y "
                        "primera reunión agendada."
                    ),
                    "prestacion": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "mensaje": (
                    "La prestación ya se encontraba "
                    "preparada para esta solicitud."
                ),
                "prestacion": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
