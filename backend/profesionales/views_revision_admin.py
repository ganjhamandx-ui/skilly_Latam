"""Registra decisiones administrativas sobre documentos profesionales."""

from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly

from .models import SolicitudValidacion, ValidacionDocumento, DocumentoProfesional
from .serializers import RevisionValidacionAdministracionSerializer
from .revision_documental import documentos_vigentes


@method_decorator(csrf_protect, name="dispatch")
class ResolverValidacionDocumentalAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["post", "options"]

    def post(self, request, id_validacion):
        accion = str(request.data.get("accion") or "").strip().upper()
        observacion = str(
            request.data.get("observacion") or ""
        ).strip()

        if accion not in (
            "INICIAR_REVISION",
            "APROBAR",
            "RECHAZAR",
            "REVISAR_DOCUMENTO",
            "FINALIZAR_REVISION",
        ):
            return Response(
                {"mensaje": "Accion administrativa no permitida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = str(request.data.get("decision") or "").strip().upper()
        if accion == "REVISAR_DOCUMENTO" and decision not in ("APROBADA", "RECHAZADA"):
            return Response({"mensaje": "Debes aprobar o rechazar el documento."}, status=400)
        if (accion == "REVISAR_DOCUMENTO" and decision == "RECHAZADA" and not observacion):
            return Response({"mensaje": "Explica por que se rechaza el documento."}, status=400)
        if accion == "RECHAZAR" and not observacion:
            return Response(
                {"mensaje": "El rechazo requiere una observacion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(observacion) > 4000:
            return Response(
                {"mensaje": "La observacion supera 4000 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            solicitud = (
                SolicitudValidacion.objects
                .select_for_update()
                .select_related(
                    "id_profesional",
                    "id_profesional__id_usuario",
                )
                .filter(id_validacion=id_validacion)
                .first()
            )

            if solicitud is None:
                return Response(
                    {"mensaje": "La solicitud no existe."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            estado_actual = str(solicitud.estado or "").upper()

            if accion == "INICIAR_REVISION":
                if estado_actual == "PENDIENTE":
                    solicitud.estado = "EN_REVISION"
                    solicitud.id_revisor_skilly = request.user
                    solicitud.fecha_asignacion = timezone.now()
                    solicitud.save(update_fields=[
                        "estado",
                        "id_revisor_skilly",
                        "fecha_asignacion",
                    ])
                    mensaje = "Revision documental iniciada."
                elif estado_actual == "EN_REVISION":
                    mensaje = "La solicitud ya esta en revision."
                else:
                    return Response(
                        {
                            "mensaje": (
                                "Esta solicitud ya tiene una resolucion "
                                "o no permite iniciar revision."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            else:
                if estado_actual not in ("EN_REVISION", "RECHAZADA"):
                    return Response(
                        {"mensaje": "La solicitud no permite modificar revisiones documentales."},
                        status=status.HTTP_409_CONFLICT,
                    )

                documentos = documentos_vigentes(solicitud, bloquear=True)
                if not documentos:
                    return Response(
                        {"mensaje": "No hay documentos asociados a la solicitud."},
                        status=status.HTTP_409_CONFLICT,
                    )

                if accion == "REVISAR_DOCUMENTO":
                    try:
                        id_documento = int(request.data.get("id_documento"))
                    except (TypeError, ValueError):
                        return Response({"mensaje": "ID de documento invalido."}, status=400)
                    vinculo = next(
                        (v for v in documentos if v.id_documento_id == id_documento),
                        None,
                    )
                    if vinculo is None or vinculo.id_documento.id_profesional_id != solicitud.id_profesional_id:
                        return Response({"mensaje": "Documento no asociado a esta solicitud."}, status=404)
                    if vinculo.estado_revision == "APROBADA":
                        return Response(
                            {"mensaje": "El documento ya fue aprobado. Su resultado se conserva."},
                            status=409,
                        )
                    vinculo.estado_revision = decision
                    vinculo.observacion = observacion or None
                    vinculo.save(update_fields=["estado_revision", "observacion"])
                    vinculo.id_documento.estado = (
                        "APROBADO" if decision == "APROBADA" else "RECHAZADO"
                    )
                    vinculo.id_documento.save(update_fields=["estado"])
                    solicitud.estado = "EN_REVISION"
                    solicitud.fecha_revision = None
                    solicitud.id_revisor_skilly = request.user
                    solicitud.observacion_resultado = None
                    solicitud.save(update_fields=[
                        "estado", "fecha_revision", "id_revisor_skilly", "observacion_resultado"
                    ])
                    mensaje = "Revision individual registrada."
                elif accion in ("FINALIZAR_REVISION", "APROBAR"):
                    # La accion antigua APROBAR se conserva, pero nunca
                    # vuelve a aprobar masivamente documentos pendientes.
                    if any(v.estado_revision != "APROBADA" for v in documentos):
                        return Response({
                            "mensaje": "Todos los documentos asociados deben estar aprobados. Revisa cada uno por separado."
                        }, status=409)
                    solicitud.estado = "APROBADA"
                    solicitud.fecha_revision = timezone.now()
                    solicitud.id_revisor_skilly = request.user
                    solicitud.observacion_resultado = observacion or "Documentacion revisada y aprobada."
                    solicitud.save(update_fields=[
                        "estado", "fecha_revision", "id_revisor_skilly", "observacion_resultado"
                    ])
                    mensaje = "Documentacion aprobada. Puede reservarse la entrevista."
                else:
                    # Rechazo general explicito, sin modificar los resultados
                    # individuales ya aprobados.
                    solicitud.estado = "RECHAZADA"
                    solicitud.fecha_revision = timezone.now()
                    solicitud.id_revisor_skilly = request.user
                    solicitud.observacion_resultado = observacion
                    solicitud.save(update_fields=[
                        "estado", "fecha_revision", "id_revisor_skilly", "observacion_resultado"
                    ])
                    mensaje = "Solicitud devuelta con observaciones."

            resultado = RevisionValidacionAdministracionSerializer(
                solicitud
            ).data

        return Response(
            {
                "mensaje": mensaje,
                "solicitud": resultado,
                "advertencia": (
                    "Esta operacion no activa automaticamente "
                    "al profesional ni reemplaza la entrevista."
                ),
            },
            status=status.HTTP_200_OK,
        )
