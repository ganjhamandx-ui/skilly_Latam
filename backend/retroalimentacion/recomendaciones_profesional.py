from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional
from profesionales.models import Profesional

from .models import RecomendacionDesarrollo
from .serializers import (
    RecomendacionDesarrolloProfesionalSerializer,
)


class MisRecomendacionesProfesionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()

        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional no "
                        "se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        recomendaciones = (
            RecomendacionDesarrollo.objects
            .filter(
                id_profesional=profesional,
                estado=(
                    RecomendacionDesarrollo
                    .Estado.COMUNICADA
                ),
                fecha_comunicacion__isnull=False,
            )
            .order_by(
                "-fecha_comunicacion",
                "-id_recomendacion",
            )
        )

        serializer = (
            RecomendacionDesarrolloProfesionalSerializer(
                recomendaciones,
                many=True,
            )
        )

        return Response(
            {
                "recomendaciones": serializer.data,
                "total": len(serializer.data),
            },
            status=status.HTTP_200_OK,
        )


class DetalleRecomendacionProfesionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(
        self,
        request,
        id_recomendacion,
    ):
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()

        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional no "
                        "se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        recomendacion = (
            RecomendacionDesarrollo.objects
            .filter(
                id_recomendacion=id_recomendacion,
                id_profesional=profesional,
                estado=(
                    RecomendacionDesarrollo
                    .Estado.COMUNICADA
                ),
                fecha_comunicacion__isnull=False,
            )
            .first()
        )

        if recomendacion is None:
            return Response(
                {
                    "mensaje": (
                        "La recomendacion no existe "
                        "o no se encuentra disponible "
                        "para este profesional."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            RecomendacionDesarrolloProfesionalSerializer(
                recomendacion
            )
        )

        return Response(
            {
                "recomendacion": serializer.data,
            },
            status=status.HTTP_200_OK,
        )