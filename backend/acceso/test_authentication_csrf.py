"""CSRF de la autenticacion por sesion, con solicitudes reales y usuario simulado."""
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.middleware.csrf import get_token
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .authentication import SesionSkillyAuthentication


@override_settings(ALLOWED_HOSTS=['testserver'], CSRF_TRUSTED_ORIGINS=[])
class AutenticacionSesionCsrfTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.usuario = SimpleNamespace(pk=1, estado='ACTIVO', rol='PROFESIONAL')
        self.autenticacion = SesionSkillyAuthentication()

    def solicitud(self, metodo, *, token_valido=False, origen=None):
        solicitud = self.factory.generic(
            metodo, '/api/solicitudes/mi-disponibilidad/',
            data='{}', content_type='application/json',
        )
        # Una sesion en memoria/cookie evita cualquier acceso al backend de sesiones SQL.
        solicitud.session = SessionStore()
        solicitud.session['id_usuario'] = self.usuario.pk
        if token_valido:
            emisor = self.factory.get('/api/acceso/csrf/')
            token = get_token(emisor)
            solicitud.COOKIES[settings.CSRF_COOKIE_NAME] = emisor.META['CSRF_COOKIE']
            solicitud.META['HTTP_X_CSRFTOKEN'] = token
        if origen is not None:
            solicitud.META['HTTP_ORIGIN'] = origen
        return Request(solicitud, parsers=[JSONParser()])

    def autenticar_usuario_simulado(self, solicitud):
        with patch('acceso.authentication.Usuario.objects') as usuarios:
            usuarios.filter.return_value.first.return_value = self.usuario
            resultado = self.autenticacion.authenticate(solicitud)
            usuarios.filter.assert_called_once_with(
                id_usuario=self.usuario.pk, estado='ACTIVO',
            )
        return resultado

    def test_get_autentica_sin_exigir_token(self):
        self.assertEqual(
            self.autenticar_usuario_simulado(self.solicitud('GET')),
            (self.usuario, None),
        )

    def test_metodos_mutadores_rechazan_token_ausente(self):
        for metodo in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(metodo=metodo), self.assertRaises(PermissionDenied):
                self.autenticar_usuario_simulado(self.solicitud(metodo))

    def test_origen_no_confiable_se_rechaza_con_token_valido(self):
        solicitud = self.solicitud(
            'POST', token_valido=True, origen='https://no-confiable.invalid',
        )
        with self.assertRaises(PermissionDenied):
            self.autenticar_usuario_simulado(solicitud)

    def test_metodos_mutadores_admiten_cookie_cabecera_y_origen_validos(self):
        for metodo in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(metodo=metodo):
                solicitud = self.solicitud(
                    metodo, token_valido=True, origen='http://testserver',
                )
                self.assertEqual(
                    self.autenticar_usuario_simulado(solicitud), (self.usuario, None),
                )

    def test_sin_sesion_no_busca_usuario_ni_autentica(self):
        solicitud = self.solicitud('POST')
        del solicitud.session['id_usuario']
        with patch('acceso.authentication.Usuario.objects') as usuarios:
            self.assertIsNone(self.autenticacion.authenticate(solicitud))
            usuarios.filter.assert_not_called()

    def test_usuario_no_disponible_invalida_la_sesion(self):
        solicitud = self.solicitud('POST')
        with patch('acceso.authentication.Usuario.objects') as usuarios:
            usuarios.filter.return_value.first.return_value = None
            self.assertIsNone(self.autenticacion.authenticate(solicitud))
        self.assertNotIn('id_usuario', solicitud.session)
