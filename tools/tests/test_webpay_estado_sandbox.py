"""Pruebas offline de consulta de estado; sin Django, BD ni credenciales reales."""
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError


TOOL_PATH = Path(__file__).resolve().parents[1] / 'webpay_estado_sandbox.py'
SPEC = importlib.util.spec_from_file_location('_webpay_estado_tested', TOOL_PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def native_path(path):
    """Solo amplía rutas locales propias, sin cambiar políticas de Windows."""
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' else path


class FakeResponse:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.read_limits = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        self.read_limits.append(limit)
        return self.body[:limit]


class EstadoSandboxTest(unittest.TestCase):
    def setUp(self):
        self.token = '0' * 16
        self.canary = 'private-canary-' + secrets.token_hex(24)
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.client = SimpleNamespace(CODIGO='0', CLAVE='0', contexto_tls_webpay=Mock(return_value=self.context))
        self.scratch = Path(tempfile.mkdtemp(prefix='skilly-estado-sandbox-test-')).resolve()
        self.assertTrue(self.scratch.is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.created_files = set()
        self.created_dirs = set()

    def tearDown(self):
        # Cada ruta pertenece al directorio único creado por esta prueba; se
        # eliminan elementos concretos, sin borrado recursivo ni comodines.
        for file in sorted(self.created_files, key=lambda item: len(str(item)), reverse=True):
            self.assertTrue(file.is_relative_to(self.scratch))
            native_path(file).unlink(missing_ok=True)
        for directory in sorted(self.created_dirs, key=lambda item: len(str(item)), reverse=True):
            self.assertTrue(directory.is_relative_to(self.scratch))
            native_path(directory).rmdir()
        self.scratch.rmdir()

    def directory(self, path):
        path = Path(path)
        missing = []
        cursor = path
        while cursor != self.scratch:
            self.assertTrue(cursor.is_relative_to(self.scratch))
            if not native_path(cursor).exists():
                missing.append(cursor)
            cursor = cursor.parent
        for directory in reversed(missing):
            native_path(directory).mkdir()
            self.created_dirs.add(directory)
        return path

    def checkout(self, data=None, *, path=None):
        file = Path(path) if path else self.scratch / 'checkout_privado.json'
        self.directory(file.parent)
        if data is None:
            data = {'ambiente': 'TRANSBANK_INTEGRACION', 'token': self.token,
                    'url': TOOL.HOST + '/webpayserver/initTransaction'}
        native_path(file).write_text(json.dumps(data), encoding='utf-8')
        self.created_files.add(file)
        return file

    def query(self, payload):
        response = FakeResponse(payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8'))
        transport = SimpleNamespace(open=Mock(return_value=response))
        result = TOOL.query_state(self.token, self.client, opener=transport)
        return result, transport, response

    def assert_private_absent(self, result):
        serialized = json.dumps(result)
        self.assertNotIn(self.canary, serialized)
        for field in ('buy_order', 'session_id', 'card_detail', 'card_number', 'token', 'response_body', 'message', 'stack'):
            self.assertNotIn(field, result)

    def test_get_usa_destino_fijo_sin_cuerpo_timeout_y_lectura_acotada(self):
        result, transport, response = self.query({'status': 'INITIALIZED'})
        request = transport.open.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertEqual(request.full_url, TOOL.HOST + TOOL.API + self.token)
        self.assertIsNone(request.data)
        self.assertEqual(transport.open.call_args.kwargs, {'timeout': 12})
        self.assertEqual(response.read_limits, [65537])
        self.assertEqual(transport.open.call_count, 1)
        self.assertTrue(result['completed'])
        self.assertTrue(result['read_only'])
        self.assertFalse(result['production_provider'])
        self.assertFalse(result['authorization_verified'])

    def test_transporte_conserva_tls_y_deshabilita_proxy_y_redirecciones(self):
        transport = SimpleNamespace(open=Mock(return_value=FakeResponse(b'{"status":"INITIALIZED"}')))
        with patch.object(TOOL, 'build_opener', return_value=transport) as build:
            TOOL.query_state(self.token, self.client)
        self.client.contexto_tls_webpay.assert_called_once_with()
        handlers = build.call_args.args
        self.assertEqual(len(handlers), 3)
        self.assertIsInstance(handlers[0], TOOL.ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], TOOL.NoRedirect)
        self.assertIsInstance(handlers[2], TOOL.HTTPSHandler)
        self.assertIs(handlers[2]._context, self.context)

    def test_rechaza_tls_inseguro_antes_de_abrir_transporte(self):
        for verify, hostname, minimum in (
            (ssl.CERT_NONE, True, ssl.TLSVersion.TLSv1_2),
            (ssl.CERT_REQUIRED, False, ssl.TLSVersion.TLSv1_2),
            (ssl.CERT_REQUIRED, True, ssl.TLSVersion.TLSv1_1),
        ):
            with self.subTest(verify=verify, hostname=hostname, minimum=minimum):
                context = SimpleNamespace(verify_mode=verify, check_hostname=hostname, minimum_version=minimum)
                client = SimpleNamespace(contexto_tls_webpay=lambda: context)
                transport = SimpleNamespace(open=Mock())
                with self.assertRaises(TOOL.InvalidCheckout):
                    TOOL.query_state(self.token, client, opener=transport)
                transport.open.assert_not_called()

    def test_estados_permitidos_no_exportan_identificadores_ni_prueban_autorizacion(self):
        for state in ('INITIALIZED', 'AUTHORIZED', 'REVERSED', 'FAILED', 'NULLIFIED', 'PARTIALLY_NULLIFIED', 'CAPTURED'):
            with self.subTest(state=state):
                result, _, _ = self.query({'status': state, 'buy_order': self.canary,
                                          'session_id': self.canary, 'card_detail': {'card_number': self.canary},
                                          'message': self.canary, 'response_code': 0})
                self.assertTrue(result['completed'])
                self.assertEqual(result['transaction_status'], state)
                self.assertFalse(result['authorization_verified'])
                self.assert_private_absent(result)

    def test_respuesta_desconocida_invalida_o_excesiva_no_filtra_contenido(self):
        for payload, expected in (
            ({'status': self.canary, 'message': self.canary}, 'UNRECOGNIZED_STATE'),
            ({'status': [self.canary]}, 'INVALID_RESPONSE'),
            ([self.canary], 'UNRECOGNIZED_STATE'),
            (self.canary.encode('utf-8'), 'INVALID_RESPONSE'),
            (b'x' * 65537, 'RESPONSE_TOO_LARGE'),
        ):
            with self.subTest(expected=expected):
                result, _, _ = self.query(payload)
                self.assertFalse(result['completed'])
                self.assertEqual(result['error_code'], expected)
                self.assert_private_absent(result)

    def test_errores_http_solo_conservan_codigo_y_no_cuerpo_headers_o_mensaje(self):
        for code in (302, 401, 404, 500):
            with self.subTest(code=code):
                error = HTTPError(self.canary, code, self.canary, {'Location': self.canary}, io.BytesIO(self.canary.encode()))
                transport = SimpleNamespace(open=Mock(side_effect=error))
                result = TOOL.query_state(self.token, self.client, opener=transport)
                self.assertFalse(result['completed'])
                self.assertEqual(result['http_status'], code)
                self.assertEqual(result['error_code'], 'HTTP_ERROR')
                self.assert_private_absent(result)
                error.close()

    def test_fallos_de_red_no_exportan_mensajes_de_excepcion(self):
        for error in (URLError(self.canary), TimeoutError(self.canary), OSError(self.canary)):
            with self.subTest(kind=type(error).__name__):
                transport = SimpleNamespace(open=Mock(side_effect=error))
                result = TOOL.query_state(self.token, self.client, opener=transport)
                self.assertEqual(result['error_code'], 'TRANSPORT_ERROR')
                self.assert_private_absent(result)

    def test_redireccion_no_puede_enviar_token_o_cabeceras_a_otro_host(self):
        request = TOOL.Request(TOOL.HOST + TOOL.API + self.token, method='GET')
        handler = TOOL.NoRedirect()
        with self.assertRaises(HTTPError) as caught:
            handler.redirect_request(request, None, 302, self.canary, {'Location': 'https://example.invalid/'}, 'https://example.invalid/')
        self.assertEqual(caught.exception.code, 302)

    def test_checkout_externo_valido_se_lee_sin_cliente_o_red(self):
        file = self.checkout()
        with patch.object(TOOL, 'client_module') as client:
            loaded, token = TOOL.load_checkout(str(file))
        self.assertEqual(loaded.name, 'checkout_privado.json')
        self.assertEqual(token, self.token)
        client.assert_not_called()

    def test_rechaza_produccion_http_host_similar_usuario_y_token_invalido(self):
        base = {'ambiente': 'TRANSBANK_INTEGRACION', 'token': self.token,
                'url': TOOL.HOST + '/webpayserver/initTransaction'}
        changes = (
            {'ambiente': 'PRODUCCION'}, {'url': 'https://webpay3g.transbank.cl/x'},
            {'url': 'http://webpay3gint.transbank.cl/x'},
            {'url': 'https://webpay3gint.transbank.cl.example.invalid/x'},
            {'url': 'https://user@webpay3gint.transbank.cl/x'},
            {'url': TOOL.HOST + ':444/x'}, {'url': TOOL.HOST + '/x#fragment'},
            {'token': '../' + self.canary}, {'token': 'x' * 201}, {'token': ''}, {'token': None},
        )
        for change in changes:
            with self.subTest(fields=tuple(change)):
                file = self.checkout({**base, **change})
                with self.assertRaises(TOOL.InvalidCheckout):
                    TOOL.load_checkout(str(file))

    def test_rechaza_archivo_dentro_del_repositorio(self):
        owned = TOOL.ROOT / ('.skilly-estado-test-' + secrets.token_hex(8) + '.tmp')
        self.assertTrue(owned.is_relative_to(TOOL.ROOT))
        owned.mkdir()
        file = owned / 'checkout_privado.json'
        try:
            file.write_text(json.dumps({'token': self.token}), encoding='utf-8')
            with self.assertRaises(TOOL.InvalidCheckout):
                TOOL.load_checkout(str(file))
        finally:
            file.unlink(missing_ok=True)
            owned.rmdir()

    def test_rechaza_ruta_relativa_y_nombre_no_privado(self):
        with self.assertRaises(TOOL.InvalidCheckout):
            TOOL.load_checkout('checkout_privado.json')
        file = self.checkout(path=self.scratch / 'otro.json')
        with self.assertRaises(TOOL.InvalidCheckout):
            TOOL.load_checkout(str(file))

    def test_cli_json_corrupto_no_filtra_canario_fragmento_o_stack(self):
        file = self.scratch / 'checkout_privado.json'
        file.write_text('{"private_field":"' + self.canary, encoding='utf-8')
        self.created_files.add(file)
        completed = subprocess.run([sys.executable, '-B', str(TOOL_PATH), str(file)],
                                   capture_output=True, text=True, timeout=15,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr.strip(), '')
        self.assertNotIn(self.canary, completed.stdout)
        self.assertNotIn('private_field', completed.stdout)
        self.assertNotIn('Traceback', completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result['error_code'], 'JSONDecodeError')
        self.assertTrue(result['read_only'])

    @unittest.skipUnless(os.name == 'nt', 'Regresion especifica de rutas MAX_PATH de Windows')
    def test_checkout_mayor_que_max_path_sin_cambiar_politicas_windows(self):
        directory = self.scratch
        while len(str(directory / 'checkout_privado.json')) <= 300:
            directory /= 'segmento_largo_de_evidencia_' + secrets.token_hex(12)
        file = self.checkout(path=directory / 'checkout_privado.json')
        self.assertGreater(len(str(file)), 260)
        loaded, token = TOOL.load_checkout(str(file))
        self.assertEqual(token, self.token)
        self.assertEqual(loaded.name, 'checkout_privado.json')
        self.assertTrue(loaded.exists())


if __name__ == '__main__':
    unittest.main()
