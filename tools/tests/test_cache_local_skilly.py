"""Guardias operativas de Memurai con proceso/transporte simulados, sin servicios."""
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


TOOL_PATH = Path(__file__).resolve().parents[1] / 'cache_local_skilly.py'
SPEC = importlib.util.spec_from_file_location('_cache_local_tested', TOOL_PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class CacheLocalTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix='skilly-cache-guard-test-')).resolve()
        self.assertEqual(self.scratch.parent, Path(tempfile.gettempdir()).resolve())
        self.backup = self.scratch / 'SKILLY_recuperacion_fixture'
        self.run = self.backup / 'cache_activa_fixture'
        self.binary = self.backup / 'Memurai/memurai.exe'
        self.config = self.run / 'memurai.conf'
        self.run.mkdir(parents=True)
        self.binary.parent.mkdir()
        self.binary.write_bytes(b'Synthetic binary bytes, never executed')
        self.config.write_text('Synthetic fixture, not a running server', encoding='utf-8')
        self.canary = secrets.token_hex(32)
        self.context = {'pid': 12345, 'host': '127.0.0.1', 'port': 49123,
                        'password': self.canary, 'created': 123.0, 'run_dir': str(self.run),
                        'binary': str(self.binary), 'config': str(self.config),
                        'binary_sha256': hashlib.sha256(self.binary.read_bytes()).hexdigest()}
        self.process = SimpleNamespace(pid=12345, exe=Mock(return_value=str(self.binary)),
            create_time=Mock(return_value=123.0), cmdline=Mock(return_value=[str(self.binary), str(self.config)]))
        self.extra_files = []

    def tearDown(self):
        for file in self.extra_files:
            self.assertTrue(file.is_relative_to(self.scratch))
            file.unlink(missing_ok=True)
        for file in [self.config, self.binary]:
            self.assertTrue(file.is_relative_to(self.scratch))
            file.unlink(missing_ok=True)
        for directory in [self.binary.parent, self.run, self.backup, self.scratch]:
            self.assertTrue(directory == self.scratch or directory.is_relative_to(self.scratch))
            directory.rmdir()

    def test_context_requires_backup_owned_paths_and_never_original_ports(self):
        self.assertEqual(TOOL.context_paths(self.context, self.backup)[0], self.run)
        for changes in [{'run_dir': str(TOOL.ROOT)}, {'config': str(self.binary)},
                        {'host': '0.0.0.0'}, {'host': '127.0.0.1.example.invalid'},
                        *[{'port': value} for value in [8000, 5432, 5173, 9000, 80, True]]]:
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                TOOL.context_paths({**self.context, **changes}, self.backup)

    def test_process_pid_reuse_foreign_command_or_modified_binary_is_rejected(self):
        with patch('psutil.Process', return_value=self.process):
            self.assertIs(TOOL.cache_process(self.context, self.backup), self.process)
            self.process.create_time.return_value = 140.0
            with self.assertRaises(ValueError):
                TOOL.cache_process(self.context, self.backup)
            self.process.create_time.return_value = 123.0
            self.process.cmdline.return_value = [str(self.binary), str(self.binary)]
            with self.assertRaises(ValueError):
                TOOL.cache_process(self.context, self.backup)
            self.process.cmdline.return_value = [str(self.binary), str(self.config)]
            self.binary.write_bytes(b'Changed synthetic executable bytes')
            with self.assertRaises(ValueError):
                TOOL.cache_process(self.context, self.backup)

    def test_authenticated_status_crosschecks_server_pid_and_safe_configuration(self):
        expected = {'bind': '127.0.0.1', 'protected-mode': 'yes', 'maxmemory': str(64 * 1024 * 1024),
                    'maxmemory-policy': 'noeviction', 'save': '', 'appendonly': 'no'}
        client = SimpleNamespace(ping=Mock(return_value=True), info=Mock(return_value={'process_id': 12345, 'redis_version': '7.2.0'}),
                                 config_get=Mock(side_effect=lambda key: {key: expected[key]}), close=Mock())
        with patch.object(TOOL, 'cache_process', return_value=self.process), patch.object(TOOL, 'redis_connection', return_value=client):
            report = TOOL.authenticated_state(self.context, self.backup)
            self.assertTrue(report['authenticated_ping'])
            self.assertNotIn(self.canary, json.dumps(report))
            client.info.return_value = {'process_id': 12346, 'redis_version': '7.2.0'}
            with self.assertRaises(ValueError):
                TOOL.authenticated_state(self.context, self.backup)
            client.info.return_value['process_id'] = 12345
            expected['protected-mode'] = 'no'
            with self.assertRaises(ValueError):
                TOOL.authenticated_state(self.context, self.backup)
        self.assertEqual(client.close.call_count, 3)

    def test_rejected_port_never_binds_and_busy_port_does_not_choose_another(self):
        for port in [8000, 5432, 5173, 9000, 80, -1, True, '49123']:
            with patch.object(TOOL.socket, 'socket') as factory, self.assertRaises(ValueError):
                TOOL.free_port(port)
            factory.assert_not_called()
        listener = Mock()
        listener.__enter__ = Mock(return_value=listener)
        listener.__exit__ = Mock(return_value=False)
        listener.bind.side_effect = OSError('Synthetic busy port')
        with patch.object(TOOL.socket, 'socket', return_value=listener), self.assertRaises(OSError):
            TOOL.free_port(49123)
        listener.bind.assert_called_once_with(('127.0.0.1', 49123))
        listener.connect.assert_not_called()

    def test_cli_never_echoes_private_json_or_bad_argument_values(self):
        file = self.run / 'conexion_privada.json'
        file.write_text('{"password":"' + self.canary, encoding='utf-8')
        self.extra_files.append(file)
        for args in [['estado', '--contexto', str(file)],
                     ['iniciar', '--respaldo', str(self.backup), '--binario', str(self.binary),
                      '--sha256', '0' * 64, '--puerto', self.canary]]:
            child = subprocess.run([sys.executable, '-B', str(TOOL_PATH), *args], capture_output=True,
                                   text=True, encoding='utf-8', timeout=15)
            self.assertEqual(child.returncode, 1)
            self.assertEqual(child.stderr, '')
            self.assertNotIn(self.canary, child.stdout)
            self.assertNotIn('password', child.stdout)
            self.assertFalse(json.loads(child.stdout)['completed'])


if __name__ == '__main__':
    unittest.main()
