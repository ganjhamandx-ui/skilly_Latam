"""Confirma administrativamente asociaciones entre solicitudes y profesionales."""

from .control_responsable import requiere_responsable_solicitud
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import (
    SesionSkillyAuthentication,
)
from acceso.permissions import (
    EsAdministracionSkilly,
)
from backoffice.services import (
    registrar_evento_trazabilidad,
)
from solicitudes.models import SolicitudServicio

from .models import SolicitudProfesional
from .serializers import (
    AsociacionSolicitudProfesionalSerializer,
)


class ConfirmarAsociacionSolicitudProfesionalView(
    APIView
):
    """Permite al administrador responsable marcar una asociación como aceptada."""

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
        """Confirma la asociación existente y registra el acto administrativo.

        Args:
            request (Request): Sesión administrativa responsable con CSRF válido.
            id_solicitud (int): Solicitud protegida por el control de responsable.
            id_profesional (int): Profesional de la asociación que se bloqueará.

        Returns:
            Response: HTTP 200 con asociación ACEPTADO, incluso si ya tenía ese
            estado; HTTP 404 si falta la asociación. Cada llamada admitida registra
            trazabilidad. No crea prestaciones ni acepta en nombre de una sesión profesional.

        Raises:
            Http404: Si la solicitud no existe al recuperarla.
        """
        solicitud = get_object_or_404(
            SolicitudServicio,
            id_solicitud=id_solicitud,
        )

        with transaction.atomic():
            asociacion = (
                SolicitudProfesional.objects
                .select_for_update()
                .filter(
                    id_solicitud=solicitud,
                    id_profesional_id=id_profesional,
                )
                .first()
            )

            if asociacion is None:
                return Response(
                    {
                        "mensaje": (
                            "No existe una asociación entre "
                            "la solicitud y el profesional "
                            "indicados."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if asociacion.estado != "ACEPTADO":
                asociacion.estado = "ACEPTADO"

                asociacion.save(
                    update_fields=[
                        "estado",
                    ]
                )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo=(
                    "solicitud_profesional"
                ),
                entidad_id=(
                    solicitud.id_solicitud
                ),
                accion=(
                    "CONFIRMAR_ASOCIACION"
                ),
                detalle_resumido=(
                    f"Skilly confirmó la asociación "
                    f"de la solicitud "
                    f"{solicitud.id_solicitud} "
                    f"con el profesional "
                    f"{id_profesional}. "
                    f"Tipo de asociación: "
                    f"{asociacion.tipo_asociacion}."
                )[:255],
            )

        serializer = (
            AsociacionSolicitudProfesionalSerializer(
                asociacion
            )
        )

        return Response(
            {
                "mensaje": (
                    "Asociación confirmada "
                    "correctamente por Skilly."
                ),
                "asociacion": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
