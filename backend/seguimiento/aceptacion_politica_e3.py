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
    """Conserva la política de cancelación aceptada para una prestación."""

    id_aceptacion = models.BigAutoField(primary_key=True)
    id_prestacion = models.OneToOneField(PrestacionServicio, models.DO_NOTHING, db_column='id_prestacion')
    porcentaje_aceptado = models.DecimalField(max_digits=7, decimal_places=4)
    version_politica = models.CharField(max_length=64)
    texto_aceptado = models.TextField()
    fecha_aceptacion = models.DateTimeField()

    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `aceptacion_politica_cancelacion_e3`."""

        managed = False
        db_table = 'aceptacion_politica_cancelacion_e3'


def politica_actual():
    """Obtiene versión, porcentaje y texto vigentes desde el parámetro administrativo.

    Returns:
        dict: Porcentaje Decimal, texto informativo y versión SHA-256 de ese texto.

    Raises:
        ValueError: Si el parámetro no existe o su porcentaje es inválido.
    """

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
    """Resuelve una prestación desde referencia privada y opcionalmente la bloquea.

    Args:
        referencia (str): Referencia firmada con solicitud y contacto empresarial.
        bloquear (bool): Aplica select_for_update; el llamador mantiene la transacción.

    Returns:
        PrestacionServicio | None: Primera prestación de esa solicitud y contacto,
        o None si la referencia es inválida o no existe coincidencia.
    """

    datos = leer_referencia_seguimiento(referencia)
    if not datos:
        return None
    consulta = PrestacionServicio.objects
    if bloquear:
        consulta = consulta.select_for_update()
    return consulta.filter(id_solicitud_id=datos['id_solicitud'],
        id_solicitud__id_contacto_id=datos['id_contacto']).first()


def detalle_politica(aceptacion):
    """Serializa la aceptación persistida para mostrarla a la empresa.

    Args:
        aceptacion (AceptacionPoliticaCancelacion): Registro autorizado para consulta.

    Returns:
        dict: Porcentaje como texto, versión, texto aceptado, fecha y mensaje
        que informa que el porcentaje quedó fijado para esa contratación.
    """

    return {'aceptada': True, 'porcentaje': str(aceptacion.porcentaje_aceptado),
            'version': aceptacion.version_politica, 'texto': aceptacion.texto_aceptado,
            'fecha_aceptacion': aceptacion.fecha_aceptacion,
            'mensaje': 'Este porcentaje quedó fijado para esta contratación. Cambios posteriores no lo modifican.'}


def bloquear_pago_sin_aceptacion(prestacion):
    """Exige aceptación previa únicamente cuando todavía no existe un pago.

    El llamador ejecuta esta comprobación en la transacción del pago, después
    de bloquear la prestación. Los pagos existentes conservan la compatibilidad
    con contrataciones anteriores a la política versionada.

    Args:
        prestacion (PrestacionServicio): Prestación cuyo pago se iniciará.

    Returns:
        None: Permite continuar si existe aceptación o cualquier pago previo.

    Raises:
        ValueError: Si no hay aceptación ni operación de pago existente.
    """
    if AceptacionPoliticaCancelacion.objects.filter(id_prestacion=prestacion).exists():
        return
    # Operaciones iniciadas antes de la implementación: no imponer condiciones retroactivas.
    if Pago.objects.filter(id_prestacion=prestacion).exists():
        return
    raise ValueError('Antes de iniciar el pago debes leer y aceptar la política de cancelación vigente.')

@method_decorator(csrf_protect, name='dispatch')
class PoliticaCancelacionEmpresaView(APIView):
    """Consulta y registra aceptación empresarial de la política versionada."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        """Consulta la política fijada o la versión disponible para una aceptación nueva.

        Args:
            request: Petición sin sesión autenticada.
            referencia (str): Referencia empresarial firmada de la prestación.

        Returns:
            Response: 200 con aceptación persistida, indicación de contrato previo
            con pago o política vigente aún no aceptada; 404 si no resuelve prestación
            y 409 si falta una configuración válida para una aceptación nueva.
        """
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
        """Registra una aceptación idempotente antes del primer pago.

        Args:
            request: Petición con acepto igual al booleano True y version de 64
                caracteres correspondiente al texto mostrado a la empresa.
            referencia (str): Referencia empresarial firmada.

        Returns:
            Response: 201 al fijar la aceptación, 200 si ya existía, 400 por entrada
            inválida, 404 si falta prestación o 409 por falta de habilitación, pago
            previo o versión desactualizada. El reintento con entrada válida devuelve
            lo ya aceptado, aunque después haya cambiado la política del sistema.
        """
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
