
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
