"""Guardias offline del verificador LAN; no HTTP, procesos ni PostgreSQL reales."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[1]
LAUNCHER_SPEC = importlib.util.spec_from_file_location('_access_launcher_tested', TOOLS / 'entorno_local_skilly.py')
LAUNCHER = importlib.util.module_from_spec(LAUNCHER_SPEC)
LAUNCHER_SPEC.loader.exec_module(LAUNCHER)
SPEC = importlib.util.spec_from_file_location('_access_http_tested', TOOLS / 'verificar_acceso_local_skilly.py')
TOOL = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {'entorno_local_skilly': LAUNCHER}):
    SPEC.loader.exec_module(TOOL)


class LocalAccessSafetyTests(unittest.TestCase):
    def test_tcp_none_windows_sin_peer_identifica_solo_extremo_local_exacto(self):
        connection = SimpleNamespace(family=socket.AF_INET, type=socket.SOCK_STREAM, status='NONE',
                                     raddr=(), laddr=SimpleNamespace(ip='127.0.0.2', port=50123))
        self.assertTrue(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=True))
        self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=False))
        self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.2', 50124, windows=True))
        self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.1', 50123, windows=True))
        connection.type = socket.SOCK_DGRAM
        self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=True))

    def test_estados_conectados_o_peer_remoto_no_suplanten_listener(self):
        connection = SimpleNamespace(family=socket.AF_INET, type=socket.SOCK_STREAM, status='LISTEN',
                                     raddr=(), laddr=SimpleNamespace(ip='127.0.0.2', port=50123))
        self.assertTrue(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=True))
        for status in ('ESTABLISHED', 'TIME_WAIT', 'CLOSE_WAIT', 'CLOSE'):
            connection.status = status
            self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=True))
        for status in ('LISTEN', 'NONE'):
            connection.status, connection.raddr = status, ('192.0.2.44', 12345)
            self.assertFalse(TOOL.tcp_bound_to(connection, '127.0.0.2', 50123, windows=True))

    def test_origen_no_acepta_servicio_ajeno_puerto_prohibido_o_credenciales(self):
        for value in ('http://127.0.0.2:8000', 'http://127.0.0.2:57647',
                      'http://127.0.0.1:50123', 'https://127.0.0.2:50123',
                      'http://secret:canary@127.0.0.2:50123', 'http://127.0.0.2:50123/?x=1'):
            with self.subTest(value=value), self.assertRaises(TOOL.VerificationRejected):
                TOOL.validated_origin(value, '127.0.0.2')

    def test_origenes_desktop_y_lan_canonicos_se_aceptan(self):
        self.assertEqual(TOOL.validated_origin('http://127.0.0.2:50123', '127.0.0.2').port, 50123)
        self.assertEqual(TOOL.validated_origin('http://192.168.100.19:50124', '192.168.100.19').port, 50124)

    def test_cliente_no_envia_a_origen_no_seleccionado_ni_post_negocio(self):
        client = TOOL.LocalHttp(['http://127.0.0.2:50123'])
        client.opener = Mock()
        for origin, path, method in (
            ('http://127.0.0.1:8000', TOOL.CSRF, 'GET'),
            ('http://127.0.0.2:50123', '/api/pagos/webpay/retorno/', 'POST'),
            ('http://127.0.0.2:50123', TOOL.CATALOG, 'POST'),
            ('http://127.0.0.2:50123', '/api/solicitudes/enviar/', 'POST'),
        ):
            with self.subTest(path=path), self.assertRaises(TOOL.VerificationRejected):
                client.request(origin, path, method=method)
        client.opener.open.assert_not_called()

    def test_redirecciones_no_se_siguen_a_ningun_destino(self):
        for target in ('https://example.invalid/provider', 'http://127.0.0.1:8000/'):
            self.assertIsNone(TOOL.NoRedirect().redirect_request(None, None, 302, '', {}, target))

    def test_fuente_nueva_no_incluida_o_modificada_invalida_manifiesto(self):
        with tempfile.TemporaryDirectory(prefix='skilly-access-sources-') as temporary:
            root = Path(temporary)
            (root / 'backend/config').mkdir(parents=True)
            wsgi = root / 'backend/config/wsgi.py'
            wsgi.write_text('# fixture WSGI only\n', encoding='utf-8')
            identity = {'pid': 101, 'project_root': str(root), 'wsgi_file': str(wsgi),
                        'product_sources': {str(wsgi.relative_to(root)): hashlib.sha256(wsgi.read_bytes()).hexdigest()}}
            with patch.object(TOOL, 'ROOT', root):
                self.assertEqual(TOOL.current_sources(identity, 101), identity['product_sources'])
                extra = root / 'backend/config/cache.py'
                extra.write_text('# new product module\n', encoding='utf-8')
                with self.assertRaises(TOOL.VerificationRejected):
                    TOOL.current_sources(identity, 101)
                extra.unlink()
                wsgi.write_text('# modified fixture WSGI\n', encoding='utf-8')
                with self.assertRaises(TOOL.VerificationRejected):
                    TOOL.current_sources(identity, 101)

    def test_error_de_argumentos_no_revela_valor_privado(self):
        canary = 'synthetic-private-argument-not-a-real-secret'
        parser = TOOL.PrivateArgumentParser()
        with self.assertRaises(TOOL.VerificationRejected) as caught:
            parser.parse_args(['--unknown=' + canary])
        self.assertNotIn(canary, str(caught.exception))


if __name__ == '__main__':
    unittest.main()
