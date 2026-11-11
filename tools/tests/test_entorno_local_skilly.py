"""Guardias del launcher con archivos ficticios y sockets simulados; sin servicios."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).resolve().parents[1] / 'entorno_local_skilly.py'
SPEC = importlib.util.spec_from_file_location('_entorno_local_tested', TOOL_PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def native(path):
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' else path


class BoundSocket:
    def __init__(self, calls, assigned, *, busy=False):
        self.calls, self.assigned, self.busy = calls, assigned, busy

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def setsockopt(self, *args):
        self.calls.append(('option', args))

    def bind(self, address):
        self.calls.append(('bind', address))
        if self.busy:
            raise OSError('Synthetic busy listener')

    def getsockname(self):
        return (TOOL.HOST, self.assigned)

    def connect(self, *args):
        raise AssertionError('No se debe sondear otro servicio mediante TCP')

    def connect_ex(self, *args):
        raise AssertionError('No se debe sondear otro servicio mediante TCP')


class EntornoLocalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product_manifest = {
            str(file.relative_to(TOOL.ROOT)): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in (TOOL.ROOT / 'backend').rglob('*.py')
            if not file.name.startswith('test') and '__pycache__' not in file.parts
        }

    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix='skilly-launcher-test-')).resolve()
        self.assertEqual(self.scratch.parent, Path(tempfile.gettempdir()).resolve())
        self.files, self.directories = set(), set()
        self.canary = secrets.token_hex(32)
        self.backup = self.directory(self.scratch / 'SKILLY_recuperacion_fixture')
        self.runtime = self.directory(self.backup / 'local_activo_0123456789abcdef')
        self.context_path = self.runtime / 'contexto.json'
        self.identity_path = self.runtime / 'backend_ready.json'
        self.context = {
            'project_root': str(TOOL.ROOT), 'run_dir': str(self.runtime),
            'backup_root': str(self.backup), 'host': '127.0.0.2',
            'backend_origin': 'http://127.0.0.2:49123',
            'frontend_origin': 'http://127.0.0.2:49124',
            'database_port': 57647, 'isolated_database': True,
            'source_identity_file': str(self.identity_path),
            'backend_pid': 12123, 'frontend_pid': 12124, 'supervisor_pid': 12125,
        }
        self.identity = {
            'pid': self.context['backend_pid'], 'project_root': str(TOOL.ROOT),
            'wsgi_file': str(TOOL.ROOT / 'backend/config/wsgi.py'),
            'product_sources': dict(self.product_manifest),
        }
        self.save_context()
        self.write_json(self.identity_path, self.identity)

    def tearDown(self):
        # Se retiran elementos concretos registrados, nunca el proyecto ni un
        # recorrido recursivo sobre una ruta proveniente del launcher.
        for file in sorted(self.files, key=lambda value: len(str(value)), reverse=True):
            self.assertTrue(file.is_relative_to(self.scratch))
            native(file).unlink(missing_ok=True)
        for directory in sorted(self.directories, key=lambda value: len(str(value)), reverse=True):
            self.assertTrue(directory.is_relative_to(self.scratch))
            native(directory).rmdir()
        self.scratch.rmdir()

    def directory(self, path):
        path = Path(path)
        self.assertTrue(path.is_relative_to(self.scratch))
        missing = []
        parent = path
        while parent != self.scratch and not native(parent).exists():
            missing.append(parent)
            parent = parent.parent
        native(path).mkdir(parents=True, exist_ok=True)
        self.directories.update(missing)
        return path

    def write(self, file, value):
        file = Path(file)
        self.directory(file.parent)
        native(file).write_bytes(value)
        self.files.add(file)

    def write_json(self, file, value):
        self.write(file, json.dumps(value).encode('utf-8'))

    def save_context(self):
        self.write_json(self.context_path, self.context)

    def remember_created(self, directory):
        self.assertTrue(directory.is_relative_to(self.scratch))
        for file in directory.rglob('*'):
            if file.is_file():
                self.files.add(file)
            elif file.is_dir():
                self.directories.add(file)

    def invoke(self, action='estado'):
        output = io.StringIO()
        with patch.object(sys, 'argv', [str(TOOL_PATH), action, '--contexto', str(self.context_path)]), contextlib.redirect_stdout(output):
            TOOL.main()
        return json.loads(output.getvalue())

    def private_sources(self):
        original = self.directory(self.scratch / 'operational_fixture')
        expected = {}
        for group, count in [('media', 18), ('entregas_privadas_e3', 3)]:
            for index in range(count):
                relative = Path(group) / 'nested' / ('synthetic-%02d.bin' % index)
                content = ('Synthetic private fixture %s %s' % (relative, self.canary)).encode()
                self.write(original / relative, content)
                self.write(self.backup / relative, content)
                expected[str(relative)] = hashlib.sha256(content).hexdigest()
        return original, expected

    def assert_sources_unchanged(self, original, expected):
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((original / relative).read_bytes()).hexdigest(), digest)
            self.assertEqual(hashlib.sha256((self.backup / relative).read_bytes()).hexdigest(), digest)

    def test_database_accepts_only_copy_identity_and_alternative_port(self):
        cfg = {'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '57647',
               'POSTGRES_DB': 'skilly', 'POSTGRES_SCHEMA': 'skilly', 'POSTGRES_USER': 'skilly_app'}
        self.assertEqual(TOOL.validate_database(cfg), 57647)
        for key, values in {
            'POSTGRES_HOST': ['0.0.0.0', '192.0.2.1', '127.0.0.1.example.invalid', '127.0.0.1@remote'],
            'POSTGRES_PORT': ['5432', '8000', '5173', '0', '-1', '65536'],
            'POSTGRES_DB': ['postgres', 'operational'],
            'POSTGRES_SCHEMA': ['skilly_cu040_pruebas', 'public'],
            'POSTGRES_USER': ['postgres', 'operational_user'],
        }.items():
            for value in values:
                with self.subTest(field=key), self.assertRaises((ValueError, TypeError)):
                    TOOL.validate_database({**cfg, key: value, 'POSTGRES_PASSWORD': self.canary})

    def test_port_selection_binds_only_new_host_without_tcp_probes(self):
        calls, ports = [], iter([8000, 49123, 49124])
        with patch.object(TOOL.socket, 'socket', side_effect=lambda: BoundSocket(calls, next(ports))):
            self.assertEqual(TOOL.free_port(0, {49123}), 49124)
        self.assertEqual([value for kind, value in calls if kind == 'bind'], [('127.0.0.2', 0)] * 3)

    def test_forbidden_ports_rejected_before_binding_and_busy_port_not_replaced(self):
        for port in [8000, 5173, 5432, -1, 65536, True, '49123']:
            with self.subTest(port_type=type(port).__name__), patch.object(TOOL.socket, 'socket') as socket_factory:
                with self.assertRaises(ValueError):
                    TOOL.free_port(port)
                socket_factory.assert_not_called()
        calls = []
        with patch.object(TOOL.socket, 'socket', return_value=BoundSocket(calls, 49123, busy=True)):
            with self.assertRaises(OSError):
                TOOL.free_port(49123)
        self.assertEqual([value for kind, value in calls if kind == 'bind'], [('127.0.0.2', 49123)])

    def test_context_bound_to_its_owned_run_and_identity_file(self):
        self.assertEqual(TOOL.context_from(self.context_path)['run_dir'], str(self.runtime))
        foreign_context = self.scratch / 'copied_context.json'
        self.write_json(foreign_context, self.context)
        with self.assertRaises(ValueError):
            TOOL.context_from(foreign_context)
        foreign_identity = self.scratch / 'forged_identity.json'
        self.write_json(foreign_identity, self.identity)
        self.context['source_identity_file'] = str(foreign_identity)
        self.save_context()
        with self.assertRaises(ValueError):
            TOOL.context_from(self.context_path)

    def test_context_rejects_original_paths_foreign_backup_or_host(self):
        baseline = dict(self.context)
        variants = [
            {'run_dir': str(TOOL.ROOT)},
            {'run_dir': str(self.scratch / 'unrelated')},
            {'backup_root': str(self.scratch / 'other_backup')},
            {'run_dir': str(self.backup / 'not_owned_runtime')},
            {'project_root': str(self.scratch)},
            {'isolated_database': False},
            {'host': '127.0.0.1'},
        ]
        for changes in variants:
            self.context = {**baseline, **changes}
            self.save_context()
            with self.subTest(changed_fields=list(changes)), self.assertRaises(ValueError):
                TOOL.context_from(self.context_path)

    def test_context_rejects_spy_urls_before_reading_identity(self):
        for field in ['backend_origin', 'frontend_origin']:
            previous = self.context[field]
            for value in [
                'http://127.0.0.1:49123', 'https://127.0.0.2:49123',
                'http://127.0.0.2:8000', 'http://127.0.0.2:5432', 'http://127.0.0.2:5173',
                'http://127.0.0.2', 'http://127.0.0.2:80',
                'http://127.0.0.2.example.invalid:49123',
                'http://user:%s@127.0.0.2:49123' % self.canary,
                'http://127.0.0.2:49123/private', 'http://127.0.0.2:49123?target=other',
                'http://127.0.0.2:49123#private',
            ]:
                self.context[field] = value
                self.save_context()
                with self.subTest(field=field), self.assertRaises(ValueError):
                    TOOL.context_from(self.context_path)
            self.context[field] = previous
        self.save_context()

    def test_stop_creates_only_own_marker_without_overwriting(self):
        result = self.invoke('detener')
        marker = self.runtime / 'stop.flag'
        self.files.add(marker)
        self.assertEqual(result, {'stop_requested': True})
        before = marker.read_bytes()
        with self.assertRaises(FileExistsError):
            self.invoke('detener')
        self.assertEqual(marker.read_bytes(), before)
        self.assertFalse((TOOL.ROOT / 'stop.flag').exists())

    def test_status_reports_current_real_product_source_without_connecting(self):
        with patch.object(TOOL.socket, 'socket', side_effect=AssertionError('No network expected')):
            result = self.invoke()
        self.assertIs(result['product_sources_current'], True)
        self.assertIs(result['isolated_database'], True)

    def test_manifest_escape_cannot_read_or_claim_other_source(self):
        for key in ['../outside.py', 'backend/../../outside.py', str(self.scratch / 'outside.py'), 'frontend/src/App.jsx']:
            self.identity['product_sources'] = {key: '0' * 64}
            self.write_json(self.identity_path, self.identity)
            with self.subTest(kind='escaping_manifest'), self.assertRaises(ValueError):
                self.invoke()

    def test_empty_or_wrong_process_identity_cannot_claim_current_product(self):
        baseline = dict(self.identity)
        for changes in [
            {'product_sources': {}}, {'pid': self.context['backend_pid'] + 1},
            {'project_root': str(self.scratch)}, {'wsgi_file': str(self.scratch / 'wrong_wsgi.py')},
        ]:
            self.identity = {**baseline, **changes}
            self.write_json(self.identity_path, self.identity)
            with self.subTest(changed_fields=list(changes)), self.assertRaises(ValueError):
                self.invoke()

    def test_copy_preserves_21_private_source_files_and_verifies_hashes(self):
        original, expected = self.private_sources()
        try:
            result = TOOL.copy_private_files(self.backup, self.runtime)
        finally:
            self.remember_created(self.runtime)
        self.assertEqual({item['group']: item['files'] for item in result}, {'media': 18, 'entregas_privadas_e3': 3})
        self.assertTrue(all(item['hashes_verified'] for item in result))
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((self.runtime / 'backend_files' / relative).read_bytes()).hexdigest(), digest)
        self.assert_sources_unchanged(original, expected)

    def test_copy_never_overwrites_existing_file_or_changes_sources(self):
        original, expected = self.private_sources()
        collision = self.runtime / 'backend_files/media/nested/synthetic-00.bin'
        self.write(collision, b'Preserve this independently existing target')
        before = hashlib.sha256(collision.read_bytes()).hexdigest()
        try:
            with self.assertRaises(FileExistsError):
                TOOL.copy_private_files(self.backup, self.runtime)
        finally:
            self.remember_created(self.runtime)
        self.assertEqual(hashlib.sha256(collision.read_bytes()).hexdigest(), before)
        self.assert_sources_unchanged(original, expected)

    def test_copy_rejects_symlink_sources_without_dereferencing_private_content(self):
        original, expected = self.private_sources()
        try:
            with patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
                TOOL.copy_private_files(self.backup, self.runtime)
        finally:
            self.remember_created(self.runtime)
        self.assert_sources_unchanged(original, expected)

    def test_generated_settings_and_runner_compile_without_running_services(self):
        origins = ['http://127.0.0.2:49124', 'http://192.168.100.19:49125']
        settings = TOOL.generated_settings(self.runtime / 'backend_files', 57647, origins, 'skilly-fixture')
        generated = ast.parse(settings)
        compile(generated, 'generated_settings', 'exec')
        assignments = {node.targets[0].id: node.value for node in generated.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
        self.assertEqual(assignments['EMAIL_BACKEND'].value, 'django.core.mail.backends.locmem.EmailBackend')
        for name in ('CORS_ALLOWED_ORIGINS', 'CSRF_TRUSTED_ORIGINS'):
            self.assertEqual(ast.literal_eval(assignments[name]), origins)
        self.assertNotIn(self.canary, settings)
        for port, identity_name in [(49123, 'backend_ready.json'), (49126, 'backend_ready_2.json')]:
            runner = TOOL.generated_runner(port, identity_name, [('127.0.0.1', 57647), ('127.0.0.1', 52893)])
            compile(ast.parse(runner), 'generated_runner', 'exec')
            self.assertIn('from config.wsgi import application', runner)
            self.assertNotIn('/__isolated/', runner)
            self.assertNotIn(self.canary, runner)

    def test_lan_host_accepts_only_exact_private_ipv4_interface(self):
        for host in ('192.168.100.19', '10.1.2.3', '172.16.1.2'):
            self.assertEqual(TOOL.lan_host(host), host)
        for host in ('0.0.0.0', '127.0.0.2', '8.8.8.8', '169.254.1.2', '192.168.100.019', 'localhost', '::1', '192.168.1.2.example.invalid'):
            with self.subTest(kind='invalid_lan'), self.assertRaises(ValueError):
                TOOL.lan_host(host)
        calls = []
        with patch.object(TOOL.socket, 'socket', return_value=BoundSocket(calls, 49125)):
            self.assertEqual(TOOL.free_port(49125, host='192.168.100.19'), 49125)
        self.assertEqual([value for kind, value in calls if kind == 'bind'], [('192.168.100.19', 49125)])

    def test_cache_private_context_preserves_secret_and_uses_unique_shared_namespace(self):
        file = self.backup / 'conexion_cache_privada.json'
        self.write_json(file, {'host': '127.0.0.1', 'port': 52893, 'password': self.canary, 'prefix': 'skilly-fixture'})
        cache = TOOL.cache_configuration(str(file), self.backup, self.runtime, 57647)
        self.assertEqual(cache['host'], '127.0.0.1')
        self.assertEqual(cache['port'], 52893)
        self.assertEqual(cache['database'], 15)
        self.assertTrue(cache['key_prefix'].startswith('skilly-local-'))
        self.assertLessEqual(len(cache['key_prefix']), 64)
        other = self.directory(self.backup / 'local_activo_other')
        other_cache = TOOL.cache_configuration(str(file), self.backup, other, 57647)
        self.assertNotEqual(cache['key_prefix'], other_cache['key_prefix'])
        self.assertEqual(json.loads(file.read_text())['password'], self.canary)

    def test_realistic_cache_prefix_and_runtime_produce_namespace_within_64_characters(self):
        file = self.backup / 'cache_namespace.json'
        self.write_json(file, {'host': '127.0.0.1', 'port': 52893, 'password': self.canary, 'prefix': 'skilly-lab-' + 'a' * 32})
        cache = TOOL.cache_configuration(str(file), self.backup, self.runtime, 57647)
        self.assertLessEqual(len(cache['key_prefix']), 64)
        self.assertEqual(cache['key_prefix'], TOOL.cache_configuration(str(file), self.backup, self.runtime, 57647)['key_prefix'])

    def test_two_workers_require_shared_cache_and_reject_local_memory(self):
        self.assertEqual(TOOL.validate_worker_count(1, None), 1)
        self.assertEqual(TOOL.validate_worker_count(2, {'location': 'redis://127.0.0.1:52893/15'}), 2)
        for count, cache in [(2, None), (2, {'location': 'locmem'}), (2, {}), (3, {'location': 'redis://127.0.0.1:52893/15'}), (True, None)]:
            with self.subTest(count=count), self.assertRaises(ValueError):
                TOOL.validate_worker_count(count, cache)

    def test_cache_rejects_remote_host_original_ports_foreign_file_and_invalid_password(self):
        file = self.backup / 'cache_privada.json'
        baseline = {'host': '127.0.0.1', 'port': 52893, 'password': self.canary, 'prefix': 'skilly-fixture'}
        for change in ({'host': '192.168.100.19'}, {'host': 'localhost'}, {'port': 8000}, {'port': 5432}, {'port': 57647},
                       {'password': ''}, {'password': self.canary + '\n'}, {'prefix': 'invalid/prefix'}):
            self.write_json(file, {**baseline, **change})
            with self.subTest(fields=list(change)), self.assertRaises(ValueError):
                TOOL.cache_configuration(str(file), self.backup, self.runtime, 57647)
        foreign = self.scratch / 'outside_cache.json'
        self.write_json(foreign, baseline)
        with self.assertRaises(ValueError):
            TOOL.cache_configuration(str(foreign), self.backup, self.runtime, 57647)

    def test_generated_guard_permits_only_copy_database_and_exact_loopback_cache(self):
        allowed = [('127.0.0.1', 57647), ('127.0.0.1', 52893)]
        syntax = ast.parse(TOOL.generated_runner(49123, 'backend_ready.json', allowed))
        guard = next(node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name == 'guarded')
        calls = []
        namespace = {'ALLOWED_OUTBOUND': allowed, 'original_connect': lambda sock, address: calls.append(address)}
        exec(compile(ast.Module(body=[guard], type_ignores=[]), 'network_guard_only', 'exec'), namespace)
        for address in allowed:
            namespace['guarded'](None, address)
        self.assertEqual(calls, allowed)
        for address in [('127.0.0.1', 5432), ('127.0.0.1', 8000), ('127.0.0.1', 52894), ('192.168.100.19', 52893), ('webpay3gint.transbank.cl', 443)]:
            with self.subTest(kind='blocked_destination'), self.assertRaises(OSError):
                namespace['guarded'](None, address)
        self.assertEqual(calls, allowed)

    def test_reuse_private_runtime_does_not_copy_or_replace_files(self):
        self.write(self.runtime / 'backend_files/media/new-upload.bin', self.canary.encode())
        self.write(self.runtime / 'backend_files/entregas_privadas_e3/new-delivery.bin', self.canary.encode())
        target = self.directory(self.backup / 'local_activo_replacement')
        with patch.object(TOOL, 'copy_private_files', side_effect=AssertionError('No recopy expected')):
            private, report, previous = TOOL.private_root_for(self.backup, target, str(self.context_path), 57647)
        self.assertEqual(private, self.runtime / 'backend_files')
        self.assertEqual(report[0]['files_copied'], 0)
        self.assertEqual(previous['run_dir'], str(self.runtime))
        self.assertFalse((target / 'backend_files').exists())
        self.assertEqual((private / 'media/new-upload.bin').read_bytes(), self.canary.encode())

    def test_closed_context_reuses_private_files_after_explicit_owned_shutdown(self):
        self.write(self.runtime / 'backend_files/media/new-upload.bin', self.canary.encode())
        self.write(self.runtime / 'backend_files/entregas_privadas_e3/new-delivery.bin', self.canary.encode())
        self.write(self.runtime / 'stop.flag', b'Owned stop')
        self.write_json(self.runtime / 'cierre.json', {'own_children_closed': True, 'own_cluster_stopped': True, 'other_processes_touched': False})
        target = self.directory(self.backup / 'local_activo_after_shutdown')
        context, closed = TOOL.reuse_context_details(str(self.context_path))
        self.assertTrue(closed)
        self.assertEqual(context['run_dir'], str(self.runtime))
        with patch.object(TOOL, 'copy_private_files', side_effect=AssertionError('No recopy expected')):
            private, report, _previous = TOOL.private_root_for(self.backup, target, str(self.context_path), 57647)
        self.assertEqual(private, self.runtime / 'backend_files')
        self.assertEqual(report[0]['files_copied'], 0)
        self.assertEqual((private / 'media/new-upload.bin').read_bytes(), self.canary.encode())

    def test_closed_context_requires_both_marker_and_successful_owned_closure(self):
        self.write(self.runtime / 'stop.flag', b'Owned stop')
        with self.assertRaises(ValueError):
            TOOL.reuse_context_details(str(self.context_path))
        for closure in ({'own_children_closed': False, 'other_processes_touched': False},
                        {'own_children_closed': True, 'other_processes_touched': True}):
            self.write_json(self.runtime / 'cierre.json', closure)
            with self.subTest(kind='incomplete_shutdown'), self.assertRaises(ValueError):
                TOOL.reuse_context_details(str(self.context_path))

    def test_two_workers_have_distinct_process_identities_and_public_cache_metadata(self):
        secondary = self.runtime / 'backend_ready_2.json'
        self.context['backend_workers'] = [
            {'origin': self.context['backend_origin'], 'pid': self.context['backend_pid'], 'source_identity_file': str(self.identity_path)},
            {'origin': 'http://127.0.0.2:49126', 'pid': 12126, 'source_identity_file': str(secondary)},
        ]
        self.context['access_cache'] = {'host': '127.0.0.1', 'port': 52893, 'database': 15, 'key_prefix': 'skilly-fixture:local_activo'}
        self.context.update(frontend_lan_host='192.168.100.19', frontend_lan_origin='http://192.168.100.19:49125')
        self.write_json(secondary, {**self.identity, 'pid': 12126})
        self.save_context()
        result = self.invoke()
        self.assertEqual(len(result['backend_workers']), 2)
        self.assertTrue(all(item['product_sources_current'] for item in result['backend_workers']))
        self.assertEqual(result['frontend_lan'], self.context['frontend_lan_origin'])
        self.assertNotIn('password', json.dumps(result))
        self.assertNotIn(self.canary, json.dumps(result))
        self.context['access_cache']['password'] = self.canary
        self.save_context()
        with self.assertRaises(ValueError):
            TOOL.context_from(self.context_path)

    def test_cli_corrupt_private_json_never_prints_canary_fragment_or_stack(self):
        self.write(self.context_path, ('{"password":"' + self.canary).encode())
        child = subprocess.run([sys.executable, '-B', str(TOOL_PATH), 'estado', '--contexto', str(self.context_path)], capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(child.returncode, 1)
        self.assertEqual(child.stderr, '')
        self.assertNotIn(self.canary, child.stdout)
        self.assertNotIn('password', child.stdout)
        result = json.loads(child.stdout)
        self.assertFalse(result['completed'])
        self.assertNotIn('stack', result)


if __name__ == '__main__':
    unittest.main()
