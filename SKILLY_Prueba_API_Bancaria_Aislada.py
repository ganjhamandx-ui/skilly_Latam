"""Ensayo API real via DRF APIRequestFactory, transaccion revertida.
Ejecutar SOLO mediante python backend/manage.py shell desde raiz SKILLY.
No registra rutas ni modifica settings permanentes.
"""
from copy import deepcopy
from types import SimpleNamespace
from django.conf import settings
from django.test import override_settings
from django.db import connections, transaction
from rest_framework.test import APIRequestFactory, force_authenticate
from backoffice.cuentas_bancarias_api import (
    CuentasBancariasView, CuentaBancariaDetalleView, HistorialCuentasBancariasView
)

ALIAS = 'bancos_api_e3'
config = deepcopy(connections.databases['default'])
config['NAME'] = 'skilly_test_concurrencia'
config['OPTIONS'] = dict(config.get('OPTIONS') or {})
config['OPTIONS']['options'] = '-c search_path=public'
connections.databases[ALIAS] = config
con = connections[ALIAS]

with con.cursor() as cur:
    cur.execute('SELECT current_database(), current_schema(), current_user')
    identidad = cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM public.cuenta_bancaria_skilly')
    inicial_cuentas = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM public.cuenta_bancaria_skilly_historial')
    inicial_historial = cur.fetchone()[0]

if identidad != ('skilly_test_concurrencia', 'public', 'skilly_app'):
    raise RuntimeError(f'ENSAYO BLOQUEADO: {identidad}')
if inicial_cuentas or inicial_historial:
    raise RuntimeError('ENSAYO BLOQUEADO: tablas no vacias; no interferir con datos previos.')
print('AISLAMIENTO CONFIRMADO:', *identidad)

factory = APIRequestFactory()
admin = SimpleNamespace(pk=901, id_usuario=901, rol='ADMIN_SKILLY', estado='ACTIVO', is_authenticated=True)
externo = SimpleNamespace(pk=902, id_usuario=902, rol='EMPRESA', estado='ACTIVO', is_authenticated=True)


def llamar(vista, metodo, ruta, datos=None, actor=admin, **kwargs):
    request = getattr(factory, metodo.lower())(ruta, datos, format='json')
    force_authenticate(request, user=actor)
    return vista.as_view()(request, **kwargs)


def exigir(resp, codigo, texto):
    if resp.status_code != codigo:
        raise AssertionError(f'{texto}: HTTP {resp.status_code} (esperado {codigo}) | {resp.data}')
    print(f'{texto}: HTTP {codigo}')


def datos(n):
    return {'titular': 'SKILLY ENSAYO SpA', 'rut_titular': '12.345.678-5',
            'banco': 'BANCO FICTICIO', 'tipo_cuenta': 'CORRIENTE',
            'numero_cuenta': f'0000012345{n}', 'correo': 'pagos@example.invalid'}

try:
    with override_settings(SKILLY_CUENTAS_BANCARIAS_HABILITADAS=True,
                           SKILLY_CUENTAS_BANCARIAS_ALIAS=ALIAS):
        with transaction.atomic(using=ALIAS):
            ruta = '/api/backoffice/configuracion/cuentas-bancarias/'
            exigir(llamar(CuentasBancariasView, 'GET', ruta, actor=externo), 403, 'NO ADMIN')
            exigir(llamar(CuentasBancariasView, 'POST', ruta, dict(datos(1), rut_titular='1-9')), 400, 'RUT INVALIDO')
            ra = llamar(CuentasBancariasView, 'POST', ruta, datos(1))
            exigir(ra, 201, 'CREAR CUENTA A')
            rb = llamar(CuentasBancariasView, 'POST', ruta, datos(2))
            exigir(rb, 201, 'CREAR CUENTA B')
            a, b = ra.data['cuenta']['id_cuenta'], rb.data['cuenta']['id_cuenta']
            exigir(llamar(CuentaBancariaDetalleView, 'PATCH', ruta+f'{a}/', {'accion':'ACTIVAR'}, id_cuenta=a), 200, 'ACTIVAR A')
            exigir(llamar(CuentaBancariaDetalleView, 'PATCH', ruta+f'{b}/', {'accion':'ACTIVAR'}, id_cuenta=b), 200, 'ACTIVAR B')
            exigir(llamar(CuentaBancariaDetalleView, 'PATCH', ruta+f'{a}/', {'accion':'PRINCIPAL'}, id_cuenta=a), 200, 'PRINCIPAL A')
            exigir(llamar(CuentaBancariaDetalleView, 'PATCH', ruta+f'{b}/', {'accion':'PRINCIPAL'}, id_cuenta=b), 200, 'CAMBIO PRINCIPAL A B')
            exigir(llamar(CuentaBancariaDetalleView, 'PATCH', ruta+f'{b}/', {'accion':'DESACTIVAR'}, id_cuenta=b), 409, 'IMPEDIR DESACTIVAR PRINCIPAL')
            respuesta = llamar(CuentasBancariasView, 'GET', ruta)
            exigir(respuesta, 200, 'LISTADO')
            cuentas = respuesta.data['cuentas']
            historial = llamar(HistorialCuentasBancariasView, 'GET', ruta+'historial/')
            exigir(historial, 200, 'HISTORIAL')
            eventos = historial.data['historial']
            assert len(cuentas) == 2 and sum(c['principal'] for c in cuentas) == 1
            assert next(c for c in cuentas if c['id_cuenta'] == b)['principal'] is True
            assert len(eventos) == 7, f'Esperados 7 eventos, obtenidos {len(eventos)}'
            salidas = [e for e in eventos if e['id_cuenta'] == a and e['accion'] == 'PRINCIPAL' and e['antes'] and e['antes']['principal'] and not e['despues']['principal']]
            assert len(salidas) == 1, 'Falta auditar deseleccion de cuenta A'
            print('ENSAYO API: 2 cuentas, 1 principal, 7 eventos, deseleccion auditada')
            transaction.set_rollback(True, using=ALIAS)
    with con.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM public.cuenta_bancaria_skilly')
        finales_cuentas = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM public.cuenta_bancaria_skilly_historial')
        finales_historial = cur.fetchone()[0]
    assert (finales_cuentas, finales_historial) == (0, 0)
    print('RESULTADO: APROBADO - API, PERMISOS, HISTORIAL Y ROLLBACK')
    print('ROLLBACK: CONFIRMADO - cuentas 0, historial 0')
    print('BASE PRINCIPAL skilly: SIN ESCRITURAS DEL ENSAYO')
finally:
    con.close()
