"""Guardias sin PostgreSQL, Android, procesos ni conexiones reales."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('_android_runtime', Path(__file__).resolve().parents[1] / 'entorno_android_skilly.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class SharedDatabaseMarker:
    """Imita solo la consulta al catalogo compartido, sin SQL generico permisivo."""
    def __init__(self, database):
        self.database, self.queries = database, []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, parameters):
        expected = "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s"
        if query != expected or parameters != [self.database]:
            raise AssertionError('El comentario de una BD requiere shobj_description del catalogo compartido')
        self.queries.append(query)
        # Sin marcador: el flujo debe cerrarse antes de iniciar, respaldar o borrar.
        return SimpleNamespace(fetchone=lambda: (None,))


class AndroidRuntimeGuardTests(unittest.TestCase):
    def resume_fixture(self, temporary):
        base = Path(temporary)
        root = base / 'project'
        root.mkdir()
        backup = base / 'SKILLY_recuperacion_synthetic'
        run = backup / ('android_aislado_' + 'a' * 20)
        run.mkdir(parents=True)
        node = backup / 'node/node.exe'
        node.parent.mkdir()
        node.write_bytes(b'synthetic-not-executable')
        ctx = {'run_id': run.name, 'run_dir': str(run), 'backup_root': str(backup),
               'database_name': 'skilly_android_' + 'a' * 20, 'restore_completed': True, 'isolated': True,
               'backend_pid': 111, 'backend_launcher_pid': 112, 'frontend_pid': 113, 'supervisor_pid': 114,
               'backend_port': 63594, 'frontend_port': 63595, 'backend_origin': 'http://127.0.0.1:63594',
               'frontend_origin': 'http://localhost:63595', 'node': str(node),
               'node_sha256': hashlib.sha256(node.read_bytes()).hexdigest(),
               'preserved_services_sha256': hashlib.sha256(b'synthetic-services').hexdigest()}
        (run / 'cierre.json').write_text(json.dumps({'own_children_closed': True}), encoding='utf-8')
        (run / 'backend_ready.json').write_text(json.dumps({'pid': 111, 'project_root': str(root),
            'wsgi_file': str(root / 'backend/config/wsgi.py')}), encoding='utf-8')
        (run / 'android_settings.py').write_text(TOOL.settings_source(ctx), encoding='utf-8')
        (run / 'fixture_privado.json').write_text(json.dumps({'run_id': run.name,
            'origin': ctx['frontend_origin'], 'backend_origin': ctx['backend_origin']}), encoding='utf-8')
        (run / 'contexto.json').write_text(json.dumps(ctx), encoding='utf-8')
        (run / 'stop.flag').write_text('synthetic-stop', encoding='utf-8')
        return ctx, root, run

    def test_database_name_rejects_existing_and_ambiguous_names(self):
        self.assertTrue(TOOL.valid_database_name('skilly_android_' + 'a' * 20))
        for value in ('skilly', 'postgres', 'skilly_cu040_pruebas', 'skilly_android_', 'skilly_android_' + 'x' * 20,
                      'skilly_android_' + 'a' * 20 + ';DROP DATABASE skilly', None):
            self.assertFalse(TOOL.valid_database_name(value))

    def test_cleanup_rejects_operational_database_before_connecting(self):
        with patch.object(TOOL, 'admin_connection', side_effect=AssertionError('No database expected')):
            with self.assertRaises(ValueError):
                TOOL.cleanup({'database_name': 'skilly', 'run_id': 'android_aislado_' + 'a' * 20})

    def test_cleanup_rejects_other_run_identity(self):
        with patch.object(TOOL, 'admin_connection', side_effect=AssertionError('No database expected')):
            with self.assertRaises(ValueError):
                TOOL.cleanup({'database_name': 'skilly_android_' + 'a' * 20,
                              'run_id': 'android_aislado_' + 'b' * 20})

    def test_generated_settings_compile_and_preserve_isolated_tuple(self):
        ctx = {'database_name': 'skilly_android_' + 'a' * 20, 'run_id': 'android_aislado_' + 'a' * 20,
               'run_dir': 'C:/synthetic/AndroidRun'}
        source = TOOL.settings_source(ctx)
        ast.parse(source)
        self.assertIn(repr((ctx['database_name'], 'skilly_app', TOOL.HOST, '57647')), source)
        self.assertIn('locmem.EmailBackend', source)
        self.assertNotIn('csrf_exempt', source)
        self.assertNotIn('__isolated', source)

    def test_environment_retargets_only_new_database_and_uses_explicit_proxy(self):
        ctx = {'app_file': 'synthetic-config.env', 'database_name': 'skilly_android_' + 'a' * 20,
               'run_dir': 'C:/synthetic/AndroidRun', 'frontend_origin': 'http://localhost:55001',
               'backend_origin': 'http://127.0.0.1:55002'}
        cfg = {'POSTGRES_DB': 'skilly', 'POSTGRES_SCHEMA': 'skilly', 'POSTGRES_USER': 'skilly_app',
               'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '57647', 'POSTGRES_PASSWORD': 'synthetic-test-only'}
        with patch('dotenv.dotenv_values', return_value=cfg):
            result = TOOL.environment(ctx)
        self.assertEqual(result['POSTGRES_DB'], ctx['database_name'])
        self.assertEqual(result['SKILLY_API_PROXY_TARGET'], ctx['backend_origin'])
        self.assertEqual(cfg['POSTGRES_DB'], 'skilly')

    def test_environment_rejects_original_port_or_other_role(self):
        for port, role in [('5432', 'skilly_app'), ('57647', 'postgres')]:
            cfg = {'POSTGRES_DB': 'skilly', 'POSTGRES_SCHEMA': 'skilly', 'POSTGRES_USER': role,
                   'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': port}
            with patch('dotenv.dotenv_values', return_value=cfg):
                with self.assertRaises(ValueError):
                    TOOL.environment({'app_file': 'synthetic.env'})

    def test_context_is_bound_to_its_run_and_external_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            backup = Path(temporary) / 'SKILLY_recuperacion_synthetic'
            run = backup / ('android_aislado_' + 'a' * 20)
            cluster = backup / 'ensayo_aislado_synthetic' / 'cluster'
            run.mkdir(parents=True)
            cluster.mkdir(parents=True)
            files = {}
            for name in ('admin_file', 'app_file', 'source_dump'):
                file = backup / name
                file.write_text('synthetic', encoding='utf-8')
                files[name] = str(file)
            ctx = {'project_root': str(TOOL.ROOT), 'run_dir': str(run), 'backup_root': str(backup),
                   'run_id': run.name, 'database_name': 'skilly_android_' + 'a' * 20,
                   'database_port': 57647, 'cluster': str(cluster), **files}
            file = run / 'contexto.json'
            file.write_text(json.dumps(ctx), encoding='utf-8')
            self.assertEqual(TOOL.context_from(file)['database_name'], ctx['database_name'])
            ctx['database_name'] = 'skilly'
            file.write_text(json.dumps(ctx), encoding='utf-8')
            with self.assertRaises(ValueError):
                TOOL.context_from(file)

    def test_free_port_uses_exclusive_bind_and_skips_forbidden(self):
        from types import SimpleNamespace
        calls, sockets = [], []
        class FakeSocket:
            def __init__(self):
                self.port = [8000, 55771][len(sockets)]
                sockets.append(self)
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def setsockopt(self, *args): calls.append(('option', args))
            def bind(self, address): calls.append(('bind', address))
            def getsockname(self): return ('127.0.0.1', self.port)
            def connect(self, *args): raise AssertionError('No network probe expected')
        with patch.object(TOOL.socket, 'socket', side_effect=FakeSocket):
            self.assertEqual(TOOL.free_port(), 55771)
        self.assertEqual([value for kind, value in calls if kind == 'bind'], [('127.0.0.1', 0)] * 2)

    def test_resume_rejects_live_previous_process_before_ports_or_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, root, _ = self.resume_fixture(temporary)
            fake_psutil = SimpleNamespace(pid_exists=Mock(return_value=True))
            with patch.object(TOOL, 'ROOT', root), patch.dict('sys.modules', {'psutil': fake_psutil}), \
                    patch.object(TOOL, 'admin_connection') as database, patch.object(TOOL, 'available_context_ports') as ports:
                with self.assertRaises(ValueError):
                    TOOL.resume_guards(ctx)
            database.assert_not_called()
            ports.assert_not_called()

    def test_resume_uses_same_fixture_and_database_without_seed_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, _, run = self.resume_fixture(temporary)
            fixture_before = (run / 'fixture_privado.json').read_bytes()
            settings_before = (run / 'android_settings.py').read_bytes()
            with patch.object(TOOL, 'resume_guards'), patch.object(TOOL, 'serve_services') as serve, \
                    patch.object(TOOL, 'close_runtime') as close, \
                    patch.object(TOOL, 'seed', side_effect=AssertionError('Never seed on resume')), \
                    patch.object(TOOL, 'pg_command', side_effect=AssertionError('Never restore on resume')):
                TOOL.resume(ctx)
            self.assertEqual(serve.call_args.args[0]['database_name'], 'skilly_android_' + 'a' * 20)
            self.assertEqual(serve.call_args.args[0]['resume_count'], 1)
            self.assertEqual((run / 'fixture_privado.json').read_bytes(), fixture_before)
            self.assertEqual((run / 'android_settings.py').read_bytes(), settings_before)
            self.assertFalse((run / 'stop.flag').exists())
            self.assertFalse((run / 'reanudar.lock').exists())
            archive = Path(ctx['last_resume_archive'])
            self.assertEqual((archive / 'stop.flag').read_text(), 'synthetic-stop')
            self.assertTrue((archive / 'cierre.json').is_file())
            self.assertTrue((archive / 'backend_ready.json').is_file())
            self.assertTrue((archive / 'contexto_previo.json').is_file())
            close.assert_called_once()

    def test_resume_validates_marker_app_identity_and_preserved_services_readonly(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, root, _ = self.resume_fixture(temporary)
            fake_psutil = SimpleNamespace(pid_exists=Mock(return_value=False))
            admin, app = Mock(), Mock()
            admin.__enter__ = Mock(return_value=admin)
            admin.__exit__ = Mock(return_value=False)
            admin.execute.return_value.fetchone.return_value = ('skilly_android:' + ctx['run_id'],)
            app.__enter__ = Mock(return_value=app)
            app.__exit__ = Mock(return_value=False)
            env = {'POSTGRES_USER': 'skilly_app', 'POSTGRES_PASSWORD': 'synthetic-test-only'}
            fake_connect = Mock(return_value=app)
            with patch.object(TOOL, 'ROOT', root), patch.dict('sys.modules', {
                    'psutil': fake_psutil, 'psycopg': SimpleNamespace(connect=fake_connect)}), \
                    patch.object(TOOL, 'available_context_ports'), patch.object(TOOL, 'check_cluster'), \
                    patch.object(TOOL, 'environment', return_value=env), patch.object(TOOL, 'admin_connection', return_value=admin):
                for identity in ((ctx['database_name'], 'skilly', 'skilly_app', 57647),
                                 ('skilly', 'skilly', 'skilly_app', 57647),
                                 (ctx['database_name'], 'public', 'skilly_app', 57647),
                                 (ctx['database_name'], 'skilly', 'postgres', 57647)):
                    app.execute.side_effect = [SimpleNamespace(fetchone=lambda: identity), [('synthetic-services',)]]
                    if identity[0] == ctx['database_name'] and identity[1:3] == ('skilly', 'skilly_app'):
                        TOOL.resume_guards(ctx)
                    else:
                        with self.assertRaises(ValueError):
                            TOOL.resume_guards(ctx)
            self.assertIn('default_transaction_read_only=on', fake_connect.call_args.kwargs['options'])

    def test_resume_checks_database_comment_with_shared_catalog_function(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, root, _ = self.resume_fixture(temporary)
            marker = SharedDatabaseMarker(ctx['database_name'])
            fake_psutil = SimpleNamespace(pid_exists=Mock(return_value=False))
            with patch.object(TOOL, 'ROOT', root), patch.dict('sys.modules', {'psutil': fake_psutil}), \
                    patch.object(TOOL, 'available_context_ports'), patch.object(TOOL, 'check_cluster'), \
                    patch.object(TOOL, 'admin_connection', return_value=marker), \
                    patch.object(TOOL, 'environment', side_effect=AssertionError('Missing marker must prevent app connection')):
                with self.assertRaises(ValueError):
                    TOOL.resume_guards(ctx)
            self.assertEqual(len(marker.queries), 1)

    def test_cleanup_checks_database_comment_with_shared_catalog_before_snapshot_or_drop(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, _, run = self.resume_fixture(temporary)
            marker = SharedDatabaseMarker(ctx['database_name'])
            fake_psutil = SimpleNamespace(pid_exists=Mock(return_value=False))
            with patch.dict('sys.modules', {'psutil': fake_psutil, 'psycopg': SimpleNamespace(sql=object())}), \
                    patch.object(TOOL, 'check_cluster'), patch.object(TOOL, 'admin_connection', return_value=marker), \
                    patch.object(TOOL, 'pg_command', side_effect=AssertionError('Missing marker must prevent snapshot')):
                with self.assertRaises(ValueError):
                    TOOL.cleanup(ctx)
            self.assertEqual(len(marker.queries), 1)
            self.assertFalse((run / 'datos_android_antes_retirada.dump').exists())

    def test_same_ports_checked_without_connecting_to_other_services(self):
        sockets, binds = [], []
        class FakeSocket:
            def __init__(self): sockets.append(self)
            def setsockopt(self, *args): pass
            def bind(self, address): binds.append(address)
            def close(self): self.closed = True
            def connect(self, address): raise AssertionError('No HTTP or service connection')
        ctx = {'backend_port': 63594, 'frontend_port': 63595,
               'backend_origin': 'http://127.0.0.1:63594', 'frontend_origin': 'http://localhost:63595'}
        with patch.object(TOOL.socket, 'socket', side_effect=FakeSocket):
            TOOL.available_context_ports(ctx)
        self.assertEqual(binds, [('127.0.0.1', 63594), ('127.0.0.1', 63595)])
        self.assertTrue(all(item.closed for item in sockets))
        with patch.object(TOOL.socket, 'socket', side_effect=AssertionError('Forbidden port')):
            with self.assertRaises(ValueError):
                TOOL.available_context_ports({**ctx, 'backend_port': 8000})

    def test_source_manifest_includes_new_untracked_product_python_excludes_venv_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('backend/config/identidad_bancaria.py', 'backend/.venv/ignored.py',
                         'backend/__pycache__/ignored.py', 'backend/config/test_ignored.py'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'synthetic')
            with patch.object(TOOL, 'ROOT', root):
                manifest = TOOL.backend_sources()
            self.assertEqual(list(manifest), [str(Path('backend/config/identidad_bancaria.py'))])


if __name__ == '__main__':
    unittest.main()
