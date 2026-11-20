"""Registro acotado de avisos de incidentes desde la sesión del profesional."""
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
from coordinacion.models import PrestacionServicio
from profesionales.models import Profesional
from .models import AvanceServicio
from .politicas_reportes_profesional import ESTADO_AVISO, preparar_aviso


@method_decorator(csrf_protect, name='dispatch')
class AvisoIncidenciaProfesionalView(APIView):
    """Registra una incidencia informativa sin modificar agenda, pago o contrato."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def post(self, request, id_prestacion):
        """Registra un aviso profesional sin cancelar ni reagendar automáticamente.

        Args:
            request: Petición del profesional con motivo y descripcion válidos.
            id_prestacion (int): Prestación del profesional que informa la incidencia.

        Returns:
            Response: 201 con id_aviso, 400 por contenido inválido, 404 por perfil
            o prestación ajena/inexistente y 409 si no está CONTRATADA. Inserta un
            avance privado y trazabilidad bajo bloqueo de la prestación; no impide
            registrar varios avisos sobre ella.
        """
        try:
            detalle = preparar_aviso(
                request.data.get('motivo'), request.data.get('descripcion')
            )
        except ValueError as error:
            return Response({'mensaje': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response(
                {'mensaje': 'No existe un perfil profesional vinculado a esta sesión.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        with transaction.atomic():
            prestacion = (PrestacionServicio.objects.select_for_update()
                          .filter(id_prestacion=id_prestacion, id_profesional=profesional)
                          .first())
            if prestacion is None:
                return Response(
                    {'mensaje': 'La prestación no existe o no te pertenece.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if prestacion.estado != 'CONTRATADA':
                return Response(
                    {'mensaje': 'Solo se admiten avisos sobre prestaciones CONTRATADAS. '
                     'Los demás estados deben revisarse con administración.'},
                    status=status.HTTP_409_CONFLICT,
                )
            aviso = AvanceServicio.objects.create(
                id_prestacion=prestacion,
                estado=ESTADO_AVISO,
                detalle=detalle,
                fecha_registro=timezone.now(),
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo='avance_servicio',
                entidad_id=aviso.id_avance,
                accion='REPORTAR_INCIDENCIA_PROFESIONAL',
                detalle_resumido=(
                    f'Profesional informó incidencia en prestación '
                    f'{prestacion.id_prestacion}. Pendiente de revisión.'
                )[:255],
            )
        return Response(
            {'mensaje': 'Aviso registrado. SKILLY debe revisar los antecedentes. '
             'No se ha cancelado ni reprogramado la prestación.',
             'id_aviso': aviso.id_avance},
            status=status.HTTP_201_CREATED,
        )
