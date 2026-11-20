"""Resuelve el seguimiento privado de una solicitud mediante referencia firmada."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SolicitudServicio
from .referencias import leer_referencia_seguimiento
from .serializers import (
    SeguimientoSolicitudServicioSerializer,
)


class SeguimientoSolicitudServicioPublicaView(
    APIView
):
    """Consulta el estado de una solicitud mediante su referencia privada firmada."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(
        self,
        request,
        referencia,
    ):
        """Devuelve seguimiento acotado tras comprobar firma y vínculo con el contacto.

        Args:
            request (Request): Petición pública sin requisito de sesión.
            referencia (str): Referencia privada de la solicitud y su contacto.

        Returns:
            Response: HTTP 200 con referencia y solicitud sin contacto empresarial;
            HTTP 404 con el mismo mensaje para firma inválida o relación inexistente.
        """
        datos_referencia = (
            leer_referencia_seguimiento(
                referencia
            )
        )

        if datos_referencia is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es válida."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        solicitud = (
            SolicitudServicio.objects
            .select_related(
                "id_empresa",
                "id_contacto",
                "id_servicio",
            )
            .filter(
                id_solicitud=(
                    datos_referencia[
                        "id_solicitud"
                    ]
                ),
                id_contacto_id=(
                    datos_referencia[
                        "id_contacto"
                    ]
                ),
            )
            .first()
        )

        if solicitud is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es válida."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            SeguimientoSolicitudServicioSerializer(
                solicitud
            )
        )

        return Response(
            {
                "referencia_seguimiento": referencia,
                "solicitud": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
