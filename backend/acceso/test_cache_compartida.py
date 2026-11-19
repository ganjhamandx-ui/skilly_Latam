"""Regresiones del contador Redis; transporte simulado y sin datos ni servicios reales."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache.backends.redis import RedisCache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from config.cache_acceso import (
    LOCAL, REDIS_ATOMICO, REDIS_DJANGO, configurar_cache_acceso, ubicacion_redis_valida,
)
from .cache import RedisIntentosCache
from .checks import cache_acceso_compartida, configuracion_limites_acceso
from .intentos import ControlIntentosNoDisponible, LimiteIntentosAcceso


def configuracion(**extra):
    """Construye una configuración Redis ficticia para pruebas sin red real."""

    return {'BACKEND': REDIS_ATOMICO, 'LOCATION': 'redis://127.0.0.1:49123/0', **extra}


class ConfiguracionRedisAccesoTests(SimpleTestCase):
    """Valida selección y parámetros seguros del backend de intentos compartido."""

    def test_configuracion_local_sigue_siendo_default_y_no_abre_conexiones(self):
        with patch('socket.socket', side_effect=AssertionError('No network expected')):
            result = configurar_cache_acceso({})
        self.assertEqual(result['BACKEND'], LOCAL)
        self.assertEqual(result['LOCATION'], 'skilly-acceso-local')

    def test_alias_builtin_usa_subclass_oficial_y_options_acotadas(self):
        result = configurar_cache_acceso({
            'ACCESO_CACHE_BACKEND': REDIS_DJANGO,
            'ACCESO_CACHE_LOCATION': 'redis://127.0.0.1:49123/0',
            'ACCESO_CACHE_KEY_PREFIX': 'skilly-prueba:compartida',
            'ACCESO_CACHE_TIMEOUT': '0.5',
        })
        self.assertEqual(result['BACKEND'], REDIS_ATOMICO)
        self.assertEqual(result['KEY_PREFIX'], 'skilly-prueba:compartida')
        self.assertEqual(result['OPTIONS'], {'socket_connect_timeout': .5, 'socket_timeout': .5})
        self.assertTrue(issubclass(RedisIntentosCache, RedisCache))

    def test_uri_ambigua_timeout_o_prefijo_invalidos_no_revelan_configuracion(self):
        canary = 'private-test-value-not-an-operational-credential'
        for location in [
            'redis://127.0.0.1:49123/0?socket_timeout=0',
            'redis://127.0.0.1:49123/0;redis://other:49124/0',
            'http://127.0.0.1:49123/0', 'redis:///0', 'redis://localhost/0',
            'redis://user:' + canary + '@localhost:49123/0#fragment',
        ]:
            with self.subTest(case='location'), self.assertRaises(ImproperlyConfigured) as exc:
                configurar_cache_acceso({'ACCESO_CACHE_BACKEND': REDIS_ATOMICO, 'ACCESO_CACHE_LOCATION': location})
            self.assertNotIn(location, str(exc.exception))
            self.assertNotIn(canary, str(exc.exception))
        for timeout in ['0', '-1', 'infinity', 'nan', '6', 'not-a-number', True]:
            with self.subTest(case='timeout'), self.assertRaises(ImproperlyConfigured):
                configurar_cache_acceso({'ACCESO_CACHE_BACKEND': REDIS_ATOMICO,
                    'ACCESO_CACHE_LOCATION': 'redis://127.0.0.1:49123/0', 'ACCESO_CACHE_TIMEOUT': timeout})
        for prefix in ['', 'x' * 65, 'namespace with spaces', 'namespace\nother']:
            with self.assertRaises(ImproperlyConfigured):
                configurar_cache_acceso({'ACCESO_CACHE_KEY_PREFIX': prefix})

    def test_endpoint_unico_admite_tls_y_configuracion_privada_sin_conectarse(self):
        for location in ['redis://localhost:49123/0', 'redis://[::1]:49123/1', 'rediss://user:synthetic@cache.example.invalid:49123/3']:
            self.assertTrue(ubicacion_redis_valida(location))

    @override_settings(CACHES={'acceso_intentos': configuracion()})
    def test_checks_no_conectan_y_reconocen_backend_atomico(self):
        with patch('socket.socket', side_effect=AssertionError('No network expected')):
            self.assertEqual(configuracion_limites_acceso(None), [])
            self.assertEqual(cache_acceso_compartida(None), [])

    @override_settings(CACHES={'acceso_intentos': configuracion(LOCATION='redis://localhost:49123/0?retry=99')})
    def test_checks_rechazan_uri_no_validada_sin_exponerla(self):
        messages = configuracion_limites_acceso(None)
        self.assertIn('acceso.E003', [message.id for message in messages])
        self.assertNotIn('retry=99', str(messages))


class ContadorRedisAccesoTests(SimpleTestCase):
    """Comprueba ventanas atómicas usando un cliente Redis simulado."""

    def setUp(self):
        self.cache = RedisIntentosCache('redis://127.0.0.1:49123/0', {
            'KEY_PREFIX': 'skilly-fixture', 'VERSION': 7,
        })
        self.client = Mock()
        self.backend = SimpleNamespace(get_client=Mock(return_value=self.client))
        self.cache._cache = self.backend

    def test_comando_unico_utiliza_clave_versionada_y_primario(self):
        self.client.eval.return_value = [4, 2]
        self.assertEqual(self.cache.incrementar_ventana('skilly:intentos:huella:5', 5), (4, 2))
        key = self.cache.make_and_validate_key('skilly:intentos:huella:5')
        self.backend.get_client.assert_called_once_with(key, write=True)
        self.assertEqual(self.client.eval.call_args.args[1:], (1, key, 5))
        self.client.eval.assert_called_once()
        self.assertEqual(self.cache._options['retry'].get_retries(), 0)
        self.assertFalse(self.cache._options['retry_on_timeout'])
        self.assertEqual(self.cache._options['socket_timeout'], 1)

    def test_ventana_invalida_no_abre_cliente_y_respuesta_invalida_no_se_admite(self):
        for window in [0, 86401, True, '5']:
            with self.assertRaises(ValueError):
                self.cache.incrementar_ventana('huella', window)
        self.backend.get_client.assert_not_called()
        for result in [None, [1], [True, 2], [0, 2], [1, False], [1, 0], [1, 6], ['4', 2]]:
            self.client.eval.return_value = result
            with self.subTest(case='malformed_server_reply'), self.assertRaises(ValueError):
                self.cache.incrementar_ventana('huella', 5)

    def test_todas_las_dimensiones_y_ventanas_se_cuentan_en_un_solo_eval(self):
        windows = [('ip:5', 5), ('ip:30', 30), ('identidad_ip:5', 5), ('identidad_ip:30', 30)]
        self.client.eval.return_value = [3, 2, 10, 29, 3, 2, 10, 29]
        self.assertEqual(self.cache.incrementar_ventanas(windows), [(3, 2), (10, 29), (3, 2), (10, 29)])
        keys = [self.cache.make_and_validate_key(key) for key, _window in windows]
        self.backend.get_client.assert_called_once_with(keys[0], write=True)
        self.client.eval.assert_called_once()
        self.assertEqual(self.client.eval.call_args.args[1:], (4, *keys, 5, 30, 5, 30))

    def test_batch_invalido_no_abre_cliente_y_respuesta_incompleta_se_rechaza(self):
        for windows in [[], None, '5', [('huella', 0)], [('huella', True)], [('huella', 5, 1)]]:
            with self.subTest(case='invalid_windows'), self.assertRaises(ValueError):
                self.cache.incrementar_ventanas(windows)
        self.backend.get_client.assert_not_called()
        for result in [[1, 2], [1, 2, 1], [1, 2, 1, 6], [1, 2, True, 2], [1, 2, 1, 0]]:
            self.client.eval.return_value = result
            with self.subTest(case='invalid_batch_reply'), self.assertRaises(ValueError):
                self.cache.incrementar_ventanas([('ip', 5), ('identidad', 5)])

    @override_settings(ACCESO_PROXIES_CONFIABLES=[], ACCESO_LIMITES={
        'iniciar_sesion': {'ip': ['3/5', '12/30'], 'identidad_ip': ['3/5', '12/30']},
    })
    def test_limiter_envia_las_dos_dimensiones_completas_en_un_batch(self):
        request = Request(APIRequestFactory().post('/', {'correo': 'synthetic@example.invalid'}, format='json', REMOTE_ADDR='192.0.2.24'), parsers=[JSONParser()])
        self.client.eval.return_value = [3, 2, 12, 20, 3, 2, 12, 20]
        with patch('acceso.intentos.caches', {'acceso_intentos': self.cache}), patch.object(
            self.cache, 'incrementar_ventana', side_effect=AssertionError('No per-dimension command'),
        ):
            self.assertTrue(LimiteIntentosAcceso().allow_request(request, SimpleNamespace(alcance_intentos='iniciar_sesion')))
        self.client.eval.assert_called_once()
        arguments = self.client.eval.call_args.args
        self.assertEqual(arguments[1], 4)
        self.assertEqual(arguments[6:], (5, 30, 5, 30))
        self.assertEqual(sum(':ip:' in key for key in arguments[2:6]), 2)
        self.assertEqual(sum(':identidad_ip:' in key for key in arguments[2:6]), 2)

    @override_settings(ACCESO_PROXIES_CONFIABLES=[], ACCESO_LIMITES={
        'iniciar_sesion': {'ip': ['3/5'], 'identidad_ip': ['3/5']},
    })
    def test_limiter_no_admite_resultados_parciales_del_batch(self):
        request = Request(APIRequestFactory().post('/', {'correo': 'synthetic@example.invalid'}, format='json', REMOTE_ADDR='192.0.2.25'), parsers=[JSONParser()])
        self.client.eval.return_value = [1, 2]
        with patch('acceso.intentos.caches', {'acceso_intentos': self.cache}), self.assertRaises(ControlIntentosNoDisponible) as error:
            LimiteIntentosAcceso().allow_request(request, SimpleNamespace(alcance_intentos='iniciar_sesion'))
        self.assertEqual(error.exception.status_code, 503)
        self.client.eval.assert_called_once()
        with patch('acceso.intentos.caches', {'acceso_intentos': self.cache}), patch.object(
            self.cache, 'incrementar_ventanas', return_value=[(1, 2)],
        ), self.assertRaises(ControlIntentosNoDisponible):
            LimiteIntentosAcceso().allow_request(request, SimpleNamespace(alcance_intentos='iniciar_sesion'))

    @override_settings(ACCESO_PROXIES_CONFIABLES=[], ACCESO_LIMITES={
        'iniciar_sesion': {'ip': ['3/5'], 'identidad_ip': ['3/5']},
    })
    def test_limiter_usa_espera_del_servidor_y_no_touch_ni_reloj_del_worker(self):
        raw = APIRequestFactory().post('/', {'correo': 'synthetic@example.invalid'}, format='json', REMOTE_ADDR='192.0.2.22')
        request = Request(raw, parsers=[JSONParser()])
        self.client.eval.return_value = [4, 2, 4, 2]
        with patch('acceso.intentos.caches', {'acceso_intentos': self.cache}), patch('acceso.intentos.time.time', side_effect=AssertionError('No worker clock')), patch.object(self.cache, 'touch', side_effect=AssertionError('No renew')), patch.object(self.cache, 'add', side_effect=AssertionError('No generic init')):
            throttle = LimiteIntentosAcceso()
            self.assertFalse(throttle.allow_request(request, SimpleNamespace(alcance_intentos='iniciar_sesion')))
            self.assertEqual(throttle.wait(), 2)

    @override_settings(ACCESO_PROXIES_CONFIABLES=[], ACCESO_LIMITES={
        'iniciar_sesion': {'ip': ['3/5'], 'identidad_ip': ['3/5']},
    })
    def test_error_redis_falla_cerrado_sin_uri_o_mensaje_de_excepcion(self):
        canary = 'private-test-backend-message'
        self.client.eval.side_effect = RuntimeError(canary)
        request = Request(APIRequestFactory().post('/', {'correo': 'synthetic@example.invalid'}, format='json', REMOTE_ADDR='192.0.2.23'), parsers=[JSONParser()])
        with patch('acceso.intentos.caches', {'acceso_intentos': self.cache}), self.assertRaises(ControlIntentosNoDisponible) as exc:
            LimiteIntentosAcceso().allow_request(request, SimpleNamespace(alcance_intentos='iniciar_sesion'))
        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.wait, 30)
        self.assertNotIn(canary, str(exc.exception.detail))
        self.assertIsNone(exc.exception.__cause__)
