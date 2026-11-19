"""Simulación DOCUMENTAL de conciliación parcial para una liquidación autorizada.

No ejecuta refund externo, no altera ni libera Pago, no resuelve ReversaPago;
conserva SOLICITADA para impedir que se libere el pago mediante el circuito normal.
"""
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from acceso.models import Usuario
from pagos.models import Pago, ReversaPago
from backoffice.services import registrar_evento_trazabilidad
from .liquidacion_cancelacion_e3 import LiquidacionCancelacionE3
from .politica_conciliacion_e3 import desglose_parcial, ConciliacionInvalida


class ConciliacionReversaE3(models.Model):
    """Registra la conciliación final de una reversa parcial."""

    id_conciliacion = models.BigAutoField(primary_key=True)
    id_liquidacion = models.OneToOneField(LiquidacionCancelacionE3, models.DO_NOTHING, db_column='id_liquidacion')
    id_pago = models.OneToOneField(Pago, models.DO_NOTHING, db_column='id_pago')
    id_reversa = models.OneToOneField(ReversaPago, models.DO_NOTHING, db_column='id_reversa')
    id_administrador = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_administrador')
    metodo_pago = models.CharField(max_length=30)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    monto_devolucion = models.DecimalField(max_digits=12, decimal_places=2)
    monto_trabajo = models.DecimalField(max_digits=12, decimal_places=2)
    monto_cargo = models.DecimalField(max_digits=12, decimal_places=2)
    remanente_pendiente = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=35)
    fundamento = models.TextField()
    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `conciliacion_reversa_e3`."""

        managed = False
        db_table = 'conciliacion_reversa_e3'


class ConciliacionSerializer(serializers.Serializer):
    """Valida fundamento y confirmación antes de conciliar una reversa."""

    fundamento = serializers.CharField(min_length=30, max_length=1500, trim_whitespace=True)
    confirmacion_simulacion = serializers.BooleanField(required=True)
    confirmacion_saldo_pendiente = serializers.BooleanField(required=True)


def datos_conciliacion(c):
    """Serializa una conciliación o devuelve nulo cuando no existe."""

    if c is None:
        return None
    return {
        'id_conciliacion': c.pk, 'id_liquidacion': c.id_liquidacion_id,
        'id_pago': c.id_pago_id, 'id_reversa': c.id_reversa_id,
        'metodo_pago': c.metodo_pago, 'monto_total': str(c.monto_total),
        'monto_devolucion': str(c.monto_devolucion),
        'monto_trabajo': str(c.monto_trabajo), 'monto_cargo': str(c.monto_cargo),
        'remanente_pendiente': str(c.remanente_pendiente), 'estado': c.estado,
        'fundamento': c.fundamento, 'fecha_registro': c.fecha_registro,
        'nota': ('Solo simulación documental académica. Reversa SOLICITADA, pago RETENIDO. '
                 'No existe devolución bancaria ni reparto del remanente ejecutado.'),
    }


@method_decorator(csrf_protect, name='dispatch')
class ConciliarReversaParcialE3View(APIView):
    """Concilia una reversa parcial bajo bloqueo y trazabilidad administrativa."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        """Consulta la conciliación documental vinculada al expediente."""
        liquidacion = LiquidacionCancelacionE3.objects.filter(id_expediente_id=id_expediente).first()
        if not liquidacion:
            return Response({'conciliacion': None, 'mensaje':'No hay liquidación para este expediente.'})
        c = ConciliacionReversaE3.objects.filter(id_liquidacion=liquidacion).first()
        return Response({'conciliacion': datos_conciliacion(c)})

    def post(self, request, id_expediente):
        """Registra la conciliación parcial bajo bloqueos sin ejecutar movimientos bancarios."""
        entrada = ConciliacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        if datos['confirmacion_simulacion'] is not True or datos['confirmacion_saldo_pendiente'] is not True:
            return Response({'mensaje':'Debes confirmar que no hay movimientos bancarios y que el saldo no puede liberarse automáticamente.'},status=400)

        with transaction.atomic():
            # Misma jerarquía de bloqueo que CU040: Pago primero, luego Reversa.
            preliminar = LiquidacionCancelacionE3.objects.filter(id_expediente_id=id_expediente).first()
            if preliminar is None:
                return Response({'mensaje':'No existe una liquidación autorizada.'},status=404)
            pago = Pago.objects.select_for_update().filter(pk=preliminar.id_pago_id).first()
            liquidacion = LiquidacionCancelacionE3.objects.select_for_update().filter(pk=preliminar.pk).first()
            if not pago or not liquidacion or liquidacion.id_pago_id != pago.pk:
                return Response({'mensaje':'La liquidación y el pago no coinciden.'},status=409)
            if liquidacion.estado != 'REVERSA_SOLICITADA' or liquidacion.id_reversa_id is None:
                return Response({'mensaje':'El expediente no tiene reversa pendiente de conciliación.'},status=409)
            if ConciliacionReversaE3.objects.filter(id_liquidacion=liquidacion).exists():
                return Response({'mensaje':'La conciliación de esta liquidación ya está registrada.'},status=409)
            reversa = ReversaPago.objects.select_for_update().filter(pk=liquidacion.id_reversa_id, id_pago=pago).first()
            if not reversa:
                return Response({'mensaje':'La reversa vinculada no coincide con el pago.'},status=409)
            if ReversaPago.objects.filter(id_pago=pago).exclude(pk=reversa.pk).exists():
                return Response({'mensaje':'Existen otras reversas en este pago: requiere revisión.'},status=409)
            expediente = liquidacion.id_expediente
            if expediente.estado != 'RESUELTO' or expediente.id_prestacion.estado != 'CANCELADA':
                return Response({'mensaje':'El expediente debe estar resuelto y la prestación cancelada.'},status=409)
            try:
                plan = desglose_parcial(
                    total=liquidacion.monto_total, trabajo=liquidacion.monto_trabajo,
                    cargo=liquidacion.cargo_autorizado, devolucion=liquidacion.monto_devolucion,
                    monto_reversa=reversa.monto_reversa, metodo_pago=pago.metodo_pago,
                    estado_pago=pago.estado_pago, estado_verificacion=pago.estado_verificacion,
                    estado_reversa=reversa.estado_reversa)
            except ConciliacionInvalida as exc:
                return Response({'mensaje':str(exc)},status=409)
            if plan['total'] != pago.monto_total:
                return Response({'mensaje':'El total del pago difiere de la liquidación.'},status=409)
            c = ConciliacionReversaE3.objects.create(
                id_liquidacion=liquidacion,id_pago=pago,id_reversa=reversa,
                id_administrador=request.user,metodo_pago=plan['metodo_pago'],
                monto_total=plan['total'],monto_devolucion=plan['devolucion_pendiente'],
                monto_trabajo=plan['trabajo_pendiente_distribucion'],
                monto_cargo=plan['cargo_pendiente_distribucion'],
                remanente_pendiente=plan['remanente_pendiente_distribucion'],
                estado=plan['estado'],fundamento=datos['fundamento'],fecha_registro=timezone.now())
            registrar_evento_trazabilidad(
                usuario=request.user,entidad_tipo='conciliacion_reversa_e3',entidad_id=c.pk,
                accion='SIMULAR_CONCILIACION_PARCIAL',
                detalle_resumido=(f'Pago #{pago.pk}, devolución pendiente {c.monto_devolucion}, '
                    f'remanente pendiente {c.remanente_pendiente}. Sin movimientos bancarios.')[:255])
        return Response({'mensaje':'Conciliación DOCUMENTAL registrada. La reversa sigue SOLICITADA y el pago RETENIDO; sin dinero movido.',
                         'conciliacion':datos_conciliacion(c)},status=201)
