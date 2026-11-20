"""Registra el cierre académico de distribución de una cancelación parcial E3.

No conecta bancos ni Webpay. Registra asientos de simulación y estados específicos
en pago, reversa, liquidación y conciliación dentro de una transacción. Los registros
permiten seguir los destinos económicos sin representar movimientos bancarios.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from backoffice.models import EventoTrazabilidad
from backoffice.services import registrar_evento_trazabilidad
from pagos.models import Pago, ReversaPago, HistorialEstadoPago
from seguimiento.models import ResolucionReclamo
from .conciliacion_reversas_e3 import ConciliacionReversaE3
from .liquidacion_cancelacion_e3 import LiquidacionCancelacionE3
from .politica_conciliacion_e3 import desglose_parcial, ConciliacionInvalida

CENTAVO = Decimal('0.01')


def detalles(liquidacion, pago, *, terminado=False):
    """Comprueba la cuadratura y desglosa los destinos de la simulación.

    Args:
        liquidacion (LiquidacionCancelacionE3): Total, trabajo, cargo y devolución.
        pago (Pago): Aporta el porcentaje de comisión aplicado al contratar.
        terminado (bool): Selecciona el estado y la nota de presentación;
            no comprueba ni modifica estados persistidos.

    Returns:
        dict: Importes como texto decimal y marca ``sin_movimiento_bancario``.
        La comisión se calcula sobre el trabajo con ROUND_HALF_UP a centavos;
        SKILLY recibe documentalmente comisión más cargo y el profesional el
        trabajo menos comisión. Los tres destinos deben sumar el total.

    Raises:
        ValueError: Si los valores convertidos no son finitos, están fuera de
            rango o los destinos no cuadran con el total de la liquidación.
    """

    trabajo = Decimal(liquidacion.monto_trabajo)
    total = Decimal(liquidacion.monto_total)
    cargo = Decimal(liquidacion.cargo_autorizado)
    devolucion = Decimal(liquidacion.monto_devolucion)
    porcentaje = Decimal(pago.porcentaje_comision_aplicado)
    if not all(v.is_finite() for v in (trabajo, total, cargo, devolucion, porcentaje)):
        raise ValueError('Montos no finitos.')
    if total <= 0 or not Decimal('0') <= porcentaje <= Decimal('100'):
        raise ValueError('Monto o comision fuera de rango.')
    if any(v < 0 for v in (trabajo, cargo, devolucion)):
        raise ValueError('No se admiten montos negativos.')
    # La comisión se calcula solo sobre el trabajo acreditado; el cargo por cancelación va aparte.
    comision = (trabajo * porcentaje / Decimal('100')).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    profesional = trabajo - comision
    skilly = comision + cargo
    if profesional < 0 or profesional + skilly + devolucion != total:
        raise ValueError('El desglose economico no cuadra con el pago retenido.')
    return {
        'estado': 'DISTRIBUIDO_SIMULADO' if terminado else 'PENDIENTE_SIMULACION',
        'total': str(total),
        'organizacion': str(devolucion),
        'profesional_neto': str(profesional),
        'skilly_comision_trabajo': str(comision),
        'skilly_cargo_cancelacion': str(cargo),
        'skilly_total': str(skilly),
        'porcentaje_comision_trabajo': str(porcentaje),
        'sin_movimiento_bancario': True,
        'nota': 'Los tres destinos fueron registrados como una simulacion; no existen transferencias ni devoluciones reales.' if terminado
                else 'Previsualizacion, aun no existe registro de distribucion simulada.',
    }


class CierreSimuladoCancelacionE3View(APIView):
    """Consulta y registra el cierre académico bajo permisos administrativos."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        """Consulta la distribución calculada a partir de la liquidación.

        Args:
            request (Request): Petición de una sesión administrativa activa.
            id_expediente (int): Identificador del expediente de cancelación.

        Returns:
            Response: HTTP 200 con ``cierre`` o ``None`` si no hay liquidación;
            HTTP 409 si falta el pago o el cálculo detecta importes inconsistentes.
            El estado de liquidación distingue previsualización de cierre simulado.
        """

        liquidacion = LiquidacionCancelacionE3.objects.filter(id_expediente_id=id_expediente).first()
        if not liquidacion:
            return Response({'cierre': None, 'mensaje': 'Primero registra la liquidacion.'})
        pago = Pago.objects.filter(pk=liquidacion.id_pago_id).first()
        if not pago:
            return Response({'mensaje': 'Pago asociado no encontrado.'}, status=409)
        try:
            terminado = liquidacion.estado == 'DISTRIBUCION_SIMULADA'
            return Response({'cierre': detalles(liquidacion, pago, terminado=terminado)})
        except ValueError as exc:
            return Response({'mensaje': str(exc)}, status=409)

    @method_decorator(csrf_protect)
    def post(self, request, id_expediente):
        """Registra una distribución académica consistente y admite su reintento.

        Bloquea pago, liquidación, reversa y conciliación en ese orden. Exige
        cancelación aprobada, prestación cancelada, pago retenido y verificado,
        reversa única solicitada e importes coincidentes. Si existe reclamo,
        su resolución debe autorizar la misma devolución. Crea la conciliación
        documental si falta y guarda conjuntamente estados simulados e historial.

        Args:
            request (Request): Sesión administrativa con CSRF y los booleanos
                ``confirmar_simulacion`` y ``confirmar_sin_dinero_real`` en ``True``.
            id_expediente (int): Expediente cuya liquidación se cerrará.

        Returns:
            Response: HTTP 201 al registrar; HTTP 200 en un reintento cuyo pago,
            reversa y conciliación ya tienen estados simulados compatibles;
            HTTP 400 si faltan confirmaciones; HTTP 409 ante relaciones, estados,
            importes o cierres previos incompatibles. No ejecuta devoluciones reales.

        Raises:
            LiquidacionCancelacionE3.DoesNotExist: Si desaparece la liquidación
                entre la lectura inicial y su recuperación bajo bloqueo.
        """

        if request.data.get('confirmar_simulacion') is not True or request.data.get('confirmar_sin_dinero_real') is not True:
            return Response({'mensaje': 'Confirma expresamente la simulacion y que no se movera dinero real.'}, status=400)
        with transaction.atomic():
            vista = LiquidacionCancelacionE3.objects.filter(id_expediente_id=id_expediente).first()
            if not vista:
                return Response({'mensaje': 'Primero registra la liquidacion.'}, status=409)
            # Orden de bloqueo uniforme: primero Pago, despues liquidacion y reversa.
            pago = Pago.objects.select_for_update().filter(pk=vista.id_pago_id).first()
            liq = LiquidacionCancelacionE3.objects.select_for_update().get(pk=vista.pk)
            if not pago or liq.id_pago_id != pago.pk:
                return Response({'mensaje': 'Pago y liquidacion no coinciden.'}, status=409)
            if not liq.id_reversa_id:
                return Response({'mensaje': 'La devolucion parcial requiere una reversa documentada.'}, status=409)
            rev = ReversaPago.objects.select_for_update().filter(pk=liq.id_reversa_id, id_pago=pago).first()
            if not rev:
                return Response({'mensaje': 'La reversa no corresponde al pago.'}, status=409)
            existente = ConciliacionReversaE3.objects.select_for_update().filter(id_liquidacion=liq).first()
            terminado = liq.estado == 'DISTRIBUCION_SIMULADA'
            try:
                plan = detalles(liq, pago, terminado=terminado)
            except ValueError as exc:
                return Response({'mensaje': str(exc)}, status=409)
            # Un reintento solo es idempotente si pago, reversa y conciliación coinciden.
            if terminado:
                if (not existente or existente.estado != 'DISTRIBUCION_SIMULADA'
                        or rev.estado_reversa != 'SIMULADA'
                        or pago.estado_pago != 'DISTRIBUIDO_SIMULADO'):
                    return Response({'mensaje': 'Cierre parcial inconsistente. Requiere revision.'}, status=409)
                return Response({'mensaje': 'La distribucion simulada ya fue registrada.', 'cierre': plan})
            if liq.estado != 'REVERSA_SOLICITADA' or rev.estado_reversa != 'SOLICITADA':
                return Response({'mensaje': 'La solicitud de devolucion no esta pendiente de conciliacion.'}, status=409)
            if pago.estado_pago != 'RETENIDO' or pago.estado_verificacion != 'VERIFICADO':
                return Response({'mensaje': 'El pago debe estar retenido y verificado para cerrar la simulacion.'}, status=409)
            exp = liq.id_expediente
            if (exp.pk != id_expediente or exp.estado != 'RESUELTO'
                    or exp.id_prestacion.estado != 'CANCELADA' or exp.decision == 'RECHAZAR_SOLICITUD'):
                return Response({'mensaje': 'La cancelacion no esta aprobada o la prestacion no esta cancelada.'}, status=409)
            if (Pago.objects.filter(pk=pago.pk).count() != 1
                    or ReversaPago.objects.filter(id_pago=pago).count() != 1
                    or Decimal(rev.monto_reversa or 0) != Decimal(liq.monto_devolucion)
                    or Decimal(pago.monto_total) != Decimal(liq.monto_total)):
                return Response({'mensaje': 'Reversa duplicada o montos inconsistentes.'}, status=409)
            # Si hubo reclamo, su resolución debe autorizar la misma devolución que la liquidación.
            if exp.id_reclamo_id:
                resolucion = ResolucionReclamo.objects.filter(id_reclamo_id=exp.id_reclamo_id).first()
                if (not resolucion or resolucion.efecto_economico != 'REVERSA'
                        or Decimal(resolucion.monto_afectado or 0) != Decimal(liq.monto_devolucion)):
                    return Response({'mensaje': 'El reclamo y la liquidacion deben coincidir.'}, status=409)
            if EventoTrazabilidad.objects.filter(
                    entidad_tipo='conciliacion_reversa_e3',
                    entidad_id=getattr(existente, 'pk', 0),
                    accion='CERRAR_DISTRIBUCION_SIMULADA').exists():
                return Response({'mensaje': 'Existe un cierre previo; no repetir.', 'cierre': plan}, status=409)
            # El cierre único crea la conciliación documental internamente; no exige otro formulario.
            if not existente:
                try:
                    resultado = desglose_parcial(
                        total=liq.monto_total, trabajo=liq.monto_trabajo,
                        cargo=liq.cargo_autorizado, devolucion=liq.monto_devolucion,
                        monto_reversa=rev.monto_reversa, metodo_pago=pago.metodo_pago,
                        estado_pago=pago.estado_pago, estado_verificacion=pago.estado_verificacion,
                        estado_reversa=rev.estado_reversa)
                except ConciliacionInvalida as exc:
                    return Response({'mensaje': str(exc)}, status=409)
                existente = ConciliacionReversaE3.objects.create(
                    id_liquidacion=liq, id_pago=pago, id_reversa=rev,
                    id_administrador=request.user, metodo_pago=resultado['metodo_pago'],
                    monto_total=resultado['total'], monto_devolucion=resultado['devolucion_pendiente'],
                    monto_trabajo=resultado['trabajo_pendiente_distribucion'],
                    monto_cargo=resultado['cargo_pendiente_distribucion'],
                    remanente_pendiente=resultado['remanente_pendiente_distribucion'],
                    estado='SIMULACION_DOCUMENTAL', fundamento=(
                        'Conciliacion y distribucion simuladas para cancelacion parcial. '
                        'No existen movimientos de dinero.'), fecha_registro=timezone.now())
            elif existente.estado != 'SIMULACION_DOCUMENTAL':
                return Response({'mensaje': 'La conciliacion tiene un estado incompatible.'}, status=409)
            cierre_id = existente.pk
            # Deja un asiento trazable por cada destino económico, sin instrucciones bancarias.
            eventos = [
                ('SIMULACION_DEVOLUCION_ORGANIZACION', f'Organizacion: {plan["organizacion"]} CLP; abono de prueba, sin transferencia.'),
                ('SIMULACION_ABONO_PROFESIONAL', f'Profesional: {plan["profesional_neto"]} CLP netos; sin transferencia.'),
                ('SIMULACION_COMISION_SKILLY', f'SKILLY comision trabajo: {plan["skilly_comision_trabajo"]} CLP; sin transferencia.'),
                ('SIMULACION_CARGO_CANCELACION', f'SKILLY cargo cancelacion: {plan["skilly_cargo_cancelacion"]} CLP; sin transferencia.'),
            ]
            for accion, detalle in eventos:
                registrar_evento_trazabilidad(
                    usuario=request.user, entidad_tipo='conciliacion_reversa_e3',
                    entidad_id=cierre_id, accion=accion, detalle_resumido=detalle)
            ahora = timezone.now()
            # Los estados simulados se guardan juntos en la transacción: no equivalen a pagos reales.
            existente.estado = 'DISTRIBUCION_SIMULADA'
            existente.remanente_pendiente = Decimal('0.00')
            existente.save(update_fields=['estado', 'remanente_pendiente'])
            rev.estado_reversa = 'SIMULADA'
            rev.fecha_resolucion = ahora
            rev.referencia_externa = f'SIM-CANC-E{exp.pk}-R{rev.pk}'
            rev.save(update_fields=['estado_reversa', 'fecha_resolucion', 'referencia_externa'])
            liq.estado = 'DISTRIBUCION_SIMULADA'
            liq.save(update_fields=['estado'])
            pago.estado_pago = 'DISTRIBUIDO_SIMULADO'
            pago.save(update_fields=['estado_pago'])
            HistorialEstadoPago.objects.create(
                id_pago=pago, id_usuario_skilly=request.user,
                estado_anterior='RETENIDO', estado_nuevo='DISTRIBUIDO_SIMULADO',
                fecha_cambio=ahora, observacion=(
                    'Distribucion academica simulada, sin movimientos bancarios. '
                    'Cancelacion parcial; consultar conciliacion para montos por destinatario.'))
            registrar_evento_trazabilidad(
                usuario=request.user, entidad_tipo='conciliacion_reversa_e3',
                entidad_id=cierre_id, accion='CERRAR_DISTRIBUCION_SIMULADA',
                detalle_resumido=(f'Expediente {exp.pk}; devolucion {plan["organizacion"]}, '
                    f'profesional {plan["profesional_neto"]}, SKILLY {plan["skilly_total"]} CLP. '
                    'Sin dinero real.')[:255])
            plan['estado'] = 'DISTRIBUIDO_SIMULADO'
        return Response({'mensaje': 'Distribucion SIMULADA finalizada y registrada para las tres partes. NO se movio dinero real.',
                         'cierre': plan}, status=201)
