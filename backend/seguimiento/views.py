
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from .serializers import RegistrarReclamoEmpresaSerializer
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly, EsProfesional
from backoffice.services import registrar_evento_trazabilidad
from coordinacion.models import PrestacionServicio
from pagos.models import Pago, ReversaPago
from profesionales.models import Profesional
from solicitudes.referencias import leer_referencia_seguimiento
from .models import AvanceServicio, Entrega, ObservacionEntrega, ReclamoPrestacion, ResolucionReclamo
from .politicas_reportes_profesional import ESTADO_AVISO
from .serializers import AvanceServicioSerializer, EntregaSerializer, ObservacionEntregaSerializer, ReclamoPrestacionSerializer, RegistrarAvanceServicioSerializer, RegistrarEntregaSerializer, RevisarEntregaEmpresaSerializer, ResolverReclamoSerializer, ResolucionReclamoSerializer


class SeguimientoPrestacionProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def get(self, request, id_prestacion):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje': 'El perfil profesional todavía no se encuentra registrado.'}, status=status.HTTP_404_NOT_FOUND)
        prestacion = PrestacionServicio.objects.select_related('id_solicitud', 'id_profesional').filter(id_prestacion=id_prestacion, id_profesional=profesional).first()
        if prestacion is None:
            return Response({'mensaje': 'La prestación solicitada no existe o no pertenece al profesional.'}, status=status.HTTP_404_NOT_FOUND)
        avances = AvanceServicio.objects.filter(id_prestacion=prestacion).order_by('fecha_registro', 'id_avance')
        serializer = AvanceServicioSerializer(avances, many=True)
        return Response({'prestacion': {'id_prestacion': prestacion.id_prestacion, 'id_solicitud': prestacion.id_solicitud_id, 'estado': prestacion.estado, 'fecha_inicio': prestacion.fecha_inicio, 'fecha_fin': prestacion.fecha_fin, 'fecha_cierre': prestacion.fecha_cierre}, 'avances': serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, id_prestacion):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje': 'El perfil profesional todavía no se encuentra registrado.'}, status=status.HTTP_404_NOT_FOUND)
        prestacion = PrestacionServicio.objects.filter(id_prestacion=id_prestacion, id_profesional=profesional).first()
        if prestacion is None:
            return Response({'mensaje': 'La prestación solicitada no existe o no pertenece al profesional.'}, status=status.HTTP_404_NOT_FOUND)
        if prestacion.estado in ['FINALIZADA', 'CANCELADA', 'POSTERGADA']:
            return Response({'mensaje': 'La prestación se encuentra cerrada para registrar nuevos avances.'}, status=status.HTTP_409_CONFLICT)
        entrada_serializer = RegistrarAvanceServicioSerializer(data=request.data)
        if not entrada_serializer.is_valid():
            return Response(entrada_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            prestacion_actual = PrestacionServicio.objects.select_for_update().filter(id_prestacion=prestacion.id_prestacion, id_profesional=profesional).first()
            if prestacion_actual is None:
                return Response({'mensaje': 'La prestación solicitada no existe.'}, status=status.HTTP_404_NOT_FOUND)
            if prestacion_actual.estado in ['FINALIZADA', 'CANCELADA', 'POSTERGADA']:
                return Response({'mensaje': 'La prestación no admite nuevos registros en su estado actual.'}, status=status.HTTP_409_CONFLICT)
            prestacion = prestacion_actual
            avance = AvanceServicio.objects.create(id_prestacion=prestacion, estado=entrada_serializer.validated_data['estado'], detalle=entrada_serializer.validated_data.get('detalle'), fecha_registro=timezone.now())
            registrar_evento_trazabilidad(usuario=request.user, entidad_tipo='avance_servicio', entidad_id=avance.id_avance, accion='REGISTRAR_AVANCE', detalle_resumido=f'Avance registrado para prestación {prestacion.id_prestacion}. Estado informado: {avance.estado}.'[:255])
        serializer = AvanceServicioSerializer(avance)
        return Response({'mensaje': 'Avance registrado correctamente.', 'avance': serializer.data}, status=status.HTTP_201_CREATED)

class SeguimientoPrestacionEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        datos_referencia = leer_referencia_seguimiento(referencia)
        if datos_referencia is None:
            return Response({'mensaje': 'La referencia de seguimiento no es valida.'}, status=status.HTTP_400_BAD_REQUEST)
        prestacion = PrestacionServicio.objects.select_related('id_solicitud', 'id_profesional').filter(id_solicitud_id=datos_referencia['id_solicitud'], id_solicitud__id_contacto_id=datos_referencia['id_contacto']).order_by('-id_prestacion').first()
        if prestacion is None:
            return Response({'mensaje': 'La prestacion solicitada no existe o no corresponde a esta empresa.'}, status=status.HTTP_404_NOT_FOUND)
        # Los avisos del profesional quedan disponibles solo en sus sesiones y
        # en administración; no se publican sin revisión al contacto empresarial.
        avances = (AvanceServicio.objects.filter(id_prestacion=prestacion)
                   .exclude(estado=ESTADO_AVISO)
                   .order_by('fecha_registro', 'id_avance'))
        serializer = AvanceServicioSerializer(avances, many=True)
        entregas = Entrega.objects.filter(id_prestacion=prestacion).order_by('fecha_entrega', 'id_entrega')
        entregas_serializer = EntregaSerializer(entregas, many=True)
        return Response({
            'prestacion': {
                'id_prestacion': prestacion.id_prestacion,
                'id_solicitud': prestacion.id_solicitud_id,
                'estado': prestacion.estado,
                'condiciones_comunicadas': str(
                    prestacion.condiciones_comunicadas or ''
                ).strip(),
                'fecha_inicio': prestacion.fecha_inicio,
                'fecha_fin': prestacion.fecha_fin,
                'fecha_cierre': prestacion.fecha_cierre
            },
            'avances': serializer.data,
            'entregas': entregas_serializer.data
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name='dispatch')
class SeguimientoPrestacionAdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    @staticmethod
    def evaluar_cierre(prestacion):
        """Valida el cierre sin modificar dinero ni estados de pago."""
        entrega = (Entrega.objects.filter(id_prestacion=prestacion)
                   .order_by('-version', '-fecha_entrega', '-id_entrega').first())
        pago = Pago.objects.filter(id_prestacion=prestacion).first()
        razones = []
        if prestacion.estado != 'CONTRATADA':
            razones.append('La prestación debe estar CONTRATADA.')
        if entrega is None or entrega.estado != 'ACEPTADA':
            razones.append('La última entrega debe estar aceptada por la empresa.')
        if pago is None or pago.estado_pago not in ('RETENIDO', 'LIBERADO') or pago.estado_verificacion != 'VERIFICADO':
            razones.append('Se requiere un pago verificado en estado RETENIDO o LIBERADO.')
        if ReclamoPrestacion.objects.filter(id_prestacion=prestacion, fecha_cierre__isnull=True).exists():
            razones.append('Existe un reclamo pendiente de resolución.')
        if pago is not None and ReversaPago.objects.filter(id_pago=pago, estado_reversa='SOLICITADA').exists():
            razones.append('Existe una reversa económica pendiente.')
        if (ResolucionReclamo.objects.filter(id_reclamo__id_prestacion=prestacion)
                .exclude(efecto_economico='LIBERACION').exists()):
            razones.append('Existe una resolución económica que requiere revisión antes del cierre.')
        return {
            'habilitado': not razones,
            'razones': razones,
            'ultima_entrega': {
                'id_entrega': entrega.id_entrega,
                'version': entrega.version,
                'estado': entrega.estado,
            } if entrega else None,
            'estado_pago': pago.estado_pago if pago else None,
        }

    @staticmethod
    def datos_prestacion(prestacion):
        return {
            'id_prestacion': prestacion.id_prestacion,
            'id_solicitud': prestacion.id_solicitud_id,
            'id_profesional': prestacion.id_profesional_id,
            'estado': prestacion.estado,
            'fecha_inicio': prestacion.fecha_inicio,
            'fecha_fin': prestacion.fecha_fin,
            'fecha_cierre': prestacion.fecha_cierre,
        }

    def get(self, request, id_prestacion):
        prestacion = PrestacionServicio.objects.select_related('id_solicitud', 'id_profesional').filter(id_prestacion=id_prestacion).first()
        if prestacion is None:
            return Response({'mensaje': 'La prestación solicitada no existe.'}, status=status.HTTP_404_NOT_FOUND)
        avances = AvanceServicio.objects.filter(id_prestacion=prestacion).order_by('fecha_registro', 'id_avance')
        return Response({
            'prestacion': self.datos_prestacion(prestacion),
            'avances': AvanceServicioSerializer(avances, many=True).data,
            'cierre': self.evaluar_cierre(prestacion),
        }, status=status.HTTP_200_OK)

    def post(self, request, id_prestacion):
        if request.data.get('accion') != 'FINALIZAR_PRESTACION':
            return Response({'mensaje': 'Acción de cierre inválida.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            prestacion = (PrestacionServicio.objects.select_for_update()
                          .filter(id_prestacion=id_prestacion).first())
            if prestacion is None:
                return Response({'mensaje': 'La prestación solicitada no existe.'}, status=status.HTTP_404_NOT_FOUND)
            if prestacion.estado == 'FINALIZADA':
                return Response({'mensaje': 'La prestación ya está finalizada.',
                                 'prestacion': self.datos_prestacion(prestacion)}, status=status.HTTP_200_OK)
            cierre = self.evaluar_cierre(prestacion)
            if not cierre['habilitado']:
                return Response({'mensaje': 'No se cumplen las condiciones de cierre.',
                                 'cierre': cierre}, status=status.HTTP_409_CONFLICT)
            ahora = timezone.now()
            prestacion.estado = 'FINALIZADA'
            prestacion.fecha_cierre = ahora
            prestacion.save(update_fields=['estado', 'fecha_cierre'])
            registrar_evento_trazabilidad(
                usuario=request.user, entidad_tipo='prestacion_servicio',
                entidad_id=prestacion.id_prestacion, accion='FINALIZAR_PRESTACION',
                detalle_resumido=f'Prestación {prestacion.id_prestacion} finalizada administrativamente. Pago sin modificación.'[:255],
            )
        return Response({'mensaje': 'Prestación finalizada correctamente. El pago no se ha liberado.',
                         'prestacion': self.datos_prestacion(prestacion)}, status=status.HTTP_200_OK)


class EntregasPrestacionProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def get(self, request, id_prestacion):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje': 'El perfil profesional todavía no se encuentra registrado.'}, status=status.HTTP_404_NOT_FOUND)
        prestacion = PrestacionServicio.objects.select_related('id_solicitud', 'id_profesional').filter(id_prestacion=id_prestacion, id_profesional=profesional).first()
        if prestacion is None:
            return Response({'mensaje': 'La prestación solicitada no existe o no pertenece al profesional.'}, status=status.HTTP_404_NOT_FOUND)
        entregas = Entrega.objects.filter(id_prestacion=prestacion).order_by('version', 'fecha_entrega', 'id_entrega')
        observaciones = ObservacionEntrega.objects.filter(id_entrega__id_prestacion=prestacion).order_by('fecha', 'id_observacion')
        entregas_serializer = EntregaSerializer(entregas, many=True)
        observaciones_data = []
        for observacion in observaciones:
            observaciones_data.append({'id_observacion': observacion.id_observacion, 'id_entrega': observacion.id_entrega_id, 'fecha': observacion.fecha, 'detalle': observacion.detalle, 'estado': observacion.estado})
        return Response({'prestacion': {'id_prestacion': prestacion.id_prestacion, 'id_solicitud': prestacion.id_solicitud_id, 'estado': prestacion.estado}, 'entregas': entregas_serializer.data, 'observaciones': observaciones_data}, status=status.HTTP_200_OK)


    def post(self, request, id_prestacion):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje': 'El perfil profesional todavía no se encuentra registrado.'}, status=status.HTTP_404_NOT_FOUND)
        prestacion = PrestacionServicio.objects.filter(id_prestacion=id_prestacion, id_profesional=profesional).first()
        if prestacion is None:
            return Response({'mensaje': 'La prestación solicitada no existe o no pertenece al profesional.'}, status=status.HTTP_404_NOT_FOUND)
        if prestacion.estado in ['FINALIZADA', 'CANCELADA', 'POSTERGADA']:
            return Response({'mensaje': 'La prestación se encuentra cerrada para registrar nuevas entregas.'}, status=status.HTTP_409_CONFLICT)
        entrada_serializer = RegistrarEntregaSerializer(data=request.data)
        if not entrada_serializer.is_valid():
            return Response(entrada_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        referencia_entrega = entrada_serializer.validated_data.get('referencia_entrega')
        if referencia_entrega == '':
            referencia_entrega = None
        with transaction.atomic():
            prestacion_actual = PrestacionServicio.objects.select_for_update().filter(id_prestacion=prestacion.id_prestacion, id_profesional=profesional).first()
            if prestacion_actual is None:
                return Response({'mensaje': 'La prestación solicitada no existe.'}, status=status.HTTP_404_NOT_FOUND)
            if prestacion_actual.estado in ['FINALIZADA', 'CANCELADA', 'POSTERGADA']:
                return Response({'mensaje': 'La prestación no admite nuevos registros en su estado actual.'}, status=status.HTTP_409_CONFLICT)
            prestacion = prestacion_actual
            ultima_version = Entrega.objects.filter(id_prestacion=prestacion).aggregate(ultima=Max('version')).get('ultima')
            if ultima_version is None:
                nueva_version = 1
            else:
                nueva_version = ultima_version + 1
            entrega = Entrega.objects.create(id_prestacion=prestacion, version=nueva_version, descripcion=entrada_serializer.validated_data['descripcion'], referencia_entrega=referencia_entrega, fecha_entrega=timezone.now(), estado='ENTREGADA')
            registrar_evento_trazabilidad(usuario=request.user, entidad_tipo='entrega', entidad_id=entrega.id_entrega, accion='REGISTRAR_ENTREGA', detalle_resumido=f'Entrega versión {entrega.version} registrada para prestación {prestacion.id_prestacion}.'[:255])
        serializer = EntregaSerializer(entrega)
        return Response({'mensaje': 'Entrega registrada correctamente.', 'entrega': serializer.data}, status=status.HTTP_201_CREATED)

@method_decorator(csrf_protect, name='dispatch')
class RevisionEntregaEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia, id_entrega):
        datos_referencia = leer_referencia_seguimiento(referencia)
        if datos_referencia is None:
            return Response({'mensaje': 'La referencia de seguimiento no es valida.'}, status=status.HTTP_400_BAD_REQUEST)
        entrega = Entrega.objects.select_related('id_prestacion', 'id_prestacion__id_solicitud').filter(id_entrega=id_entrega, id_prestacion__id_solicitud_id=datos_referencia['id_solicitud'], id_prestacion__id_solicitud__id_contacto_id=datos_referencia['id_contacto']).first()
        if entrega is None:
            return Response({'mensaje': 'La entrega solicitada no existe o no corresponde a esta empresa.'}, status=status.HTTP_404_NOT_FOUND)
        observaciones = ObservacionEntrega.objects.select_related('id_contacto').filter(id_entrega=entrega).order_by('fecha', 'id_observacion')
        return Response({'entrega': EntregaSerializer(entrega).data, 'observaciones': ObservacionEntregaSerializer(observaciones, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request, referencia, id_entrega):
        datos_referencia = leer_referencia_seguimiento(referencia)
        if datos_referencia is None:
            return Response({'mensaje': 'La referencia de seguimiento no es valida.'}, status=status.HTTP_400_BAD_REQUEST)
        entrada_serializer = RevisarEntregaEmpresaSerializer(data=request.data)
        if not entrada_serializer.is_valid():
            return Response(entrada_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        accion = entrada_serializer.validated_data['accion']
        detalle = entrada_serializer.validated_data.get('detalle')
        with transaction.atomic():
            entrega = Entrega.objects.select_for_update().select_related('id_prestacion', 'id_prestacion__id_solicitud').filter(id_entrega=id_entrega, id_prestacion__id_solicitud_id=datos_referencia['id_solicitud'], id_prestacion__id_solicitud__id_contacto_id=datos_referencia['id_contacto']).first()
            if entrega is None:
                return Response({'mensaje': 'La entrega solicitada no existe o no corresponde a esta empresa.'}, status=status.HTTP_404_NOT_FOUND)
            if accion == 'ACEPTAR':
                if entrega.estado == 'ACEPTADA':
                    return Response({'mensaje': 'La entrega ya se encontraba aceptada.', 'entrega': EntregaSerializer(entrega).data}, status=status.HTTP_200_OK)
                if entrega.estado != 'ENTREGADA':
                    return Response({'mensaje': 'La entrega no se encuentra en un estado valido para ser aceptada.'}, status=status.HTTP_409_CONFLICT)
                entrega.estado = 'ACEPTADA'
                entrega.save(update_fields=['estado'])
                registrar_evento_trazabilidad(usuario=None, entidad_tipo='entrega', entidad_id=entrega.id_entrega, accion='ACEPTAR_ENTREGA_EMPRESA', detalle_resumido=f"Entrega {entrega.id_entrega} aceptada por el contacto empresarial {datos_referencia['id_contacto']}."[:255])
                return Response({'mensaje': 'Entrega aceptada correctamente.', 'entrega': EntregaSerializer(entrega).data}, status=status.HTTP_200_OK)
            if entrega.estado == 'CON_OBSERVACIONES':
                observaciones = ObservacionEntrega.objects.select_related('id_contacto').filter(id_entrega=entrega).order_by('fecha', 'id_observacion')
                return Response({'mensaje': 'La entrega ya posee una revision con observaciones.', 'entrega': EntregaSerializer(entrega).data, 'observaciones': ObservacionEntregaSerializer(observaciones, many=True).data}, status=status.HTTP_200_OK)
            if entrega.estado != 'ENTREGADA':
                return Response({'mensaje': 'La entrega no se encuentra en un estado valido para registrar observaciones.'}, status=status.HTTP_409_CONFLICT)
            observacion = ObservacionEntrega.objects.create(id_entrega=entrega, id_contacto_id=datos_referencia['id_contacto'], fecha=timezone.now(), detalle=detalle, estado='REGISTRADA')
            entrega.estado = 'CON_OBSERVACIONES'
            entrega.save(update_fields=['estado'])
            registrar_evento_trazabilidad(usuario=None, entidad_tipo='entrega', entidad_id=entrega.id_entrega, accion='REGISTRAR_OBSERVACION_ENTREGA', detalle_resumido=f"Entrega {entrega.id_entrega} observada por el contacto empresarial {datos_referencia['id_contacto']}."[:255])
        return Response({'mensaje': 'Observacion registrada correctamente.', 'entrega': EntregaSerializer(entrega).data, 'observacion': ObservacionEntregaSerializer(observacion).data}, status=status.HTTP_201_CREATED)

class GestionReclamoAdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_reclamo):
        reclamo = ReclamoPrestacion.objects.select_related('id_prestacion', 'id_contacto').filter(id_reclamo=id_reclamo).first()
        if reclamo is None:
            return Response({'mensaje': 'El reclamo solicitado no existe.'}, status=status.HTTP_404_NOT_FOUND)
        resolucion = ResolucionReclamo.objects.select_related('id_usuario_skilly').filter(id_reclamo=reclamo).first()
        pago = Pago.objects.filter(id_prestacion=reclamo.id_prestacion).first()
        pago_data = None
        if pago is not None:
            pago_data = {'id_pago': pago.id_pago, 'monto_total': pago.monto_total, 'moneda': pago.moneda, 'estado_pago': pago.estado_pago, 'estado_verificacion': pago.estado_verificacion, 'fecha_pago': pago.fecha_pago, 'fecha_retencion': pago.fecha_retencion, 'fecha_liberacion': pago.fecha_liberacion}
        resolucion_data = None
        if resolucion is not None:
            resolucion_data = ResolucionReclamoSerializer(resolucion).data
        return Response({'reclamo': ReclamoPrestacionSerializer(reclamo).data, 'prestacion': {'id_prestacion': reclamo.id_prestacion_id, 'estado': reclamo.id_prestacion.estado, 'id_profesional': reclamo.id_prestacion.id_profesional_id}, 'pago': pago_data, 'resolucion': resolucion_data}, status=status.HTTP_200_OK)

    def post(self, request, id_reclamo):
        entrada_serializer = ResolverReclamoSerializer(data=request.data)
        if not entrada_serializer.is_valid():
            return Response(entrada_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            reclamo = ReclamoPrestacion.objects.select_for_update().filter(id_reclamo=id_reclamo).first()
            if reclamo is None:
                return Response({'mensaje': 'El reclamo solicitado no existe.'}, status=status.HTTP_404_NOT_FOUND)
            resolucion_existente = ResolucionReclamo.objects.filter(id_reclamo=reclamo).exists()
            if resolucion_existente or reclamo.fecha_cierre is not None:
                return Response({'mensaje': 'El reclamo ya se encuentra resuelto o cerrado.'}, status=status.HTTP_409_CONFLICT)
            ahora = timezone.now()
            resolucion = ResolucionReclamo.objects.create(id_reclamo=reclamo, id_usuario_skilly=request.user, decision=entrada_serializer.validated_data['decision'], efecto_economico=entrada_serializer.validated_data['efecto_economico'], monto_afectado=entrada_serializer.validated_data.get('monto_afectado'), observacion=entrada_serializer.validated_data.get('observacion'), fecha_resolucion=ahora)
            reclamo.estado = 'RESUELTO'
            reclamo.fecha_cierre = ahora
            reclamo.save(update_fields=['estado', 'fecha_cierre'])
            registrar_evento_trazabilidad(usuario=request.user, entidad_tipo='resolucion_reclamo', entidad_id=resolucion.id_resolucion, accion='RESOLVER_RECLAMO', detalle_resumido=f'Reclamo {reclamo.id_reclamo} resuelto. Prestación {reclamo.id_prestacion_id}. Efecto económico: {resolucion.efecto_economico}.'[:255])
        resolucion = ResolucionReclamo.objects.select_related('id_usuario_skilly').get(id_resolucion=resolucion.id_resolucion)
        return Response({'mensaje': 'Resolución del reclamo registrada correctamente.', 'reclamo': ReclamoPrestacionSerializer(reclamo).data, 'resolucion': ResolucionReclamoSerializer(resolucion).data, 'nota': 'El efecto económico quedó registrado. La liberación, retención o reversa del pago se gestiona en su flujo económico correspondiente.'}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name='dispatch')
class RegistrarReclamoEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, referencia):
        datos_referencia = leer_referencia_seguimiento(referencia)
        if datos_referencia is None:
            return Response({'mensaje': 'La referencia de seguimiento no es valida.'}, status=status.HTTP_400_BAD_REQUEST)
        entrada_serializer = RegistrarReclamoEmpresaSerializer(data=request.data)
        if not entrada_serializer.is_valid():
            return Response(entrada_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        id_solicitud = datos_referencia['id_solicitud']
        id_contacto = datos_referencia['id_contacto']
        with transaction.atomic():
            prestacion = PrestacionServicio.objects.select_for_update().filter(id_solicitud_id=id_solicitud, id_solicitud__id_contacto_id=id_contacto).order_by('-id_prestacion').first()
            if prestacion is None:
                return Response({'mensaje': 'La prestacion no existe o no corresponde a esta empresa.'}, status=status.HTTP_404_NOT_FOUND)
            reclamo_pendiente = ReclamoPrestacion.objects.filter(id_prestacion=prestacion, fecha_cierre__isnull=True).exists()
            if reclamo_pendiente:
                return Response({'mensaje': 'La prestacion ya posee un reclamo pendiente de resolucion.'}, status=status.HTTP_409_CONFLICT)
            reclamo = ReclamoPrestacion.objects.create(id_prestacion=prestacion, id_contacto_id=id_contacto, motivo=entrada_serializer.validated_data['motivo'], descripcion=entrada_serializer.validated_data['descripcion'], estado='ABIERTO', fecha_registro=timezone.now(), fecha_cierre=None)
            registrar_evento_trazabilidad(usuario=None, entidad_tipo='reclamo_prestacion', entidad_id=reclamo.id_reclamo, accion='REGISTRAR_RECLAMO', detalle_resumido=f'Reclamo {reclamo.id_reclamo} registrado por contacto empresarial {id_contacto}. Prestacion {prestacion.id_prestacion}.'[:255])
        salida_serializer = ReclamoPrestacionSerializer(reclamo)
        return Response({'mensaje': 'Reclamo registrado correctamente. Queda pendiente de gestion por Skilly.', 'reclamo': salida_serializer.data, 'nota': 'El registro del reclamo no ejecuta una devolucion ni una sancion automatica.'}, status=status.HTTP_201_CREATED)
