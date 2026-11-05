"""Política de cancelación informada y aceptada para cada prestación nueva.

La aceptación conserva la versión y el porcentaje de ese contrato, sin
provocar cobros, cancelaciones ni limitar derechos legales.
"""
import hashlib
from decimal import Decimal, InvalidOperation
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from backoffice.models import ParametroSistema
from coordinacion.models import PrestacionServicio
from pagos.models import Pago
from solicitudes.referencias import leer_referencia_seguimiento
from .politica_texto_cancelacion_e3 import texto_versionado, firma_politica, porcentaje_valido

CLAVE = 'cancelacion_injustificada_porcentaje'

class AceptacionPoliticaCancelacion(models.Model):
    id_aceptacion = models.BigAutoField(primary_key=True)
    id_prestacion = models.OneToOneField(PrestacionServicio, models.DO_NOTHING, db_column='id_prestacion')
    porcentaje_aceptado = models.DecimalField(max_digits=7, decimal_places=4)
    version_politica = models.CharField(max_length=64)
    texto_aceptado = models.TextField()
    fecha_aceptacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'aceptacion_politica_cancelacion_e3'


def politica_actual():
    parametro = ParametroSistema.objects.filter(clave=CLAVE).first()
    if not parametro:
        raise ValueError('SKILLY aún no configura el cargo por cancelación; no se puede iniciar un pago nuevo.')
    try:
        porcentaje = porcentaje_valido(parametro.valor_actual)
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError('El porcentaje de cancelación vigente es inválido.')
    texto = texto_versionado(porcentaje)
    return {'porcentaje': porcentaje, 'version': firma_politica(texto), 'texto': texto}


def obtener_prestacion(referencia, bloquear=False):
    datos = leer_referencia_seguimiento(referencia)
    if not datos:
        return None
    consulta = PrestacionServicio.objects
    if bloquear:
        consulta = consulta.select_for_update()
    return consulta.filter(id_solicitud_id=datos['id_solicitud'],
        id_solicitud__id_contacto_id=datos['id_contacto']).first()


def detalle_politica(aceptacion):
    return {'aceptada': True, 'porcentaje': str(aceptacion.porcentaje_aceptado),
            'version': aceptacion.version_politica, 'texto': aceptacion.texto_aceptado,
            'fecha_aceptacion': aceptacion.fecha_aceptacion,
            'mensaje': 'Este porcentaje quedó fijado para esta contratación. Cambios posteriores no lo modifican.'}


def bloquear_pago_sin_aceptacion(prestacion):
    """Se llama dentro de la transacción del pago, tras bloquear la prestación."""
    if AceptacionPoliticaCancelacion.objects.filter(id_prestacion=prestacion).exists():
        return
    # Operaciones iniciadas antes de la implementación: no imponer condiciones retroactivas.
    if Pago.objects.filter(id_prestacion=prestacion).exists():
        return
    raise ValueError('Antes de iniciar el pago debes leer y aceptar la política de cancelación vigente.')

@method_decorator(csrf_protect, name='dispatch')
class PoliticaCancelacionEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        prestacion = obtener_prestacion(referencia)
        if not prestacion:
            return Response({'mensaje': 'Solicitud no encontrada.'}, status=404)
        aceptacion = AceptacionPoliticaCancelacion.objects.filter(id_prestacion=prestacion).first()
        if aceptacion:
            return Response(detalle_politica(aceptacion))
        # Para pagos preexistentes se conserva el trato original; no imponer nueva política.
        if Pago.objects.filter(id_prestacion=prestacion).exists():
            return Response({'aceptada': False, 'contrato_previo': True,
                'mensaje': 'Esta prestación tiene una operación de pago previa a la aceptación versionada. No se aplicarán cargos nuevos retroactivamente.'})
        try:
            actual = politica_actual()
        except ValueError as exc:
            return Response({'mensaje': str(exc)}, status=409)
        return Response({'aceptada': False, 'contrato_previo': False,
            'porcentaje': str(actual['porcentaje']), 'version': actual['version'],
            'texto': actual['texto'], 'mensaje': 'Revisa antes de pagar. El cargo no es automático y está sujeto a derechos y evaluación.'})

    def post(self, request, referencia):
        if request.data.get('acepto') is not True:
            return Response({'mensaje': 'Marca la aceptación expresa de las condiciones antes de continuar.'}, status=400)
        version = request.data.get('version')
        if not isinstance(version, str) or len(version) != 64:
            return Response({'mensaje': 'Versión de política no válida.'}, status=400)
        with transaction.atomic():
            prestacion = obtener_prestacion(referencia, bloquear=True)
            if not prestacion:
                return Response({'mensaje': 'Solicitud no encontrada.'}, status=404)
            existente = AceptacionPoliticaCancelacion.objects.filter(id_prestacion=prestacion).first()
            if existente:
                return Response(detalle_politica(existente), status=200)
            if prestacion.estado != 'PENDIENTE_CONTRATACION' or not str(prestacion.condiciones_comunicadas or '').strip():
                return Response({'mensaje': 'La prestación no está habilitada para contratar.'}, status=409)
            if Pago.objects.filter(id_prestacion=prestacion).exists():
                return Response({'mensaje': 'Ya existe una operación de pago. No se puede imponer una nueva aceptación retroactiva.'}, status=409)
            try:
                actual = politica_actual()
            except ValueError as exc:
                return Response({'mensaje': str(exc)}, status=409)
            if version != actual['version']:
                return Response({'mensaje': 'SKILLY actualizó el porcentaje. Revisa y acepta la versión nueva antes de pagar.',
                                 'porcentaje_vigente': str(actual['porcentaje'])}, status=409)
            nueva = AceptacionPoliticaCancelacion.objects.create(
                id_prestacion=prestacion, porcentaje_aceptado=actual['porcentaje'],
                version_politica=actual['version'], texto_aceptado=actual['texto'],
                fecha_aceptacion=timezone.now())
        return Response(detalle_politica(nueva), status=201)
