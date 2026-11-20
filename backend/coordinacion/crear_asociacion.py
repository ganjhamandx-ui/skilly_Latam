"""Crea asociaciones profesionales después de validar permisos y estado."""

from .control_responsable import requiere_responsable_solicitud
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from backoffice.services import registrar_evento_trazabilidad

from solicitudes.models import (
    SolicitudServicio,
    ReservaDisponibilidad,
)

from .models import (
    SolicitudProfesional,
    PrestacionServicio,
)

from .serializers import (
    AsociacionSolicitudProfesionalSerializer,
)


class CrearAsociacionSolicitudProfesionalView(APIView):
    """Propone al profesional del servicio seleccionado bajo control del responsable.

    La asociación pendiente prepara la coordinación; no equivale a contratación
    ni pago. Exige una sesión administrativa y protección CSRF por autenticación.
    """
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
        """Crea una asociación pendiente para una solicitud recibida y reservada.

        Args:
            request (Request): Petición del administrador responsable de la solicitud.
            id_solicitud (int): Solicitud RECIBIDA con un servicio seleccionado.
            id_profesional (int): Profesional que debe coincidir con el del servicio.

        Returns:
            Response: HTTP 201 con asociación PROPUESTO/PENDIENTE y trazabilidad;
            HTTP 404 si falta solicitud o 409 por estado, profesional, reserva,
            asociación previa o prestación ya preparada. El decorador también
            rechaza ausencia de responsable, duplicidad de asignaciones o ajenidad.
        """
        with transaction.atomic():
            solicitud = (
                SolicitudServicio.objects
                .select_for_update(of=("self",))
                .filter(id_solicitud=id_solicitud)
                .first()
            )

            if solicitud is None:
                return Response(
                    {"mensaje": "La solicitud no existe."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if solicitud.estado != "RECIBIDA":
                return Response(
                    {
                        "mensaje": (
                            "La solicitud no se encuentra "
                            "en estado RECIBIDA."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if solicitud.id_servicio_id is None:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud no tiene un "
                            "servicio seleccionado."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if (
                solicitud.id_servicio.id_profesional_id
                != id_profesional
            ):
                return Response(
                    {
                        "mensaje": (
                            "El profesional no corresponde "
                            "al servicio seleccionado."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            reserva_valida = (
                ReservaDisponibilidad.objects
                .filter(
                    id_solicitud_id=id_solicitud,
                    id_disponibilidad__id_profesional_id=(
                        id_profesional
                    ),
                    estado__in=[
                        "PENDIENTE_PAGO",
                        "ACTIVA",
                    ],
                )
                .exists()
            )

            if not reserva_valida:
                return Response(
                    {
                        "mensaje": (
                            "No existe una reserva vigente "
                            "para este profesional."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            asociacion_existente = (
                SolicitudProfesional.objects
                .filter(
                    id_solicitud_id=id_solicitud,
                    id_profesional_id=id_profesional,
                )
                .exists()
            )

            if asociacion_existente:
                return Response(
                    {
                        "mensaje": (
                            "La asociacion profesional "
                            "ya existe."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            otra_asociacion = (
                SolicitudProfesional.objects
                .filter(
                    id_solicitud_id=id_solicitud
                )
                .exclude(
                    id_profesional_id=id_profesional
                )
                .exists()
            )

            if otra_asociacion:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud ya tiene una "
                            "asociacion con otro profesional."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if PrestacionServicio.objects.filter(
                id_solicitud_id=id_solicitud
            ).exists():
                return Response(
                    {
                        "mensaje": (
                            "La solicitud ya posee una "
                            "prestacion preparada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            asociacion = (
                SolicitudProfesional.objects.create(
                    id_solicitud=solicitud,
                    id_profesional_id=id_profesional,
                    tipo_asociacion="PROPUESTO",
                    estado="PENDIENTE",
                    fecha_asociacion=timezone.now(),
                )
            )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="solicitud_profesional",
                entidad_id=id_solicitud,
                accion="CREAR_ASOCIACION",
                detalle_resumido=(
                    f"Asociacion propuesta para solicitud "
                    f"{id_solicitud} y profesional "
                    f"{id_profesional}. "
                    f"Estado provisional: PENDIENTE."
                )[:255],
            )

            datos = (
                AsociacionSolicitudProfesionalSerializer(
                    asociacion
                ).data
            )

        return Response(
            {
                "mensaje": (
                    "Asociacion registrada como PENDIENTE. "
                    "No implica pago ni contratacion."
                ),
                "asociacion": datos,
            },
            status=status.HTTP_201_CREATED,
        )


class ProponerAsociacionSolicitudProfesionalView(
    CrearAsociacionSolicitudProfesionalView
):
    """Resuelve el profesional desde el servicio para reutilizar el alta validada."""
    @requiere_responsable_solicitud
    def post(self, request, id_solicitud):
        """Propone al profesional elegido en el catálogo por la organización.

        Args:
            request (Request): Petición administrativa con control de responsable.
            id_solicitud (int): Solicitud de la que se obtiene el servicio.

        Returns:
            Response: HTTP 404 si falta la solicitud, 409 si carece de servicio
            o la respuesta de creación de la vista base con todas sus validaciones.
        """
        solicitud = (
            SolicitudServicio.objects
            .select_related("id_servicio")
            .filter(id_solicitud=id_solicitud)
            .first()
        )

        if solicitud is None:
            return Response(
                {"mensaje": "La solicitud no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if solicitud.id_servicio_id is None:
            return Response(
                {
                    "mensaje": (
                        "La solicitud no tiene un servicio "
                        "seleccionado."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        profesional_id = (
            solicitud.id_servicio.id_profesional_id
        )

        return super().post(
            request,
            id_solicitud=id_solicitud,
            id_profesional=profesional_id,
        )
