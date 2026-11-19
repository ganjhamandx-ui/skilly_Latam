"""Expediente privado de cancelacion; no ejecuta cancelacion ni devolucion."""
import hashlib
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import models, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly, EsProfesional
from backoffice.models import ParametroSistema
from backoffice.services import registrar_evento_trazabilidad
from coordinacion.models import PrestacionServicio
from pagos.models import Pago
from profesionales.models import Profesional
from solicitudes.referencias import leer_referencia_seguimiento
from .models import AvanceServicio, ReclamoPrestacion
from .politica_liquidacion_cancelacion_e3 import proyectar_liquidacion
from .aceptacion_politica_e3 import AceptacionPoliticaCancelacion, obtener_prestacion


class ExpedienteCancelacion(models.Model):
    id_expediente = models.BigAutoField(primary_key=True)
    id_prestacion = models.ForeignKey(PrestacionServicio, models.DO_NOTHING, db_column='id_prestacion')
    id_reclamo = models.ForeignKey(ReclamoPrestacion, models.DO_NOTHING, db_column='id_reclamo', null=True)
    id_avance = models.ForeignKey(AvanceServicio, models.DO_NOTHING, db_column='id_avance', null=True)
    origen = models.CharField(max_length=20)
    motivo = models.CharField(max_length=120)
    descripcion = models.TextField()
    evidencia_nombre = models.CharField(max_length=150, null=True)
    evidencia_mime = models.CharField(max_length=40, null=True)
    evidencia_sha256 = models.CharField(max_length=64, null=True)
    evidencia_contenido = models.BinaryField(null=True)
    fecha_registro = models.DateTimeField()
    estado = models.CharField(max_length=25)
    decision = models.CharField(max_length=45, null=True)
    fundamento = models.TextField(null=True)
    fecha_resolucion = models.DateTimeField(null=True)
    id_administrador = models.BigIntegerField(null=True)
    porcentaje_referencia = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    monto_trabajo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    cargo_ejecutado = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    cargo_teorico = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    devolucion_propuesta = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 'expediente_cancelacion_e3'


class SolicitudSerializer(serializers.Serializer):
    motivo = serializers.CharField(min_length=5, max_length=120)
    descripcion = serializers.CharField(min_length=20, max_length=2000)


class ResolucionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['JUSTIFICADA', 'INJUSTIFICADA', 'INCUMPLIMIENTO_CONTRAPARTE', 'RECHAZAR_SOLICITUD'])
    fundamento = serializers.CharField(min_length=20, max_length=2000)
    monto_trabajo_acreditado = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'), default=Decimal('0'))


MIME = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
MAX_BYTES = 5 * 1024 * 1024


def evidencia_validada(archivo):
    if not archivo:
        return {}
    nombre = os.path.basename((archivo.name or '').replace('\\', '/'))[:150]
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in MIME or archivo.size > MAX_BYTES or archivo.size == 0:
        raise serializers.ValidationError({'evidencia': 'Solo PDF, JPG o PNG de 1 byte a 5 MB.'})
    contenido = archivo.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise serializers.ValidationError({'evidencia': 'El archivo supera 5 MB.'})
    if extension == '.pdf':
        valido = contenido.startswith(b'%PDF-')
    elif extension == '.png':
        valido = contenido.startswith(b'\x89PNG\r\n\x1a\n')
    else:
        valido = contenido.startswith(b'\xff\xd8\xff') and contenido.endswith(b'\xff\xd9')
    if not valido:
        raise serializers.ValidationError({'evidencia': 'Contenido y extension del archivo no coinciden.'})
    if archivo.content_type not in (MIME[extension], 'application/octet-stream'):
        raise serializers.ValidationError({'evidencia': 'Tipo MIME incompatible con el archivo.'})
    return {'evidencia_nombre': nombre, 'evidencia_mime': MIME[extension],
            'evidencia_sha256': hashlib.sha256(contenido).hexdigest(),
            'evidencia_contenido': contenido}



def desglose_cancelacion_admin(exp, pago, aceptacion):
    """Proyección interna: no libera, cobra ni devuelve fondos."""
    if not pago or exp.estado != 'RESUELTO' or exp.monto_trabajo is None:
        return None
    if pago.estado_pago != 'RETENIDO' or pago.estado_verificacion != 'VERIFICADO':
        return None
    total = Decimal(pago.monto_total)
    trabajo = Decimal(exp.monto_trabajo)
    pct_comision = Decimal(pago.porcentaje_comision_aplicado)
    if (not all(x.is_finite() for x in (total, trabajo, pct_comision))
            or total <= 0 or trabajo < 0 or trabajo > total
            or not Decimal('0') <= pct_comision <= Decimal('100')):
        return None
    comision = (trabajo * pct_comision / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP)
    neto_profesional = trabajo - comision
    aceptacion_previa = bool(
        aceptacion and pago.fecha_pago
        and aceptacion.fecha_aceptacion <= pago.fecha_pago
        and exp.porcentaje_referencia is not None
        and Decimal(exp.porcentaje_referencia) == Decimal(aceptacion.porcentaje_aceptado))
    cargo_cancelacion = Decimal('0')
    if (exp.origen == 'ORGANIZACION' and exp.decision == 'INJUSTIFICADA'
            and aceptacion_previa and exp.cargo_teorico is not None):
        cargo_cancelacion = Decimal(exp.cargo_teorico)
    if cargo_cancelacion < 0 or cargo_cancelacion > total - trabajo:
        return None
    devolucion_prevista = total - trabajo - cargo_cancelacion
    return {
        'porcentaje_comision_servicio': str(pct_comision),
        'comision_skilly_trabajo': str(comision),
        'neto_profesional_trabajo': str(neto_profesional),
        'cargo_skilly_cancelacion': str(cargo_cancelacion),
        'total_skilly_previsto': str(comision + cargo_cancelacion),
        'devolucion_organizacion_prevista': str(devolucion_prevista),
        'aceptacion_cancelacion_previa': aceptacion_previa,
    }


def datos_expediente(exp, *, desglose=None):
    datos = {
        'id_expediente': exp.id_expediente, 'id_prestacion': exp.id_prestacion_id,
        'id_reclamo': exp.id_reclamo_id, 'id_avance': exp.id_avance_id,
        'origen': exp.origen, 'motivo': exp.motivo, 'descripcion': exp.descripcion,
        'evidencia_disponible': bool(exp.evidencia_nombre), 'evidencia_nombre': exp.evidencia_nombre,
        'estado': exp.estado, 'fecha_registro': exp.fecha_registro,
        'decision': exp.decision, 'fundamento': exp.fundamento,
        'fecha_resolucion': exp.fecha_resolucion,
        'porcentaje_referencia': exp.porcentaje_referencia,
        'monto_total': exp.monto_total, 'monto_trabajo': exp.monto_trabajo,
        'cargo_teorico': exp.cargo_teorico, 'cargo_ejecutado': exp.cargo_ejecutado,
        'devolucion_propuesta': exp.devolucion_propuesta,
        'nota': 'Evaluacion de expediente. La resolucion de reclamo, cancelacion de prestacion y reversa bancaria son operaciones separadas.',
    }
    if desglose is not None:
        datos['desglose_economico'] = desglose
    return datos


def construir_expediente(*, prestacion, origen, data, archivo, usuario=None, id_contacto=None):
    entrada = SolicitudSerializer(data=data)
    entrada.is_valid(raise_exception=True)
    evidencia = evidencia_validada(archivo)
    with transaction.atomic():
        prestacion = PrestacionServicio.objects.select_for_update().get(pk=prestacion.pk)
        if prestacion.estado != 'CONTRATADA':
            return Response({'mensaje': 'Las cancelaciones formales corresponden a prestaciones CONTRATADAS.'}, status=409)
        if ExpedienteCancelacion.objects.filter(id_prestacion=prestacion, estado__in=['PENDIENTE', 'EN_REVISION']).exists():
            return Response({'mensaje': 'Esta prestación ya tiene un expediente de cancelación pendiente.'}, status=409)
        reclamo = None
        avance = None
        if origen == 'ORGANIZACION':
            if ReclamoPrestacion.objects.filter(id_prestacion=prestacion, fecha_cierre__isnull=True).exists():
                return Response({'mensaje': 'La prestación ya tiene un reclamo sin resolver. Administración debe revisarlo.'}, status=409)
            reclamo = ReclamoPrestacion.objects.create(
                id_prestacion=prestacion, id_contacto_id=id_contacto,
                motivo='Cancelación solicitada por la organización',
                descripcion=entrada.validated_data['descripcion'], estado='ABIERTO', fecha_registro=timezone.now())
        else:
            avance = AvanceServicio.objects.create(
                id_prestacion=prestacion, estado='INCIDENCIA_PROFESIONAL',
                detalle=f"SOLICITUD_CANCELACION | {entrada.validated_data['motivo']} | {entrada.validated_data['descripcion']}",
                fecha_registro=timezone.now())
        exp = ExpedienteCancelacion.objects.create(
            id_prestacion=prestacion, origen=origen, id_reclamo=reclamo, id_avance=avance,
            motivo=entrada.validated_data['motivo'], descripcion=entrada.validated_data['descripcion'],
            fecha_registro=timezone.now(), estado='PENDIENTE', **evidencia)
        registrar_evento_trazabilidad(
            usuario=usuario, entidad_tipo='expediente_cancelacion_e3', entidad_id=exp.id_expediente,
            accion='SOLICITAR_CANCELACION', detalle_resumido=f'Prestación {prestacion.pk}: cancelación solicitada por {origen}; pendiente de revisión.'[:255])
    return Response({'mensaje': 'Solicitud de cancelación y antecedentes registrados. No se ha cancelado la prestación ni movido dinero.', 'expediente': datos_expediente(exp)}, status=201)


@method_decorator(csrf_protect, name='dispatch')
class CancelacionOrganizacionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, referencia):
        datos = leer_referencia_seguimiento(referencia)
        if not datos:
            return Response({'mensaje': 'Referencia inválida.'}, status=400)
        prestacion = PrestacionServicio.objects.filter(
            id_solicitud_id=datos['id_solicitud'], id_solicitud__id_contacto_id=datos['id_contacto']).first()
        if not prestacion:
            return Response({'mensaje': 'No existe una prestación asociada a la referencia.'}, status=404)
        return construir_expediente(prestacion=prestacion, origen='ORGANIZACION', data=request.data,
                                   archivo=request.FILES.get('evidencia'), id_contacto=datos['id_contacto'])


@method_decorator(csrf_protect, name='dispatch')
class CancelacionProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, id_prestacion):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        prestacion = PrestacionServicio.objects.filter(pk=id_prestacion, id_profesional=profesional).first() if profesional else None
        if not prestacion:
            return Response({'mensaje': 'Prestación no encontrada o no te pertenece.'}, status=404)
        return construir_expediente(prestacion=prestacion, origen='PROFESIONAL', data=request.data,
                                   archivo=request.FILES.get('evidencia'), usuario=request.user)


class ExpedientesCancelacionAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        expedientes = list(ExpedienteCancelacion.objects.order_by('-fecha_registro', '-id_expediente')[:100])
        ids = {e.id_prestacion_id for e in expedientes if e.estado == 'RESUELTO'}
        pagos = {p.id_prestacion_id: p for p in Pago.objects.filter(id_prestacion_id__in=ids)}
        aceptaciones = {a.id_prestacion_id: a for a in AceptacionPoliticaCancelacion.objects.filter(id_prestacion_id__in=ids)}
        return Response({'expedientes': [datos_expediente(
            e, desglose=desglose_cancelacion_admin(
                e, pagos.get(e.id_prestacion_id), aceptaciones.get(e.id_prestacion_id)))
            for e in expedientes]})


class ExpedienteCancelacionAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        exp = ExpedienteCancelacion.objects.filter(pk=id_expediente).first()
        if not exp:
            return Response({'mensaje': 'Expediente no encontrado.'}, status=404)
        pago = Pago.objects.filter(id_prestacion_id=exp.id_prestacion_id).first()
        aceptacion = AceptacionPoliticaCancelacion.objects.filter(id_prestacion_id=exp.id_prestacion_id).first()
        return Response({'expediente': datos_expediente(
            exp, desglose=desglose_cancelacion_admin(exp, pago, aceptacion))})

    @method_decorator(csrf_protect)
    def patch(self, request, id_expediente):
        entrada = ResolucionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        with transaction.atomic():
            exp = ExpedienteCancelacion.objects.select_for_update().filter(pk=id_expediente).first()
            if not exp:
                return Response({'mensaje': 'Expediente no encontrado.'}, status=404)
            if exp.estado != 'PENDIENTE':
                return Response({'mensaje': 'El expediente ya fue resuelto.'}, status=409)
            pago = Pago.objects.select_for_update().filter(id_prestacion=exp.id_prestacion).first()
            total = (Decimal(pago.monto_total) if pago and pago.estado_pago == 'RETENIDO' and
                     pago.estado_verificacion == 'VERIFICADO' else Decimal('0'))
            trabajo = datos['monto_trabajo_acreditado']
            if trabajo > total:
                return Response({'mensaje': 'El trabajo acreditado supera el pago retenido verificado.'}, status=409)
            # Porcentaje CONGELADO al contratar; NUNCA usar el actual para contratos antiguos.
            aceptacion = AceptacionPoliticaCancelacion.objects.filter(id_prestacion=exp.id_prestacion).first()
            porcentaje = Decimal(aceptacion.porcentaje_aceptado) if aceptacion else Decimal('0')
            if not porcentaje.is_finite() or not Decimal('0') <= porcentaje <= Decimal('100'):
                return Response({'mensaje': 'Porcentaje fuera de rango.'}, status=409)
            try:
                proyeccion = proyectar_liquidacion(
                    monto_total=total, monto_trabajo=trabajo, porcentaje=porcentaje,
                    origen=exp.origen, decision=datos['decision'])
            except ValueError as error:
                return Response({'mensaje': str(error)}, status=409)
            exp.estado = 'RESUELTO'
            exp.decision = datos['decision']
            exp.fundamento = datos['fundamento']
            exp.fecha_resolucion = timezone.now()
            exp.id_administrador = request.user.pk
            exp.porcentaje_referencia = porcentaje
            exp.monto_total = total
            exp.monto_trabajo = trabajo
            exp.cargo_teorico = proyeccion["cargo_teorico"]
            exp.cargo_ejecutado = proyeccion["cargo_ejecutado"]
            exp.devolucion_propuesta = proyeccion["devolucion_propuesta"]
            exp.save(update_fields=['estado', 'decision', 'fundamento', 'fecha_resolucion',
                                    'id_administrador', 'porcentaje_referencia', 'monto_total',
                                    'monto_trabajo', 'cargo_teorico', 'cargo_ejecutado', 'devolucion_propuesta'])
            registrar_evento_trazabilidad(
                usuario=request.user, entidad_tipo='expediente_cancelacion_e3', entidad_id=exp.id_expediente,
                accion='EVALUAR_CANCELACION', detalle_resumido=f'Expediente {exp.pk} {exp.decision}; cargo ejecutado $0, sin mover dinero.'[:255])
        return Response({'mensaje': 'Evaluación guardada. Cargo efectivamente aplicado: $0. No hubo cancelación ni reembolso automático.',
                         'expediente': datos_expediente(
                             exp, desglose=desglose_cancelacion_admin(exp, pago, aceptacion))})


class EvidenciaCancelacionAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        exp = ExpedienteCancelacion.objects.filter(pk=id_expediente).first()
        if not exp or not exp.evidencia_nombre or not exp.evidencia_contenido:
            return Response({'mensaje': 'No existe evidencia.'}, status=404)
        response = HttpResponse(bytes(exp.evidencia_contenido), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="expediente-{exp.pk}{os.path.splitext(exp.evidencia_nombre)[1]}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class EstadoCancelacionOrganizacionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        prestacion = obtener_prestacion(referencia)
        if not prestacion:
            return Response({'mensaje': 'Solicitud no encontrada.'}, status=404)
        exp = ExpedienteCancelacion.objects.filter(id_prestacion=prestacion).order_by('-fecha_registro').first()
        if not exp:
            return Response({'expediente': None})
        if exp.estado != 'RESUELTO':
            return Response({'expediente': {'estado': exp.estado,
                'mensaje': 'SKILLY está revisando la solicitud; todavía no hay decisión económica.'}})
        from .liquidacion_cancelacion_e3 import LiquidacionCancelacionE3
        liq = LiquidacionCancelacionE3.objects.filter(id_expediente=exp).first()
        motivos_publicos = {
            'JUSTIFICADA': 'Cancelación justificada según revisión administrativa; no corresponde cargo de cancelación.',
            'INJUSTIFICADA': 'Cancelación sin causa suficiente acreditada; se informa el cálculo de gestión sujeto a los derechos aplicables.',
            'INCUMPLIMIENTO_CONTRAPARTE': 'Incumplimiento de la contraparte reconocido en la evaluación; se resguardan los derechos de la parte afectada.',
            'RECHAZAR_SOLICITUD': 'La cancelación solicitada no fue aprobada y la prestación continúa su curso según resolución.'
        }
        return Response({'expediente': {
            'estado': exp.estado, 'decision': exp.decision,
            'motivo_publico': motivos_publicos.get(exp.decision, 'Evaluación administrativa registrada.'),
            'porcentaje_contratado': str(exp.porcentaje_referencia or 0),
            'monto_total': str(exp.monto_total or 0), 'monto_trabajo': str(exp.monto_trabajo or 0),
            'cargo_teorico': str(exp.cargo_teorico or 0), 'cargo_aplicado': str(exp.cargo_ejecutado or 0),
            'devolucion_propuesta': str(exp.devolucion_propuesta) if exp.devolucion_propuesta is not None else None,
            'liquidacion': ({'estado':liq.estado,'cargo_autorizado':str(liq.cargo_autorizado),
                'monto_devolucion':str(liq.monto_devolucion),
                'id_reversa':liq.id_reversa_id,
                'mensaje':'Liquidación autorizada; devolución pendiente. No se ha transferido dinero.'}
                if liq else None),
            'mensaje': 'La evaluación no acredita un descuento ejecutado ni dinero devuelto. Consulta el estado del pago.'
        }})
