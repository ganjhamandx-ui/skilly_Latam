"""Expediente privado de cancelacion; no ejecuta cancelacion ni devolucion."""
import hashlib
import os
from decimal import Decimal, InvalidOperation

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
    """Conserva antecedentes, evidencia y resolución de una cancelación."""

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
        """Vincula el expediente con su tabla SQL preexistente, sin gestión de esquema por Django."""
        managed = False
        db_table = 'expediente_cancelacion_e3'


class SolicitudSerializer(serializers.Serializer):
    """Valida motivo y descripción de una solicitud de cancelación."""

    motivo = serializers.CharField(min_length=5, max_length=120)
    descripcion = serializers.CharField(min_length=20, max_length=2000)


class ResolucionSerializer(serializers.Serializer):
    """Valida la decisión y fundamento administrativo del expediente."""

    decision = serializers.ChoiceField(choices=['JUSTIFICADA', 'INJUSTIFICADA', 'INCUMPLIMIENTO_CONTRAPARTE', 'RECHAZAR_SOLICITUD'])
    fundamento = serializers.CharField(min_length=20, max_length=2000)
    monto_trabajo_acreditado = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'), default=Decimal('0'))


MIME = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
MAX_BYTES = 5 * 1024 * 1024


def evidencia_validada(archivo):
    """Valida una evidencia opcional y calcula la huella de sus bytes.

    Args:
        archivo: Archivo cargado con name, size, content_type y lectura binaria;
            None permite abrir el expediente sin evidencia.

    Returns:
        dict: Nombre sin directorios, MIME, SHA-256 y contenido binario, o dict
        vacío si falta el archivo. La lectura no restablece el cursor.

    Raises:
        serializers.ValidationError: Si extensión, tamaño, firma o MIME no
            corresponden a PDF, PNG o JPEG de hasta 5 MiB. No valida íntegramente
            el archivo ni calcula una firma autenticada.
    """

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


def datos_expediente(exp):
    """Serializa el expediente sin incluir los bytes privados de su evidencia.

    Args:
        exp (ExpedienteCancelacion): Expediente autorizado para consulta.

    Returns:
        dict: Antecedentes, nombre de evidencia, decisión y montos conservados.
        Incluye descripción y fundamento internos; las respuestas empresariales
        reducidas se construyen por separado en EstadoCancelacionOrganizacionView.
    """

    return {
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


def construir_expediente(*, prestacion, origen, data, archivo, usuario=None, id_contacto=None):
    """Crea un expediente, su antecedente y trazabilidad en una transacción.

    Args:
        prestacion (PrestacionServicio): Prestación cuyo acceso autorizó la vista.
        origen (str): ORGANIZACION crea un reclamo; el flujo PROFESIONAL crea
            un avance privado de incidencia.
        data: Mapeo con motivo y descripcion.
        archivo: Evidencia opcional que se valida antes de persistir.
        usuario: Usuario responsable para trazabilidad, o None para la empresa.
        id_contacto (int | None): Contacto empresarial del reclamo organizacional.

    Returns:
        Response: 201 con el expediente o 409 si la prestación no está CONTRATADA,
        ya tiene expediente pendiente/en revisión o la organización tiene un
        reclamo sin cerrar. No cancela la prestación ni modifica pagos.

    Raises:
        serializers.ValidationError: Si los datos o la evidencia son inválidos;
            DRF los convierte en una respuesta 400.
    """

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
    """Permite a la organización iniciar cancelación mediante referencia privada."""

    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, referencia):
        """Abre un expediente organizacional usando una referencia privada válida.

        Args:
            request: Petición multipart con motivo, descripcion y evidencia opcional.
            referencia (str): Referencia firmada de solicitud y contacto empresarial.

        Returns:
            Response: 201 al registrar el expediente, 400 por referencia o datos
            inválidos, 404 si no hay prestación coincidente y 409 por las restricciones
            de apertura comprobadas por construir_expediente.
        """
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
    """Permite al profesional asignado aportar antecedentes para evaluar una cancelación."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, id_prestacion):
        """Abre un expediente para una prestación perteneciente al profesional.

        Args:
            request: Petición autenticada multipart con motivo, descripcion y
                evidencia opcional; no exige que la causa ya haya sido justificada.
            id_prestacion (int): Prestación del profesional autenticado.

        Returns:
            Response: 201 con el expediente, 400 por datos/evidencia inválidos,
            404 por perfil o prestación ajena/inexistente y 409 por estado incompatible
            o expediente pendiente. La justificación se decide posteriormente.
        """
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        prestacion = PrestacionServicio.objects.filter(pk=id_prestacion, id_profesional=profesional).first() if profesional else None
        if not prestacion:
            return Response({'mensaje': 'Prestación no encontrada o no te pertenece.'}, status=404)
        return construir_expediente(prestacion=prestacion, origen='PROFESIONAL', data=request.data,
                                   archivo=request.FILES.get('evidencia'), usuario=request.user)


class ExpedientesCancelacionAdminView(APIView):
    """Lista los expedientes recientes de todos los estados para administración."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        """Lista los cien expedientes más recientes sin incluir bytes de evidencia.

        Args:
            request: Petición administrativa autenticada.

        Returns:
            Response: 200 con expedientes y proyección económica cuando procede,
            ordenados por fecha e identificador descendentes; no filtra por responsable.
        """
        expedientes = ExpedienteCancelacion.objects.order_by('-fecha_registro', '-id_expediente')[:100]
        return Response({'expedientes': [_datos_expediente_admin(exp) for exp in expedientes]})


class ExpedienteCancelacionAdminView(APIView):
    """Consulta y resuelve un expediente bajo responsabilidad administrativa."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        """Obtiene antecedentes y proyección económica de un expediente.

        Args:
            request: Petición con permiso administrativo, sin filtro por responsable.
            id_expediente (int): Expediente consultado.

        Returns:
            Response: 200 con el detalle o 404 si no existe.
        """
        exp = ExpedienteCancelacion.objects.filter(pk=id_expediente).first()
        if not exp:
            return Response({'mensaje': 'Expediente no encontrado.'}, status=404)
        return Response({'expediente': _datos_expediente_admin(exp)})

    @method_decorator(csrf_protect)
    def patch(self, request, id_expediente):
        """Resuelve un expediente PENDIENTE y conserva su evaluación económica.

        Args:
            request: Petición administrativa con decision, fundamento de 20 a 2000
                caracteres y monto_trabajo_acreditado opcional, por defecto cero.
            id_expediente (int): Expediente que se evaluará.

        Returns:
            Response: 200 con la evaluación, 404 si falta expediente o 409 por
            resolución previa, trabajo superior al total o cálculo inválido. Usa
            el total del pago solo si está RETENIDO y VERIFICADO; en otro caso usa
            cero. Toma el porcentaje de la aceptación existente o cero si falta.
            Conserva cargo_ejecutado en cero y no cancela ni realiza reembolsos.

        Raises:
            serializers.ValidationError: Si la entrada no cumple el contrato; DRF
                devuelve 400. La autorización exige rol administrativo, no asignación
                individual como responsable de la prestación.
        """
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
                         'expediente': _datos_expediente_admin(exp)})


class EvidenciaCancelacionAdminView(APIView):
    """Descarga evidencia de cancelación solo para administración autorizada."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_expediente):
        """Descarga evidencia privada únicamente para administración autenticada.

        Args:
            request: Petición con permiso administrativo.
            id_expediente (int): Expediente que contiene la evidencia.

        Returns:
            HttpResponse | Response: Adjunto binario sin caché o 404 si falta el
            expediente, nombre o contenido. No recalcula el SHA-256 al descargar.
        """
        exp = ExpedienteCancelacion.objects.filter(pk=id_expediente).first()
        if not exp or not exp.evidencia_nombre or not exp.evidencia_contenido:
            return Response({'mensaje': 'No existe evidencia.'}, status=404)
        response = HttpResponse(bytes(exp.evidencia_contenido), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="expediente-{exp.pk}{os.path.splitext(exp.evidencia_nombre)[1]}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class EstadoCancelacionOrganizacionView(APIView):
    """Expone a la organización el estado de su expediente mediante referencia."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        """Expone el estado empresarial del último expediente sin sus antecedentes internos.

        Args:
            request: Petición de consulta sin sesión.
            referencia (str): Referencia firmada que permite resolver la prestación.

        Returns:
            Response: 200 con expediente None si no existe, estado acotado si sigue
            pendiente o decisión, importes y liquidación si está RESUELTO; 404 si la
            referencia no resuelve prestación. No expone evidencia ni fundamento libre
            y advierte que los cálculos no acreditan transferencias ejecutadas.
        """
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


def _datos_expediente_admin(exp):
    """Agrega una proyección económica administrativa cuando hay datos compatibles.

    Args:
        exp (ExpedienteCancelacion): Expediente cuya representación se ampliará.

    Returns:
        dict: Datos del expediente y, si está RESUELTO con trabajo acreditado
        y pago RETENIDO/VERIFICADO válido, desglose de comisión, neto y devolución.
        Solo proyecta cargo de cancelación para origen ORGANIZACION y decisión
        INJUSTIFICADA con aceptación anterior al pago y porcentaje coincidente.
        La comisión usa ROUND_HALF_UP a centavos; no persiste ni mueve fondos.
    """
    from decimal import Decimal, ROUND_HALF_UP

    respuesta = datos_expediente(exp)
    if exp.estado != 'RESUELTO' or exp.monto_trabajo is None:
        return respuesta
    pago = Pago.objects.filter(id_prestacion_id=exp.id_prestacion_id).first()
    if not pago or pago.estado_pago != 'RETENIDO' or pago.estado_verificacion != 'VERIFICADO':
        return respuesta
    total = Decimal(pago.monto_total)
    trabajo = Decimal(exp.monto_trabajo)
    porcentaje_comision = Decimal(pago.porcentaje_comision_aplicado)
    valores = (total, trabajo, porcentaje_comision)
    if (not all(x.is_finite() for x in valores) or total <= 0
            or trabajo < 0 or trabajo > total
            or not Decimal('0') <= porcentaje_comision <= Decimal('100')):
        return respuesta

    comision_trabajo = (trabajo * porcentaje_comision / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP)
    neto_profesional = trabajo - comision_trabajo

    aceptacion = AceptacionPoliticaCancelacion.objects.filter(
        id_prestacion_id=exp.id_prestacion_id).first()
    aceptada_antes_pago = bool(
        aceptacion and pago.fecha_pago and aceptacion.fecha_aceptacion <= pago.fecha_pago
        and exp.porcentaje_referencia is not None
        and Decimal(exp.porcentaje_referencia) == Decimal(aceptacion.porcentaje_aceptado)
    )
    cargo_cancelacion = Decimal('0')
    if (exp.origen == 'ORGANIZACION' and exp.decision == 'INJUSTIFICADA'
            and aceptada_antes_pago and exp.cargo_teorico is not None):
        cargo_cancelacion = Decimal(exp.cargo_teorico)
    if cargo_cancelacion < 0 or cargo_cancelacion > total - trabajo:
        return respuesta

    respuesta['desglose_economico'] = {
        'porcentaje_comision_servicio': str(porcentaje_comision),
        'comision_skilly_trabajo': str(comision_trabajo),
        'neto_profesional_trabajo': str(neto_profesional),
        'cargo_skilly_cancelacion': str(cargo_cancelacion),
        'total_skilly_previsto': str(comision_trabajo + cargo_cancelacion),
        'devolucion_organizacion_prevista': str(total - trabajo - cargo_cancelacion),
        'aceptacion_cancelacion_previa': aceptada_antes_pago,
    }
    return respuesta
