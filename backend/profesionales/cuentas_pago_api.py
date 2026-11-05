"""Datos bancarios profesionales: autenticación por sesión, cifrado y abonos separados."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly, EsProfesional
from backoffice.validacion_bancaria import validar_cuenta, DatosBancariosInvalidos
from pagos.models import Pago
from .models import Profesional, CuentaPagoProfesional, AbonoPagoProfesional


def cifrador():
    # Separación de propósito sobre SECRET_KEY. Un cambio de SECRET_KEY exige
    # recifrar previamente las cuentas guardadas.
    clave = hashlib.sha256(
        ('skilly:cuentas-profesionales:v1:' + settings.SECRET_KEY).encode('utf-8')
    ).digest()
    return Fernet(base64.urlsafe_b64encode(clave))


def cifrar(numero):
    return cifrador().encrypt(numero.encode('ascii')).decode('ascii')


def descifrar(numero_cifrado):
    try:
        return cifrador().decrypt(numero_cifrado.encode('ascii')).decode('ascii')
    except InvalidToken:
        raise ValueError('No se pudo acceder a los datos cifrados de esta cuenta.')


def datos_publicos(cuenta):
    if cuenta is None:
        return None
    return {
        'id_cuenta': cuenta.id_cuenta,
        'titular': cuenta.titular,
        'rut_titular': cuenta.rut_titular,
        'banco': cuenta.banco,
        'tipo_cuenta': cuenta.tipo_cuenta,
        'numero_oculto': f'•••• {cuenta.ultimos_digitos}',
        'correo': cuenta.correo,
        'fecha_actualizacion': cuenta.fecha_actualizacion,
    }


class CuentaEntradaSerializer(serializers.Serializer):
    titular = serializers.CharField(max_length=180, trim_whitespace=True)
    rut_titular = serializers.CharField(max_length=15, trim_whitespace=True)
    banco = serializers.CharField(max_length=120, trim_whitespace=True)
    tipo_cuenta = serializers.ChoiceField(choices=['CORRIENTE','VISTA','CUENTA_RUT','AHORRO'])
    numero_cuenta = serializers.RegexField(regex=r'^\d{5,32}$', max_length=32)
    correo = serializers.EmailField(max_length=254)

    def validate(self, attrs):
        try:
            return validar_cuenta(dict(attrs))
        except DatosBancariosInvalidos as exc:
            raise serializers.ValidationError({'mensaje': str(exc)})


@method_decorator(csrf_protect, name='dispatch')
class MiCuentaPagoView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def get(self, request):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje':'Registra primero tu perfil profesional.'}, status=404)
        cuenta = CuentaPagoProfesional.objects.filter(profesional=profesional).first()
        return Response({'cuenta': datos_publicos(cuenta)})

    def put(self, request):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'mensaje':'Registra primero tu perfil profesional.'}, status=404)
        entrada = CuentaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        numero = datos['numero_cuenta']
        # Un solo registro actual por profesional. Los abonos previos conservan
        # el destino utilizado al momento de su registro (snapshot cifrado).
        with transaction.atomic():
            cuenta, _ = CuentaPagoProfesional.objects.select_for_update().update_or_create(
                profesional=profesional,
                defaults={
                    'titular': datos['titular'],
                    'rut_titular': datos['rut_titular'],
                    'banco': datos['banco'],
                    'tipo_cuenta': datos['tipo_cuenta'],
                    'numero_cifrado': cifrar(numero),
                    'ultimos_digitos': numero[-4:],
                    'correo': datos['correo'],
                },
            )
        return Response({'mensaje':'Cuenta para recibir pagos guardada correctamente.',
                         'cuenta': datos_publicos(cuenta)})


@method_decorator(csrf_protect, name='dispatch')
class DestinoYAbonoAdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    @staticmethod
    def obtener_pago(id_pago):
        return Pago.objects.select_related('id_prestacion').filter(id_pago=id_pago).first()

    def get(self, request, id_pago):
        pago = self.obtener_pago(id_pago)
        if pago is None:
            return Response({'mensaje': 'Pago no encontrado.'}, status=404)
        profesional = Profesional.objects.filter(
            id_profesional=pago.id_prestacion.id_profesional_id).first()
        cuenta = CuentaPagoProfesional.objects.filter(profesional=profesional).first() if profesional else None
        abono = AbonoPagoProfesional.objects.filter(pago=pago).first()
        return Response({
            'id_pago': pago.id_pago,
            'estado_pago': pago.estado_pago,
            'monto_neto_profesional': str(pago.monto_neto_profesional),
            'moneda': pago.moneda,
            'cuenta': datos_publicos(cuenta),
            # Solo ADMIN_SKILLY obtiene el número para efectuar el abono.
            'numero_cuenta': descifrar(cuenta.numero_cifrado) if cuenta else None,
            'abono': datos_abono(abono),
            # Auditoría visible solo en esta API con permiso de Administración.
            'auditoria_abono': ({
                'responsable_id': abono.registrado_por_id,
                'observacion': abono.observacion,
            } if abono is not None else None),
        })

    def post(self, request, id_pago):
        entrada = RegistroAbonoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with transaction.atomic():
            pago = Pago.objects.select_for_update().select_related('id_prestacion').filter(id_pago=id_pago).first()
            if pago is None:
                return Response({'mensaje':'Pago no encontrado.'}, status=404)
            if pago.estado_pago != 'LIBERADO':
                return Response({'mensaje':'El pago debe estar LIBERADO.'}, status=409)
            if AbonoPagoProfesional.objects.filter(pago=pago).exists():
                return Response({'mensaje':'Ya existe un abono registrado para este pago.'}, status=409)
            profesional = Profesional.objects.filter(id_profesional=pago.id_prestacion.id_profesional_id).first()
            cuenta = CuentaPagoProfesional.objects.select_for_update().filter(profesional=profesional).first() if profesional else None
            if cuenta is None:
                return Response({'mensaje':'El profesional todavía no registró una cuenta para recibir pagos.'}, status=409)
            abono = AbonoPagoProfesional.objects.create(
                pago=pago, cuenta=cuenta,
                numero_destino_cifrado=cuenta.numero_cifrado,
                destino_resumen=f'{cuenta.banco} · {cuenta.tipo_cuenta} · •••• {cuenta.ultimos_digitos}',
                monto_neto=pago.monto_neto_profesional, moneda=pago.moneda,
                referencia_abono=entrada.validated_data['referencia_abono'],
                observacion=('SIMULACIÓN ACADÉMICA: sin transferencia bancaria real. ' + entrada.validated_data.get('observacion', '').strip()).strip(),
                registrado_por=request.user,
            )
        return Response({'mensaje':'Abono de prueba registrado en SKILLY. No se realizó una transferencia bancaria real.',
                         'abono':datos_abono(abono)}, status=201)


class RegistroAbonoSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=['REGISTRAR_ABONO'])
    referencia_abono = serializers.CharField(max_length=120, trim_whitespace=True)
    observacion = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    confirmado = serializers.BooleanField()

    def validate_confirmado(self, value):
        if value is not True:
            raise serializers.ValidationError('Debes confirmar que el abono fue realizado.')
        return value


def datos_abono(abono):
    if abono is None:
        return None
    return {
        'id_abono':abono.id_abono,
        'id_pago':abono.pago_id,
        'monto_neto':str(abono.monto_neto),
        'moneda':abono.moneda,
        'destino':abono.destino_resumen,
        'referencia_abono':abono.referencia_abono,
        'fecha_registro':abono.fecha_registro,
    }


class MisAbonosView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def get(self, request):
        profesional = Profesional.objects.filter(id_usuario=request.user).first()
        if profesional is None:
            return Response({'abonos': []})
        abonos = AbonoPagoProfesional.objects.filter(
            pago__id_prestacion__id_profesional=profesional
        ).order_by('-fecha_registro')
        return Response({'abonos':[datos_abono(a) for a in abonos]})
