"""Confirmación del contacto previo sin modificar la entrevista ni crear tablas."""
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from backoffice.models import EventoTrazabilidad
from backoffice.services import registrar_evento_trazabilidad
from .models import EntrevistaValidacion

TIPO_CONTACTO = "entrevista_validacion"
ACCION_CONTACTO = "CONTACTO_PREENTREVISTA_REALIZADO"

@method_decorator(csrf_protect, name="dispatch")
class ConfirmarContactoEntrevistaAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["post", "options"]

    def post(self, request, id_entrevista):
        if request.data and (not isinstance(request.data, dict) or set(request.data) - {"confirmar"}):
            return Response({"mensaje": "Datos no permitidos."}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("confirmar") is not True:
            return Response({"mensaje": "Debe confirmar el contacto realizado."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            entrevista = (EntrevistaValidacion.objects.select_for_update()
                          .filter(id_entrevista=id_entrevista).first())
            if entrevista is None:
                return Response({"mensaje": "Entrevista inexistente."}, status=status.HTTP_404_NOT_FOUND)
            if entrevista.estado != "AGENDADA":
                return Response({"mensaje": "Solo se confirma el contacto de entrevistas agendadas."}, status=status.HTTP_409_CONFLICT)
            existente = EventoTrazabilidad.objects.filter(
                entidad_tipo=TIPO_CONTACTO, entidad_id=entrevista.pk,
                accion=ACCION_CONTACTO).order_by("-id_evento").first()
            if existente:
                return Response({"mensaje": "El contacto ya estaba confirmado.", "contactado": True, "fecha_contacto": existente.fecha_evento}, status=status.HTTP_200_OK)
            evento = registrar_evento_trazabilidad(
                usuario=request.user, entidad_tipo=TIPO_CONTACTO,
                entidad_id=entrevista.pk, accion=ACCION_CONTACTO,
                detalle_resumido=f"Contacto previo confirmado para entrevista #{entrevista.pk} y validación #{entrevista.id_validacion_id}.")
        return Response({"mensaje": "Contacto confirmado. La entrevista continúa agendada.", "contactado": True, "fecha_contacto": evento.fecha_evento}, status=status.HTTP_200_OK)
