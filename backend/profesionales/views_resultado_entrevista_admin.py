"""Resolucion administrativa final de una entrevista de validacion profesional.

Esta vista NO aprueba documentos ni registra reservas. Preserva el flujo
separado de revision documental, entrevista y habilitacion del perfil.
"""

from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly

from .models import (
    EntrevistaValidacion,
    Profesional,
    SolicitudValidacion,
    ValidacionDocumento,
)
from .serializers import RevisionValidacionAdministracionSerializer
from .revision_documental import documentos_vigentes


class ResultadoEntrevistaAdminSerializer(serializers.Serializer):
    resultado = serializers.ChoiceField(choices=["APROBADO", "RECHAZADO"])
    observacion = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=2000,
    )
    confirmacion_realizada = serializers.BooleanField(required=True)

    def validate_confirmacion_realizada(self, valor):
        if valor is not True:
            raise serializers.ValidationError(
                "Debe confirmar que la entrevista se realizo antes de resolver."
            )
        return valor


@method_decorator(csrf_protect, name="dispatch")
class ResolverEntrevistaYValidacionAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["post", "options"]

    def post(self, request, id_validacion):
        entrada = ResultadoEntrevistaAdminSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)

        resultado = entrada.validated_data["resultado"]
        observacion = entrada.validated_data["observacion"]

        with transaction.atomic():
            solicitud = (
                SolicitudValidacion.objects
                .select_for_update()
                .filter(id_validacion=id_validacion)
                .first()
            )
            if solicitud is None:
                return Response(
                    {"mensaje": "La solicitud de validacion no existe."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if solicitud.estado != "APROBADA":
                return Response(
                    {"mensaje": "Primero debe aprobarse la revision documental."},
                    status=status.HTTP_409_CONFLICT,
                )

            profesional = (
                Profesional.objects
                .select_for_update()
                .filter(pk=solicitud.id_profesional_id)
                .first()
            )
            if profesional is None:
                return Response(
                    {"mensaje": "El profesional asociado no existe."},
                    status=status.HTTP_409_CONFLICT,
                )

            if profesional.estado_validacion != "PENDIENTE":
                return Response(
                    {"mensaje": "El perfil ya tiene una validacion final registrada."},
                    status=status.HTTP_409_CONFLICT,
                )

            vigentes = documentos_vigentes(solicitud, bloquear=True)
            if not vigentes or any(
                vinculo.estado_revision != "APROBADA"
                or vinculo.id_documento.id_profesional_id != profesional.pk
                for vinculo in vigentes
            ):
                return Response(
                    {"mensaje": "Existen documentos vigentes sin aprobar."},
                    status=status.HTTP_409_CONFLICT,
                )

            entrevista = (
                EntrevistaValidacion.objects
                .select_for_update()
                .select_related("id_bloque_entrevista")
                .filter(id_validacion=solicitud)
                .order_by("-fecha_reserva", "-id_entrevista")
                .first()
            )
            if entrevista is None:
                return Response(
                    {"mensaje": "Debe existir una entrevista reservada para esta solicitud."},
                    status=status.HTTP_409_CONFLICT,
                )

            if entrevista.estado != "AGENDADA":
                return Response(
                    {"mensaje": "La entrevista ya esta resuelta o no puede finalizarse."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Una confirmacion manual no permite resolver entrevistas futuras.
            # Se usa la zona horaria configurada en Django (America/Santiago).
            bloque = entrevista.id_bloque_entrevista
            if not bloque or not bloque.fecha or not bloque.hora_fin:
                return Response(
                    {"mensaje": "La entrevista no tiene un horario valido."},
                    status=status.HTTP_409_CONFLICT,
                )

            fin_programado = datetime.combine(bloque.fecha, bloque.hora_fin)
            if timezone.is_naive(fin_programado):
                fin_programado = timezone.make_aware(
                    fin_programado, timezone.get_current_timezone()
                )

            if timezone.now() < fin_programado:
                return Response(
                    {
                        "mensaje": (
                            "Aun no ha finalizado el horario programado "
                            "para esta entrevista. No puede registrarse "
                            "su resultado anticipadamente."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # La administracion certifica la evaluacion mediante la casilla
            # y observacion obligatoria, despues del horario programado.
            # Se registra en el modelo existente, sin nuevas tablas.
            revisor = getattr(request.user, "pk", None)
            marca = timezone.now().isoformat()
            entrevista.estado = "REALIZADA"
            entrevista.observacion = (
                f"Resultado: {resultado}. "
                f"Revisor SKILLY ID: {revisor}. "
                f"Fecha de decision: {marca}. "
                f"Observacion: {observacion}"
            )
            entrevista.save(update_fields=["estado", "observacion"])

            profesional.estado_validacion = resultado
            profesional.save(update_fields=["estado_validacion"])

            # Volvemos a consultar luego de la actualizacion para presentar
            # el estado final, evitando respuestas parcialmente desfasadas.
            solicitud.refresh_from_db()
            salida = RevisionValidacionAdministracionSerializer(solicitud).data

        return Response(
            {
                "mensaje": (
                    "Entrevista registrada y perfil profesional aprobado."
                    if resultado == "APROBADO"
                    else "Entrevista registrada y perfil profesional rechazado."
                ),
                "solicitud": salida,
            },
            status=status.HTTP_200_OK,
        )
