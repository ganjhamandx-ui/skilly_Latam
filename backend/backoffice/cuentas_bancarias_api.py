"""API administrativa bancaria, protegida por sesion y base de datos SKILLY."""
from django.db import connections, transaction, IntegrityError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from config.identidad_bancaria import identidad_bancaria_autorizada
from .validacion_bancaria import validar_cuenta, DatosBancariosInvalidos
from .cuentas_bancarias_models import CuentaBancariaSkilly as Cuenta, HistorialCuentaBancariaSkilly as Cambio

CAMPOS = ('titular', 'rut_titular', 'banco', 'tipo_cuenta', 'numero_cuenta', 'correo')


def base_ensayo():
    """Comprueba identidad de la conexión principal y existencia de tablas bancarias.

    Returns:
        str | None: Alias default si coinciden base, esquema y rol autorizados
        y existen ambas tablas; None si las comprobaciones no se cumplen.

    Los errores de conexión o de consulta se propagan; esta función no inicia
    una base de ensayo ni modifica el esquema.
    """
    alias = 'default'
    conexion = connections[alias]
    with conexion.cursor() as cursor:
        cursor.execute('SELECT current_database(), current_schema(), current_user')
        if not identidad_bancaria_autorizada(conexion, cursor.fetchone()):
            return None
        cursor.execute("SELECT to_regclass('skilly.cuenta_bancaria_skilly') IS NOT NULL AND to_regclass('skilly.cuenta_bancaria_skilly_historial') IS NOT NULL")
        tablas = cursor.fetchone()[0]
    if not tablas:
        return None
    return alias


def serializar(c):
    """Representa una cuenta completa para administración y su historial privado.

    Args:
        c (CuentaBancariaSkilly): Cuenta que se representará.

    Returns:
        dict: Datos bancarios, incluido el número sin enmascarar, indicadores
        activa/principal y fecha de modificación en formato ISO.
    """

    return {'id_cuenta': c.id_cuenta, **{x: getattr(c, x) for x in CAMPOS},
            'activa': c.activa, 'principal': c.principal,
            'fecha_modificacion': c.fecha_modificacion.isoformat()}


def evento(alias, c, accion, antes, usuario):
    """Inserta una instantánea del cambio bancario en la base indicada.

    Args:
        alias (str): Conexión usada también para modificar la cuenta.
        c (CuentaBancariaSkilly): Cuenta con los valores posteriores al cambio.
        accion (str): Acción administrativa realizada.
        antes (dict | None): Valores anteriores; None durante la creación.
        usuario (int): Identificador del administrador responsable.

    Returns:
        None: El historial se persiste mediante el ORM. El llamador mantiene
        la transacción que engloba la cuenta y su evento.
    """

    Cambio.objects.using(alias).create(
        id_cuenta=c, accion=accion, datos_anteriores=antes,
        datos_nuevos=serializar(c), id_usuario_skilly=usuario,
        fecha_cambio=timezone.now(),
    )


def usuario_id(request):
    """Devuelve la clave primaria del usuario autenticado de request."""

    return request.user.pk


@method_decorator(csrf_protect, name='dispatch')
class CuentasBancariasView(APIView):
    """Lista y crea cuentas receptoras bajo autenticación administrativa y CSRF."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        """Lista las cuentas receptoras completas para administración.

        Args:
            request: Petición administrativa autenticada.

        Returns:
            Response: 200 con cuentas ordenadas por principal, activa e identificador,
            o 503 cuando la identidad o las tablas requeridas no están habilitadas.
        """
        alias = base_ensayo()
        if alias is None:
            return Response({'mensaje': 'Modulo bancario no disponible: compruebe conexion y esquema autorizados.'}, status=503)
        return Response({'cuentas': [serializar(c) for c in Cuenta.objects.using(alias).order_by('-principal', '-activa', 'id_cuenta')]})

    def post(self, request):
        """Crea una cuenta inactiva y no principal junto con su evento histórico.

        Args:
            request: Petición con los campos bancarios exigidos por validar_cuenta.

        Returns:
            Response: 201 con la cuenta, 400 por datos inválidos o intento de
            activación en la creación, 409 por conflicto de integridad o 503 si
            la instalación no está habilitada. Activar y elegir principal requieren
            operaciones posteriores.
        """
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


@method_decorator(csrf_protect, name='dispatch')
class CuentaBancariaDetalleView(APIView):
    """Modifica una cuenta y protege la unicidad de la principal dentro de una transacción."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def patch(self, request, id_cuenta):
        """Modifica datos o estado de una cuenta bajo bloqueo de la tabla bancaria.

        Args:
            request: Petición con accion MODIFICAR, ACTIVAR, DESACTIVAR o PRINCIPAL;
                MODIFICAR requiere los campos bancarios completos.
            id_cuenta (int): Cuenta destinataria de la acción.

        Returns:
            Response: 200 con la cuenta, 400 por entrada inválida, 404 si falta,
            409 por estado incompatible o integridad y 503 si no está habilitada.
            Solo modifica datos de cuentas inactivas y no principales; elegir una
            principal exige que esté activa y retira esa condición de las anteriores,
            conservando el historial de cada cambio.
        """
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
    """Expone el historial inmutable de cambios bancarios al personal autorizado."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        """Consulta los cien cambios bancarios más recientes.

        Args:
            request: Petición administrativa autenticada.

        Returns:
            Response: 200 con valores anteriores y posteriores, incluidos los
            números completos de cuenta, o 503 si la instalación no está habilitada.
        """
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
