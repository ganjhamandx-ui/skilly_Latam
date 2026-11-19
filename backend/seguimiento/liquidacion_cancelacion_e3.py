"""Autorización económica y solicitud de reversa; sin devolver ni transferir dinero.
Solo administración; independiente de comisión normal y de los pagos históricos.
"""
from decimal import Decimal
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
from seguimiento.models import ResolucionReclamo
from backoffice.services import registrar_evento_trazabilidad
from .expedientes_cancelacion_e3 import ExpedienteCancelacion
from .aceptacion_politica_e3 import AceptacionPoliticaCancelacion
from .politica_liquidacion_final_e3 import calcular_liquidacion


class LiquidacionCancelacionE3(models.Model):
    """Registra montos y enlaces económicos derivados de una cancelación."""

    id_liquidacion = models.BigAutoField(primary_key=True)
    id_expediente = models.OneToOneField(ExpedienteCancelacion, models.DO_NOTHING, db_column='id_expediente')
    id_pago = models.OneToOneField(Pago, models.DO_NOTHING, db_column='id_pago')
    id_reversa = models.OneToOneField(ReversaPago, models.DO_NOTHING, db_column='id_reversa', null=True)
    id_administrador = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_administrador')
    version_politica = models.CharField(max_length=64, null=True)
    porcentaje_contratado = models.DecimalField(max_digits=7, decimal_places=4)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    monto_trabajo = models.DecimalField(max_digits=12, decimal_places=2)
    cargo_autorizado = models.DecimalField(max_digits=12, decimal_places=2)
    monto_devolucion = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=45)
    fundamento = models.TextField()
    fecha_registro = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `liquidacion_cancelacion_e3`."""

        managed = False
        db_table = 'liquidacion_cancelacion_e3'


class LiquidacionSerializer(serializers.Serializer):
    """Valida cargo y fundamento antes de liquidar el expediente."""

    cargo_autorizado = serializers.DecimalField(min_value=Decimal('0'), max_digits=12, decimal_places=2)
    fundamento = serializers.CharField(min_length=30, max_length=2000, trim_whitespace=True)
    derechos_verificados = serializers.BooleanField()
    excepcion_legal = serializers.BooleanField(default=False)
    confirmacion_sin_dinero = serializers.BooleanField()


def datos_liquidacion(l):
    """Serializa el resultado económico sin exponer datos bancarios."""

    return {'id_liquidacion':l.pk,'id_expediente':l.id_expediente_id,
      'id_pago':l.id_pago_id,'id_reversa':l.id_reversa_id,
      'porcentaje_contratado':str(l.porcentaje_contratado),
      'monto_total':str(l.monto_total),'monto_trabajo':str(l.monto_trabajo),
      'cargo_autorizado':str(l.cargo_autorizado),'monto_devolucion':str(l.monto_devolucion),
      'estado':l.estado,'fundamento':l.fundamento,'fecha_registro':l.fecha_registro,
      'nota':'Monto documentado y reversa SOLICITADA, no dinero transferido ni devuelto.'}


@method_decorator(csrf_protect, name='dispatch')
class LiquidarCancelacionE3View(APIView):
    """Calcula y persiste una liquidación idempotente bajo bloqueo transaccional."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        """Consulta la liquidación documentada para un expediente."""
        liq = LiquidacionCancelacionE3.objects.filter(id_expediente_id=id_expediente).first()
        return Response({'liquidacion':datos_liquidacion(liq) if liq else None})

    def post(self, request, id_expediente):
        """Crea la liquidación y solicita su reversa bajo validaciones transaccionales."""
        s = LiquidacionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        entrada = s.validated_data
        if entrada['derechos_verificados'] is not True or entrada['confirmacion_sin_dinero'] is not True:
            return Response({'mensaje':'Debes confirmar revisión de derechos y ausencia de movimiento bancario.'},status=400)
        with transaction.atomic():
            exp = ExpedienteCancelacion.objects.select_for_update().filter(pk=id_expediente).first()
            if not exp:
                return Response({'mensaje':'Expediente no encontrado.'},status=404)
            if exp.estado!='RESUELTO' or exp.decision=='RECHAZAR_SOLICITUD':
                return Response({'mensaje':'La evaluación administrativa no autoriza liquidar la cancelación.'},status=409)
            if LiquidacionCancelacionE3.objects.filter(id_expediente=exp).exists():
                return Response({'mensaje':'Este expediente ya tiene una liquidación registrada.'},status=409)
            pago = Pago.objects.select_for_update().filter(id_prestacion=exp.id_prestacion).first()
            if not pago or pago.estado_pago!='RETENIDO' or pago.estado_verificacion!='VERIFICADO':
                return Response({'mensaje':'Se requiere un pago RETENIDO y VERIFICADO.'},status=409)
            if exp.id_prestacion.estado!='CANCELADA':
                return Response({'mensaje':'Primero cancela la prestación desde Gestión de agenda de SKILLY.'},status=409)
            if exp.monto_total is None or Decimal(exp.monto_total) != Decimal(pago.monto_total):
                return Response({'mensaje':'El monto del pago no coincide con el expediente evaluado; requiere revisión.'},status=409)
            if ReversaPago.objects.filter(id_pago=pago).exists() or LiquidacionCancelacionE3.objects.filter(id_pago=pago).exists():
                return Response({'mensaje':'Ya hay una reversa o liquidación vinculada a este pago; evita duplicaciones.'},status=409)
            # La resolución formal del reclamo es independiente y debe habilitar la reversa.
            if exp.id_reclamo_id:
                resolucion = ResolucionReclamo.objects.filter(id_reclamo_id=exp.id_reclamo_id).first()
                if not resolucion:
                    return Response({'mensaje':'Primero resuelve formalmente el reclamo en Gestión de reclamos.'},status=409)
                if resolucion.efecto_economico != 'REVERSA':
                    return Response({'mensaje':'La resolución del reclamo debe autorizar una REVERSA.'},status=409)
            else:
                resolucion = None
            # Solo se admite el porcentaje aceptado antes del pago, nunca el vigente hoy.
            aceptacion = AceptacionPoliticaCancelacion.objects.filter(id_prestacion=exp.id_prestacion).first()
            aceptacion_previa = bool(aceptacion and pago.fecha_pago and aceptacion.fecha_aceptacion <= pago.fecha_pago)
            porcentaje = Decimal(aceptacion.porcentaje_aceptado) if aceptacion_previa else Decimal('0')
            if exp.porcentaje_referencia is not None and Decimal(exp.porcentaje_referencia)!=porcentaje:
                return Response({'mensaje':'Discrepancia con la versión congelada; revisar expediente.'},status=409)
            try:
                calculo = calcular_liquidacion(total=pago.monto_total,
                    trabajo=exp.monto_trabajo or Decimal('0'), porcentaje=porcentaje,
                    decision=exp.decision,origen=exp.origen,
                    cargo_solicitado=entrada['cargo_autorizado'],
                    aceptacion_previa=aceptacion_previa,excepcion_legal=entrada['excepcion_legal'])
            except ValueError as exc:
                return Response({'mensaje':str(exc)},status=409)
            devolucion = calculo['devolucion_autorizada']
            if resolucion and (resolucion.monto_afectado is None or Decimal(resolucion.monto_afectado)!=devolucion):
                return Response({'mensaje':'Monto de resolución de reclamo debe coincidir con devolución autorizada.'},status=409)
            if not devolucion and resolucion:
                return Response({'mensaje':'No corresponde marcar REVERSA con devolución de cero pesos.'},status=409)
            # Crear la reversa en estado SOLICITADA no devuelve dinero: el cierre vendrá después.
            rev = None
            if devolucion>0:
                rev = ReversaPago.objects.create(
                    id_pago=pago,id_usuario_skilly=request.user,
                    id_resolucion_reclamo=resolucion,
                    monto_reversa=devolucion,estado_reversa='SOLICITADA',
                    motivo=(f'Expediente #{exp.pk} - devolución autorizada {devolucion} CLP. '
                            'No constituye reembolso ejecutado. '+entrada['fundamento']),
                    referencia_externa=None,fecha_solicitud=timezone.now(),fecha_resolucion=None)
            liq = LiquidacionCancelacionE3.objects.create(
                id_expediente=exp,id_pago=pago,id_reversa=rev,
                id_administrador=request.user,
                version_politica=aceptacion.version_politica if aceptacion_previa else None,
                porcentaje_contratado=porcentaje,
                monto_total=calculo['monto_total'],monto_trabajo=calculo['trabajo_acreditado'],
                cargo_autorizado=calculo['cargo_autorizado'],
                monto_devolucion=devolucion,
                estado='REVERSA_SOLICITADA' if rev else 'PENDIENTE_CONCILIACION',
                fundamento=entrada['fundamento'],fecha_registro=timezone.now())
            registrar_evento_trazabilidad(usuario=request.user,
                entidad_tipo='liquidacion_cancelacion_e3',entidad_id=liq.pk,
                accion='AUTORIZAR_LIQUIDACION',
                detalle_resumido=f'Expediente {exp.pk}; cargo autorizado {liq.cargo_autorizado}, reversa solicitada {devolucion} CLP; dinero no movido.'[:255])
        return Response({'mensaje':'Liquidación registrada y reversa solicitada cuando corresponde. NO se ejecutó devolución ni cobro bancario.',
                         'liquidacion':datos_liquidacion(liq)},status=201)
