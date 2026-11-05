"""Decisión profesional sobre versión comercial: máximo un reintento administrativo.
La fuente de verdad son las revisiones históricas de la BD, no contadores del navegador.
"""
import json

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional
from backoffice.services import registrar_evento_trazabilidad
from profesionales.models import Profesional
from .models import RevisionServicio, Servicio

MOTIVOS = {
    "TARIFA_INSUFICIENTE": "Tarifa insuficiente",
    "DESACUERDO_ALCANCE": "Desacuerdo con el alcance",
    "CONDICIONES_EJECUCION": "Condiciones de ejecución",
    "OTRO": "Otro",
}


@method_decorator(csrf_protect, name="dispatch")
class RechazarVersionComercialProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    http_method_names = ["post", "head", "options"]

    def post(self, request, id_servicio):
        categoria = request.data.get("motivo_categoria")
        detalle = request.data.get("motivo_detalle")
        if not isinstance(categoria, str) or categoria not in MOTIVOS:
            return Response({"mensaje": "Selecciona un motivo válido del rechazo."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(detalle, str) or not 10 <= len(detalle.strip()) <= 600:
            return Response({"mensaje": "Describe tu motivo en 10 a 600 caracteres."},
                            status=status.HTTP_400_BAD_REQUEST)
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({"mensaje": "El perfil profesional no existe."},
                            status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            servicio = (Servicio.objects.select_for_update().filter(
                id_servicio=id_servicio, id_profesional=profesional).first())
            if servicio is None:
                return Response({"mensaje": "Servicio inexistente o ajeno al profesional."},
                                status=status.HTTP_404_NOT_FOUND)
            if servicio.estado_publicacion != "PEND_APROBACION_PROFESIONAL":
                return Response({"mensaje": "No hay una versión final pendiente de tu decisión."},
                                status=status.HTTP_409_CONFLICT)
            ultima = (RevisionServicio.objects.select_for_update()
                      .filter(id_servicio=servicio)
                      .order_by("-numero_version", "-fecha_revision", "-id_revision_servicio").first())
            if ultima is None or ultima.estado_revision != "PEND_APROBACION_PROFESIONAL":
                return Response({"mensaje": "La versión final ya fue respondida o no existe."},
                                status=status.HTTP_409_CONFLICT)
            rechazos_anteriores = RevisionServicio.objects.filter(
                id_servicio=servicio,
                estado_revision__in=["RECHAZO_COMERCIAL", "CIERRE_SIN_ACUERDO"],
            ).count()
            if rechazos_anteriores >= 2:
                return Response({"mensaje": "Se alcanzó el límite de decisiones comerciales."},
                                status=status.HTTP_409_CONFLICT)
            definitivo = rechazos_anteriores == 1
            ahora = timezone.now()
            ultima.estado_revision = "RECHAZADA_PROFESIONAL"
            ultima.save(update_fields=["estado_revision"])
            revision = RevisionServicio.objects.create(
                id_servicio=servicio,
                id_usuario_skilly=None,
                numero_version=ultima.numero_version + 1,
                contenido_revisado=json.dumps({
                    "tipo": "DECISION_COMERCIAL_PROFESIONAL",
                    "motivo_categoria": categoria,
                    "motivo_etiqueta": MOTIVOS[categoria],
                    "ronda": rechazos_anteriores + 1,
                    "id_version_rechazada": ultima.id_revision_servicio,
                }, ensure_ascii=False),
                observacion=detalle.strip(),
                estado_revision="CIERRE_SIN_ACUERDO" if definitivo else "RECHAZO_COMERCIAL",
                fecha_revision=ahora,
                fecha_aprobacion_profesional=None,
            )
            servicio.estado_publicacion = (
                "CERRADA_SIN_ACUERDO" if definitivo else "EN_REVISION"
            )
            servicio.fecha_actualizacion = ahora
            servicio.save(update_fields=["estado_publicacion", "fecha_actualizacion"])
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="revision_servicio",
                entidad_id=revision.id_revision_servicio,
                accion="CIERRE_COMERCIAL" if definitivo else "RECHAZO_COMERCIAL",
                detalle_resumido=(
                    f"Servicio {servicio.id_servicio}: "
                    f"{'cierre definitivo sin acuerdo' if definitivo else 'rechazo y posible reconsideración única'}. "
                    f"Motivo: {MOTIVOS[categoria]}."
                )[:255],
            )
        return Response({
            "mensaje": (
                "Condiciones rechazadas. La propuesta quedó cerrada sin acuerdo y su historial se conserva."
                if definitivo else
                "Rechazo registrado. La propuesta no se publicará. SKILLY podrá evaluar una única reconsideración, sin obligación de cambiar sus condiciones."
            ),
            "estado_publicacion": servicio.estado_publicacion,
            "ronda": rechazos_anteriores + 1,
            "id_revision_servicio": revision.id_revision_servicio,
        }, status=status.HTTP_200_OK)
