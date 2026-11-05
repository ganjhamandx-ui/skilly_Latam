
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional

from profesionales.models import (
    Profesional,
    DocumentoProfesional,
    SolicitudValidacion,
    ValidacionDocumento,
)
from profesionales.serializers import EstadoValidacionSerializer


class SolicitarMiValidacionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    http_method_names = ["post", "options"]

    def post(self, request):
        with transaction.atomic():
            profesional = (
                Profesional.objects
                .select_for_update()
                .filter(id_usuario=request.user)
                .first()
            )

            if profesional is None:
                return Response(
                    {"mensaje": "Debes completar tu perfil profesional."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            existente = (
                SolicitudValidacion.objects
                .filter(id_profesional=profesional)
                .order_by("-fecha_solicitud", "-id_validacion")
                .first()
            )

            if existente is not None:
                return Response(
                    {
                        "mensaje": (
                            "Ya existe una solicitud de validacion. "
                            "Consulta su estado antes de enviar otra."
                        ),
                        "solicitud": EstadoValidacionSerializer(
                            existente
                        ).data,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            documentos = list(
                DocumentoProfesional.objects
                .filter(id_profesional=profesional)
                .order_by("id_documento")
            )

            if not documentos:
                return Response(
                    {
                        "mensaje": (
                            "Debes adjuntar al menos un documento "
                            "antes de enviar tu solicitud."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            solicitud = SolicitudValidacion.objects.create(
                id_profesional=profesional,
                id_revisor_skilly=None,
                estado="PENDIENTE",
                fecha_solicitud=timezone.now(),
                fecha_asignacion=None,
                fecha_revision=None,
                observacion_resultado=None,
            )

            for documento in documentos:
                ValidacionDocumento.objects.create(
                    id_validacion=solicitud,
                    id_documento=documento,
                    estado_revision="PENDIENTE",
                    observacion=None,
                )

        return Response(
            {
                "mensaje": (
                    "Solicitud de validacion enviada correctamente."
                ),
                "solicitud": EstadoValidacionSerializer(
                    solicitud
                ).data,
                "documentos_asociados": len(documentos),
            },
            status=status.HTTP_201_CREATED,
        )
