"""Webpay Plus exclusivo sandbox (E3 SKILLY).
La transferencia existente permanece intacta. No se realizan cargos reales.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from backoffice.models import ParametroSistema
from backoffice.services import registrar_evento_trazabilidad
from config.origenes import normalizar_origen_frontend
from coordinacion.models import PrestacionServicio
from marketplace.serializers import normalizar_precio_clp
from solicitudes.models import ReservaDisponibilidad, Disponibilidad
from solicitudes.referencias import leer_referencia_seguimiento, crear_referencia_seguimiento
from .models import Pago, HistorialEstadoPago
from seguimiento.aceptacion_politica_e3 import bloquear_pago_sin_aceptacion
from .serializers import PagoEstadoComunicableSerializer
from .webpay_cliente_e3 import iniciar, confirmar, autorizacion_valida, ErrorWebpay, RUTA_RETORNO_WEBPAY

PENDIENTE='PENDIENTE_WEBPAY'
RECHAZADO='WEBPAY_RECHAZADO'
REVISION='WEBPAY_REVISION_MANUAL'
ANULADO='WEBPAY_ANULADO'
RETENIDO_REVISION='RETENIDO_REVISION_AGENDA'


def origen_frontend():
    """Devuelve el origen frontend normalizado para construir destinos de retorno.

    Returns:
        str: Origen validado por la política local de configuración.

    Raises:
        ErrorWebpay: Si FRONTEND_ORIGIN no satisface esa política.
    """
    try:
        return normalizar_origen_frontend(settings.FRONTEND_ORIGIN)
    except ValueError:
        raise ErrorWebpay('El origen local del frontend no es válido.') from None


def retorno_webpay():
    """Devuelve la URL del callback añadiendo la ruta fija al origen validado.

    Raises:
        ErrorWebpay: Si el origen frontend no es válido.
    """
    return origen_frontend() + RUTA_RETORNO_WEBPAY


def sesion_pago(id_pago):
    """Devuelve el identificador de sesión Webpay derivado del id de pago recibido."""
    return f'SKSE3{id_pago}'
def orden_pago(id_pago):
    """Devuelve la orden Webpay estable derivada del id de pago recibido."""
    return f'SKWE3{id_pago}'


def contexto_pago(prestacion):
    """Calcula importes desde la oferta y la comisión configurada en el servidor.

    Args:
        prestacion (PrestacionServicio): Prestación PENDIENTE_CONTRATACION con
            condiciones comunicadas y servicio del mismo profesional.

    Returns:
        dict: Total CLP entero positivo, porcentaje a cuatro decimales, comisión
        y neto profesional. Usa ROUND_HALF_UP para porcentaje y comisión en centavos.

    Raises:
        ValueError: Si estado, condiciones, oferta, precio o comisión no son válidos.
    """
    if prestacion.estado != 'PENDIENTE_CONTRATACION' or not str(prestacion.condiciones_comunicadas or '').strip():
        raise ValueError('La prestación no está habilitada para contratar y pagar.')
    servicio = prestacion.id_solicitud.id_servicio
    if not servicio or servicio.id_profesional_id != prestacion.id_profesional_id:
        raise ValueError('La oferta no corresponde al profesional asignado.')
    try:
        precio=normalizar_precio_clp(servicio.referencia_precio,permitir_vacio=False)
        cantidad, moneda=precio.split()
        monto=Decimal(cantidad)
    except (ValidationError, InvalidOperation, ValueError, AttributeError):
        raise ValueError('El servicio no tiene un precio final válido.')
    if moneda != 'CLP' or monto <= 0 or not monto.is_finite() or monto != monto.to_integral_value():
        raise ValueError('Webpay requiere un precio positivo en pesos chilenos enteros.')
    parametro=ParametroSistema.objects.filter(clave='comision_porcentaje').first()
    try:
        porcentaje=Decimal(str(parametro.valor_actual).strip())
    except (AttributeError,InvalidOperation,TypeError,ValueError):
        raise ValueError('La comisión de SKILLY no está configurada.')
    if not porcentaje.is_finite() or not Decimal('0') <= porcentaje <= Decimal('100'):
        raise ValueError('El porcentaje de comisión no es válido.')
    porcentaje=porcentaje.quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
    comision=(monto*porcentaje/Decimal(100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return {'monto_total':monto,'moneda':'CLP','porcentaje_comision_aplicado':porcentaje,
            'monto_comision':comision,'monto_neto_profesional':monto-comision}


def horario_pendiente(prestacion, bloquear=False):
    """Revalida el horario de la selección pendiente de pago más reciente.

    Args:
        prestacion (PrestacionServicio): Solicitud y profesional esperados.
        bloquear (bool): Añade select_for_update a reserva y bloque; requiere
            transacción activa cuando es verdadero.

    Returns:
        tuple: Reserva y bloque si pertenecen al profesional, el bloque está
        DISPONIBLE, no tiene otra reserva ACTIVA y su inicio es futuro;
        ``(None, None)`` si falta alguno o falla esa validación.
    """
    consulta=ReservaDisponibilidad.objects
    if bloquear: consulta=consulta.select_for_update()
    reserva=(consulta.filter(id_solicitud_id=prestacion.id_solicitud_id,
                             estado='PENDIENTE_PAGO').order_by('-fecha_reserva','-id_reserva').first())
    if not reserva:return None,None
    bloque_consulta=Disponibilidad.objects
    if bloquear:bloque_consulta=bloque_consulta.select_for_update()
    bloque=bloque_consulta.filter(id_disponibilidad=reserva.id_disponibilidad_id).first()
    if not bloque or bloque.id_profesional_id!=prestacion.id_profesional_id or bloque.estado!='DISPONIBLE':
        return None,None
    if ReservaDisponibilidad.objects.filter(id_disponibilidad=bloque,estado='ACTIVA').exclude(id_reserva=reserva.id_reserva).exists():
        return None,None
    try:
        momento=timezone.make_aware(datetime.combine(bloque.fecha,bloque.hora_inicio),timezone.get_current_timezone())
    except ValueError:return None,None
    if momento<=timezone.now():return None,None
    return reserva,bloque


def redireccion(pago, resultado):
    """Construye el regreso al seguimiento con una referencia firmada nueva.

    Args:
        pago (Pago): Pago cuya solicitud aporta la identidad del seguimiento.
        resultado (str): Etiqueta de resultado para la interfaz, no prueba de autorización.

    Returns:
        HttpResponseRedirect: HTTP 302 al frontend con referencia y etiqueta Webpay.

    Raises:
        ErrorWebpay: Si el origen frontend configurado no es válido.
    """
    solicitud=pago.id_prestacion.id_solicitud
    referencia=crear_referencia_seguimiento(solicitud)
    query=urlencode({'referencia':referencia,'webpay':resultado})
    return HttpResponseRedirect(origen_frontend()+'/seguimiento?'+query)


def ambiente_disponible():
    """Devuelve si DEBUG habilita los endpoints de integración académica.

    No detecta el entorno de despliegue por otros medios; depende de esa configuración.
    """
    return bool(settings.DEBUG)


@method_decorator(csrf_protect,name='dispatch')
class IniciarWebpayPlusEmpresaView(APIView):
    """Inicia pagos de integración por referencia privada, con protección CSRF."""
    authentication_classes=[]
    permission_classes=[AllowAny]

    def post(self,request,referencia):
        """Crea o reinicia un pago de prueba y obtiene su formulario de Webpay.

        Args:
            request (Request): Petición pública protegida por CSRF; los importes
                se calculan en el servidor y no se toman de su cuerpo.
            referencia (str): Referencia firmada de solicitud y contacto.

        Returns:
            Response: HTTP 201 con URL, token y ambiente TRANSBANK_INTEGRACION;
            400 por referencia inválida, 404 si falta prestación, 409 por política,
            horario, importes o pago incompatible, 502 por fallo del cliente Webpay
            y 503 si DEBUG no habilita el entorno.

        Note:
            Mantiene bloqueados prestación, solicitud, reserva y pago durante el
            inicio remoto. Solo reutiliza pagos WEBPAY_PLUS rechazados o anulados;
            un error que sale de la transacción revierte los cambios locales.
        """
        if not ambiente_disponible():
            return Response({'mensaje':'Webpay de pruebas no está disponible en producción.'},status=503)
        datos=leer_referencia_seguimiento(referencia)
        if datos is None:
            return Response({'mensaje':'Referencia de seguimiento inválida.'},status=400)
        try:
            with transaction.atomic():
                prestacion=(PrestacionServicio.objects.select_for_update(of=('self', 'id_solicitud'))
                    .select_related('id_solicitud','id_solicitud__id_servicio')
                    .filter(id_solicitud_id=datos['id_solicitud'],
                            id_solicitud__id_contacto_id=datos['id_contacto']).first())
                if not prestacion:return Response({'mensaje':'Prestación no encontrada.'},status=404)
                bloquear_pago_sin_aceptacion(prestacion)
                importes=contexto_pago(prestacion)
                reserva,bloque=horario_pendiente(prestacion,bloquear=True)
                if reserva is None:
                    return Response({'mensaje':'Debes seleccionar un horario futuro disponible antes de pagar.'},status=409)
                pago=(Pago.objects.select_for_update().filter(id_prestacion=prestacion).first())
                if pago:
                    if pago.metodo_pago!='WEBPAY_PLUS' or pago.estado_pago not in (RECHAZADO,ANULADO):
                        return Response({'mensaje':'Esta prestación ya tiene una operación de pago. Consulta su estado.'},status=409)
                    for campo,valor in importes.items():setattr(pago,campo,valor)
                    pago.estado_pago=PENDIENTE
                    pago.estado_verificacion='PENDIENTE'
                    pago.referencia_transaccion=None
                    pago.fecha_pago=None
                    pago.fecha_retencion=None
                    pago.save(update_fields=[*importes,'estado_pago','estado_verificacion','referencia_transaccion','fecha_pago','fecha_retencion'])
                else:
                    pago=Pago.objects.create(id_prestacion=prestacion,**importes,
                        estado_pago=PENDIENTE,metodo_pago='WEBPAY_PLUS',
                        proveedor_pago='TRANSBANK_INTEGRACION',estado_verificacion='PENDIENTE',
                        comprobante_transferencia=None,fecha_pago=None,fecha_retencion=None,
                        fecha_liberacion=None,referencia_transaccion=None)
                # Bloqueo de prestación y pago hasta obtener token para impedir inicios concurrentes.
                resultado=iniciar(orden_pago(pago.id_pago),sesion_pago(pago.id_pago),
                                  pago.monto_total,retorno_webpay())
                pago.referencia_transaccion=resultado['token']
                pago.save(update_fields=['referencia_transaccion'])
                HistorialEstadoPago.objects.create(id_pago=pago,id_usuario_skilly=None,
                    estado_anterior=None,estado_nuevo=PENDIENTE,fecha_cambio=timezone.now(),
                    observacion='Webpay Plus: inicio de transacción en ambiente de integración; sin dinero real.')
                registrar_evento_trazabilidad(usuario=None,entidad_tipo='pago',entidad_id=pago.id_pago,
                    accion='INICIAR_WEBPAY_E3',detalle_resumido=f'Iniciado pago Webpay sandbox #{pago.id_pago}.')
            return Response({'mensaje':'Continúa en el ambiente de pruebas de Webpay Plus.',
                             'url':resultado['url'],'token':resultado['token'],
                             'ambiente':'TRANSBANK_INTEGRACION'},status=201)
        except (ErrorWebpay,ValueError) as e:
            return Response({'mensaje':str(e)},status=502 if isinstance(e,ErrorWebpay) else 409)


@method_decorator(csrf_exempt,name='dispatch')
class RetornoWebpayPlusEmpresaView(APIView):
    """Procesa el callback público del proveedor sin exigir cookie CSRF.

    La excepción CSRF permite el retorno externo. El éxito se decide consultando
    Webpay y contrastando token, orden, sesión e importe con el pago persistido.
    """
    authentication_classes=[]
    permission_classes=[AllowAny]
    http_method_names=['get','post','head','options']

    def get(self,request):
        """Procesa los parámetros de retorno GET con el contrato común del callback."""
        return self._procesar(request)
    def post(self,request):
        """Procesa el cuerpo de retorno POST con el contrato común del callback."""
        return self._procesar(request)

    def _procesar(self,request):
        """Confirma el resultado de integración y activa la reserva si sigue disponible.

        Args:
            request (Request): Parámetros GET o cuerpo POST con token_ws; TBK_TOKEN
                sin token_ws indica abandono o anulación del formulario.

        Returns:
            HttpResponseRedirect | Response: HTTP 302 al seguimiento con el resultado;
            400 por token inválido, 404 por transacción desconocida, 409 por estado
            incompatible o 503 por entorno deshabilitado/fallo de comunicación.

        Note:
            El bloqueo del pago serializa callbacks. Los estados ya retenidos,
            rechazados o anulados se reutilizan sin confirmar otra vez. Una aparente
            autorización con identidad o importe discordantes queda en revisión manual.
            Si la autorización coincide pero la agenda perdió vigencia, se conserva
            RETENIDO_REVISION_AGENDA sin activar reserva ni formalizar contratación.
        """
        if not ambiente_disponible():return Response({'mensaje':'Webpay sandbox deshabilitado.'},status=503)
        token=request.data.get('token_ws') if request.method=='POST' else request.query_params.get('token_ws')
        cancelado=request.data.get('TBK_TOKEN') if request.method=='POST' else request.query_params.get('TBK_TOKEN')
        if not token and not cancelado:
            return Response({'mensaje':'Webpay no entregó token de retorno.'},status=400)
        token=token or cancelado
        if not isinstance(token,str) or not 5<=len(token)<=200:
            return Response({'mensaje':'Token inválido.'},status=400)
        try:
            with transaction.atomic():
                pago=(Pago.objects.select_for_update().select_related('id_prestacion__id_solicitud')
                      .filter(metodo_pago='WEBPAY_PLUS',referencia_transaccion=token).first())
                if pago is None:return Response({'mensaje':'Transacción desconocida.'},status=404)
                if pago.estado_pago in ('RETENIDO',RETENIDO_REVISION):return redireccion(pago,'aprobado')
                if pago.estado_pago in (RECHAZADO,ANULADO):return redireccion(pago,'no_aprobado')
                if pago.estado_pago!=PENDIENTE:
                    return Response({'mensaje':'Transacción con estado incompatible.'},status=409)
                if cancelado and not (request.data.get('token_ws') if request.method=='POST' else request.query_params.get('token_ws')):
                    pago.estado_pago=ANULADO
                    pago.estado_verificacion='RECHAZADO'
                    pago.save(update_fields=['estado_pago','estado_verificacion'])
                    HistorialEstadoPago.objects.create(id_pago=pago,estado_anterior=PENDIENTE,
                        estado_nuevo=ANULADO,fecha_cambio=timezone.now(),
                        observacion='El usuario abandonó o anuló la operación en el sandbox Webpay.')
                    return redireccion(pago,'cancelado')
                respuesta=confirmar(token)  # SIEMPRE consultado con proveedor, nunca con datos del navegador.
                autorizado=autorizacion_valida(respuesta,monto=pago.monto_total,
                                               buy_order=orden_pago(pago.id_pago),
                                               session_id=sesion_pago(pago.id_pago))
                previo=pago.estado_pago
                ahora=timezone.now()
                if not autorizado:
                    # Una autorización con identidad o importe discordantes NO es
                    # un rechazo: debe quedar inmovilizada para conciliación.
                    riesgo=(respuesta.get('status') == 'AUTHORIZED' and
                            respuesta.get('response_code') == 0)
                    pago.estado_pago=REVISION if riesgo else RECHAZADO
                    pago.estado_verificacion='PENDIENTE' if riesgo else 'RECHAZADO'
                    pago.save(update_fields=['estado_pago','estado_verificacion'])
                    HistorialEstadoPago.objects.create(id_pago=pago,estado_anterior=previo,
                        estado_nuevo=pago.estado_pago,fecha_cambio=ahora,
                        observacion=('Transbank informó autorización con monto/orden/sesión discordante. '
                                     'REVISAR ANTES DE COBRAR O DEVOLVER.' if riesgo else
                                     'Webpay no autorizó la operación.'))
                    return redireccion(pago,'revision' if riesgo else 'no_aprobado')
                prestacion=(PrestacionServicio.objects.select_for_update()
                            .filter(id_prestacion=pago.id_prestacion_id).first())
                reserva,bloque=horario_pendiente(prestacion,bloquear=True) if prestacion else (None,None)
                agenda_ok=bool(prestacion and prestacion.estado=='PENDIENTE_CONTRATACION' and reserva and bloque)
                pago.estado_pago='RETENIDO' if agenda_ok else RETENIDO_REVISION
                pago.estado_verificacion='VERIFICADO'
                pago.fecha_pago=ahora
                pago.fecha_retencion=ahora
                pago.save(update_fields=['estado_pago','estado_verificacion','fecha_pago','fecha_retencion'])
                if agenda_ok:
                    reserva.estado='ACTIVA'
                    reserva.fecha_cambio=ahora
                    reserva.motivo_cambio='Reserva confirmada tras Webpay sandbox autorizado.'
                    reserva.save(update_fields=['estado','fecha_cambio','motivo_cambio'])
                    bloque.estado='RESERVADA'
                    bloque.save(update_fields=['estado'])
                HistorialEstadoPago.objects.create(id_pago=pago,estado_anterior=previo,
                    estado_nuevo=pago.estado_pago,fecha_cambio=ahora,
                    observacion=('Transbank integración confirmó AUTHORIZED y response_code=0. '
                                 +('Horario confirmado.' if agenda_ok else 'Requiere resolución administrativa de agenda.')))
                registrar_evento_trazabilidad(usuario=None,entidad_tipo='pago',entidad_id=pago.id_pago,
                    accion='CONFIRMAR_WEBPAY_E3',detalle_resumido=f'Pago sandbox #{pago.id_pago}: {pago.estado_pago}.')
                return redireccion(pago,'aprobado' if agenda_ok else 'agenda_pendiente')
        except ErrorWebpay:
            # NO declarar rechazo ni éxito ante caída de comunicación.
            return Response({'mensaje':'No fue posible consultar Transbank. Pago pendiente de conciliación; no intentes un segundo cobro.'},status=503)
