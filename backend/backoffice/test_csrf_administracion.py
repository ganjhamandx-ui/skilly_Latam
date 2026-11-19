"""Regresiones CSRF sobre rutas reales, sin ejecutar operaciones ni acceder a BD."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from rest_framework.response import Response

from acceso.authentication import SesionSkillyAuthentication
from .configuracion_cargo_cancelacion_e3 import ConfiguracionCargoCancelacionView
from .cuentas_bancarias_api import CuentasBancariasView, CuentaBancariaDetalleView


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class CsrfAdministracionTests(SimpleTestCase):
    """Comprueba que las escrituras administrativas con sesión exijan CSRF válido."""

    operaciones = (
        ('post', '/api/backoffice/configuracion/cuentas-bancarias/', CuentasBancariasView),
        ('patch', '/api/backoffice/configuracion/cuentas-bancarias/1/', CuentaBancariaDetalleView),
        ('patch', '/api/backoffice/configuracion/cancelaciones/', ConfiguracionCargoCancelacionView),
    )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.administrador = SimpleNamespace(pk=1, estado='ACTIVO', rol='ADMIN_SKILLY')

    def token_csrf(self):
        respuesta = self.client.get('/api/acceso/csrf/')
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()['csrfToken']

    def comprobar_operaciones(self, usuario, estado, **cabeceras):
        autenticacion = (usuario, None) if usuario is not None else None
        for metodo, ruta, vista in self.operaciones:
            with self.subTest(metodo=metodo, ruta=ruta), patch.object(
                SesionSkillyAuthentication, 'authenticate', return_value=autenticacion,
            ), patch.object(
                vista, metodo, return_value=Response({'diagnostico': 'sin-operaciones'}),
            ) as controlador:
                respuesta = getattr(self.client, metodo)(
                    ruta, data='{}', content_type='application/json', **cabeceras,
                )
                self.assertEqual(respuesta.status_code, estado)
                if estado == 200:
                    controlador.assert_called_once()
                else:
                    controlador.assert_not_called()

    def test_rechaza_escrituras_sin_token(self):
        self.comprobar_operaciones(self.administrador, 403)

    def test_rechaza_token_que_no_corresponde_a_la_cookie(self):
        self.token_csrf()
        self.comprobar_operaciones(
            self.administrador, 403, HTTP_X_CSRFTOKEN='A' * 64,
        )

    def test_rechaza_origen_no_confiable_aunque_el_token_sea_valido(self):
        self.comprobar_operaciones(
            self.administrador, 403, HTTP_X_CSRFTOKEN=self.token_csrf(),
            HTTP_ORIGIN='https://no-confiable.invalid',
        )

    def test_administrador_con_token_y_origen_validos_llega_al_controlador(self):
        self.comprobar_operaciones(
            self.administrador, 200, HTTP_X_CSRFTOKEN=self.token_csrf(),
            HTTP_ORIGIN='http://testserver',
        )

    def test_token_valido_no_otorga_permisos_administrativos(self):
        profesional = SimpleNamespace(pk=2, estado='ACTIVO', rol='PROFESIONAL')
        self.comprobar_operaciones(
            profesional, 403, HTTP_X_CSRFTOKEN=self.token_csrf(),
        )

    def test_token_valido_no_autentica_un_usuario_anonimo(self):
        self.comprobar_operaciones(None, 403, HTTP_X_CSRFTOKEN=self.token_csrf())
