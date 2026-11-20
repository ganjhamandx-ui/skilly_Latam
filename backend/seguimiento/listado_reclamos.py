"""Lista reclamos para administración aplicando permisos por rol."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly

from .models import ReclamoPrestacion
from .serializers import ReclamoPrestacionSerializer


class ListadoReclamosAdministracionView(APIView):
    """
    Consulta administrativa de reclamos.

    Solo permite GET.
    No modifica reclamos, resoluciones ni pagos.
    """

    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        """Lista reclamos por fecha e identificador descendentes para administración.

        Args:
            request: Petición autenticada con estado opcional en query_params;
                el filtro elimina espacios externos y compara el texto exacto.

        Returns:
            Response: 200 con cantidad y reclamos, sin paginación. Un estado que
            no coincide con registros produce una lista vacía, no un error.
        """
        reclamos = (
            ReclamoPrestacion.objects
            .order_by(
                "-fecha_registro",
                "-id_reclamo",
            )
        )

        # Filtro opcional por estado.
        estado = request.query_params.get(
            "estado", ""
        ).strip()

        if estado:
            reclamos = reclamos.filter(
                estado=estado
            )

        serializer = ReclamoPrestacionSerializer(
            reclamos,
            many=True,
        )

        return Response(
            {
                "cantidad": len(serializer.data),
                "reclamos": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
