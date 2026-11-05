"""API administrativa bancaria, protegida por sesion y base de datos SKILLY."""
from django.conf import settings
from django.db import connections, transaction, IntegrityError
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from .validacion_bancaria import validar_cuenta, DatosBancariosInvalidos
from .cuentas_bancarias_models import CuentaBancariaSkilly as Cuenta, HistorialCuentaBancariaSkilly as Cambio

CAMPOS = ('titular', 'rut_titular', 'banco', 'tipo_cuenta', 'numero_cuenta', 'correo')


def base_ensayo():
    """Permite solamente el esquema productivo esperado; fallo cerrado."""
    alias = 'default'
    with connections[alias].cursor() as cursor:
        cursor.execute('SELECT current_database(), current_schema(), current_user')
        base, esquema, usuario = cursor.fetchone()
        cursor.execute("SELECT to_regclass('skilly.cuenta_bancaria_skilly') IS NOT NULL AND to_regclass('skilly.cuenta_bancaria_skilly_historial') IS NOT NULL")
        tablas = cursor.fetchone()[0]
    if (base, esquema, usuario) != ('skilly', 'skilly', 'skilly_app') or not tablas:
        return None
    return alias


def serializar(c):
    return {'id_cuenta': c.id_cuenta, **{x: getattr(c, x) for x in CAMPOS},
            'activa': c.activa, 'principal': c.principal,
            'fecha_modificacion': c.fecha_modificacion.isoformat()}


def evento(alias, c, accion, antes, usuario):
    Cambio.objects.using(alias).create(
        id_cuenta=c, accion=accion, datos_anteriores=antes,
        datos_nuevos=serializar(c), id_usuario_skilly=usuario,
        fecha_cambio=timezone.now(),
    )


def usuario_id(request):
    return request.user.pk


class CuentasBancariasView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        alias = base_ensayo()
        if alias is None:
            return Response({'mensaje': 'Modulo bancario no disponible: compruebe conexion y esquema autorizados.'}, status=503)
        return Response({'cuentas': [serializar(c) for c in Cuenta.objects.using(alias).order_by('-principal', '-activa', 'id_cuenta')]})

    def post(self, request):
        alias = base_ensayo()
        if alias is None:
            return Response({'mensaje': 'Modulo bancario no disponible: compruebe conexion y esquema autorizados.'}, status=503)
        try:
            datos = validar_cuenta(request.data)
        except DatosBancariosInvalidos as exc:
            return Response({'mensaje': str(exc)}, status=400)
        if request.data.get('principal') is True or request.data.get('activa') is True:
            return Response({'mensaje': 'Crear inactiva; activar y elegir principal por separado.'}, status=400)
        try:
            with transaction.atomic(using=alias):
                ahora = timezone.now()
                u = usuario_id(request)
                c = Cuenta.objects.using(alias).create(
                    **datos, activa=False, principal=False,
                    fecha_creacion=ahora, fecha_modificacion=ahora,
                    id_usuario_creacion=u, id_usuario_modificacion=u,
                )
                evento(alias, c, 'CREAR', None, u)
        except IntegrityError:
            return Response({'mensaje': 'Cuenta duplicada o datos inconsistentes.'}, status=409)
        return Response({'cuenta': serializar(c)}, status=201)


class CuentaBancariaDetalleView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def patch(self, request, id_cuenta):
        alias = base_ensayo()
        if alias is None:
            return Response({'mensaje': 'Modulo bancario no disponible: compruebe conexion y esquema autorizados.'}, status=503)
        accion = request.data.get('accion')
        if accion not in ('MODIFICAR', 'ACTIVAR', 'DESACTIVAR', 'PRINCIPAL'):
            return Response({'mensaje': 'Accion no admitida.'}, status=400)
        try:
            with transaction.atomic(using=alias):
                # El bloqueo se realiza sobre la tabla aislada, no sobre tablas de produccion.
                with connections[alias].cursor() as cursor:
                    cursor.execute('LOCK TABLE skilly.cuenta_bancaria_skilly IN SHARE ROW EXCLUSIVE MODE')
                c = Cuenta.objects.using(alias).select_for_update().filter(pk=id_cuenta).first()
                if c is None:
                    return Response({'mensaje': 'Cuenta inexistente.'}, status=404)
                antes = serializar(c)
                u = usuario_id(request)
                if accion == 'MODIFICAR':
                    if c.activa or c.principal:
                        return Response({'mensaje': 'Desactive antes de modificar datos bancarios.'}, status=409)
                    datos = validar_cuenta(request.data)
                    for campo, valor in datos.items():
                        setattr(c, campo, valor)
                elif accion == 'ACTIVAR':
                    c.activa = True
                elif accion == 'DESACTIVAR':
                    if c.principal:
                        return Response({'mensaje': 'Seleccione otra principal antes de desactivar.'}, status=409)
                    c.activa = False
                elif accion == 'PRINCIPAL':
                    if not c.activa:
                        return Response({'mensaje': 'Active la cuenta antes de elegirla principal.'}, status=409)
                    anteriores = list(Cuenta.objects.using(alias).filter(principal=True).exclude(pk=c.pk))
                    for anterior in anteriores:
                        snapshot = serializar(anterior)
                        anterior.principal = False
                        anterior.fecha_modificacion = timezone.now()
                        anterior.id_usuario_modificacion = u
                        anterior.save(using=alias)
                        evento(alias, anterior, 'PRINCIPAL', snapshot, u)
                    c.principal = True
                c.fecha_modificacion = timezone.now()
                c.id_usuario_modificacion = u
                c.save(using=alias)
                evento(alias, c, accion, antes, u)
                resultado = serializar(c)
        except DatosBancariosInvalidos as exc:
            return Response({'mensaje': str(exc)}, status=400)
        except IntegrityError:
            return Response({'mensaje': 'Conflicto de integridad bancaria.'}, status=409)
        return Response({'cuenta': resultado})


class HistorialCuentasBancariasView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        alias = base_ensayo()
        if alias is None:
            return Response({'mensaje': 'Modulo bancario no disponible: compruebe conexion y esquema autorizados.'}, status=503)
        filas = Cambio.objects.using(alias).order_by('-fecha_cambio', '-id_cambio')[:100]
        return Response({'historial': [
            {'id_cambio': h.id_cambio, 'id_cuenta': h.id_cuenta_id,
             'accion': h.accion, 'usuario_id': h.id_usuario_skilly,
             'fecha': h.fecha_cambio, 'antes': h.datos_anteriores,
             'despues': h.datos_nuevos}
            for h in filas
        ]})
