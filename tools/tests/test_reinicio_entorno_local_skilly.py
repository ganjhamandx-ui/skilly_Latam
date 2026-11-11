"""Recuperacion de launcher: procesos, PostgreSQL y sockets siempre simulados."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('_restart_launcher_tested', Path(__file__).resolve().parents[1] / 'entorno_local_skilly.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class FakeProcessError(Exception):
    pass


class FakeNoSuchProcess(FakeProcessError):
    pass


class StopBeforeDatabase(Exception):
    pass


class RestartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='skilly-restart-')
        self.addCleanup(self.temp.cleanup)
        self.backup = Path(self.temp.name) / 'SKILLY_recuperacion_fixture'
        self.run = self.backup / 'local_activo_previous'
        self.run.mkdir(parents=True)
        self.file = self.run / 'contexto.json'
        self.canary = secrets.token_hex(32)
        self.context = {
            'project_root': str(TOOL.ROOT), 'run_dir': str(self.run), 'backup_root': str(self.backup),
            'host': TOOL.HOST, 'backend_origin': 'http://127.0.0.2:49123',
            'frontend_origin': 'http://127.0.0.2:49124', 'database_port': 57647,
            'isolated_database': True, 'source_identity_file': str(self.run / 'backend_ready.json'),
            'backend_pid': 101, 'frontend_pid': 102, 'supervisor_pid': 103, 'system_boot_time': 900,
        }
        self.save()
        self.module = SimpleNamespace(boot_time=Mock(return_value=1000),
            Process=Mock(side_effect=FakeNoSuchProcess), Error=FakeProcessError, NoSuchProcess=FakeNoSuchProcess)
        patcher = patch.dict(sys.modules, {'psutil': self.module})
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self):
        self.file.write_text(json.dumps(self.context), encoding='utf-8')

    def recovery(self):
        return TOOL.reuse_context_details(self.file, after_restart=True)

    def private_files(self):
        media = self.run / 'backend_files/media/new-upload.bin'
        delivery = self.run / 'backend_files/entregas_privadas_e3/new-delivery.bin'
        for file in (media, delivery):
            file.parent.mkdir(parents=True)
            file.write_bytes(self.canary.encode())
        return media, delivery

    def test_new_boot_checks_every_previous_pid_without_altering_context(self):
        self.context.update(frontend_lan_pid=104)
        self.save()
        (self.run / 'startup.json').write_text(json.dumps({'project_root': str(TOOL.ROOT), 'launcher_pids': [105, 106, 102, 104]}), encoding='utf-8')
        before = self.file.read_bytes()
        context, closed = self.recovery()
        report = context['restart_recovery']
        self.assertFalse(closed)
        self.assertTrue(report['system_restart_confirmed'])
        self.assertEqual(report['confirmation_source'], 'recorded_system_boot_time')
        self.assertEqual([r['pid'] for r in report['previous_processes']], [101, 102, 103, 104, 105, 106])
        self.assertTrue(all(r['state'] == 'absent' for r in report['previous_processes']))
        self.assertFalse(report['processes_terminated'])
        self.assertEqual(self.file.read_bytes(), before)
        self.assertNotIn(self.canary, json.dumps(report))

    def test_same_boot_does_not_authorize_recovery_even_when_all_pids_are_gone(self):
        self.context['system_boot_time'] = 1000
        self.save()
        with self.assertRaises(TOOL.RestartRecoveryError) as error:
            self.recovery()
        self.assertEqual(error.exception.reason, 'system_restart_not_confirmed')
        self.module.Process.assert_not_called()

    def test_invalid_or_future_previous_boot_cannot_hide_live_processes(self):
        for value in (1001, float('nan'), -1, True, '900'):
            self.context['system_boot_time'] = value
            self.save()
            with self.subTest(value_type=type(value).__name__), self.assertRaises(TOOL.RestartRecoveryError):
                self.recovery()
        self.module.Process.assert_not_called()

    def test_legacy_context_uses_original_file_time_not_a_new_pointer(self):
        del self.context['system_boot_time']
        self.save()
        os.utime(self.file, (950, 950))
        context, _closed = self.recovery()
        self.assertEqual(context['restart_recovery']['confirmation_source'], 'original_context_mtime_before_current_boot')
        os.utime(self.file, (1001, 1001))
        with self.assertRaises(TOOL.RestartRecoveryError) as error:
            self.recovery()
        self.assertEqual(error.exception.reason, 'system_restart_not_confirmed')

    def test_reused_pid_is_left_untouched_without_reading_its_private_command(self):
        process = Mock()
        process.create_time.return_value = 1003
        process.cmdline.side_effect = AssertionError('Do not read foreign process arguments')
        self.module.Process.side_effect = None
        self.module.Process.return_value = process
        context, _closed = self.recovery()
        self.assertTrue(all(r['state'] == 'pid_reused_after_restart_left_untouched' for r in context['restart_recovery']['previous_processes']))
        process.cmdline.assert_not_called()
        process.terminate.assert_not_called()
        process.kill.assert_not_called()

    def test_process_predating_claimed_boot_blocks_and_is_never_terminated(self):
        process = Mock()
        process.create_time.return_value = 990
        self.module.Process.side_effect = None
        self.module.Process.return_value = process
        with self.assertRaises(TOOL.RestartRecoveryError) as error:
            self.recovery()
        self.assertEqual(error.exception.reason, 'previous_process_not_proven_absent')
        process.terminate.assert_not_called()
        process.kill.assert_not_called()

    def test_permission_failure_does_not_leak_raw_error_or_assume_absence(self):
        self.module.Process.side_effect = FakeProcessError(self.canary)
        with self.assertRaises(TOOL.RestartRecoveryError) as error:
            self.recovery()
        self.assertEqual(error.exception.reason, 'previous_process_identity_unavailable')
        self.assertNotIn(self.canary, str(error.exception))

    def test_exit_between_pid_lookup_and_creation_time_is_proven_absent(self):
        process = Mock()
        process.create_time.side_effect = FakeNoSuchProcess
        self.module.Process.side_effect = None
        self.module.Process.return_value = process
        context, _closed = self.recovery()
        self.assertTrue(all(r['state'] == 'absent' for r in context['restart_recovery']['previous_processes']))

    def test_foreign_startup_or_invalid_pid_rejects_recovery(self):
        for value in ({'project_root': str(self.backup), 'launcher_pids': [105]},
                      {'project_root': str(TOOL.ROOT), 'launcher_pids': [True]},
                      {'project_root': str(TOOL.ROOT), 'launcher_pids': '105'}):
            (self.run / 'startup.json').write_text(json.dumps(value), encoding='utf-8')
            with self.subTest(kind='invalid_startup'), self.assertRaises(TOOL.RestartRecoveryError):
                self.recovery()
        self.module.Process.assert_not_called()

    def test_interrupted_shutdown_is_preserved_without_fabricating_success(self):
        marker = self.run / 'stop.flag'
        marker.write_text('Owned shutdown interrupted by restart', encoding='utf-8')
        closure = self.run / 'cierre.json'
        closure.write_text(json.dumps({'own_children_closed': False, 'other_processes_touched': False}), encoding='utf-8')
        before = {file: file.read_bytes() for file in (self.file, marker, closure)}
        with self.assertRaises(ValueError):
            TOOL.reuse_context_details(self.file)
        context, closed = self.recovery()
        self.assertFalse(closed)
        self.assertTrue(context['restart_recovery']['system_restart_confirmed'])
        for file, content in before.items():
            self.assertEqual(file.read_bytes(), content)

    def test_recovery_reuses_new_uploads_without_copying_original_backups(self):
        files = self.private_files()
        target = self.backup / 'local_activo_replacement'
        with patch.object(TOOL, 'copy_private_files', side_effect=AssertionError('Do not recopy old media')):
            private, report, _previous = TOOL.private_root_for(self.backup, target, self.file, 57647, after_restart=True)
        self.assertEqual(private, self.run / 'backend_files')
        self.assertEqual(report[0]['files_copied'], 0)
        self.assertFalse(target.exists())
        self.assertTrue(all(file.read_bytes() == self.canary.encode() for file in files))

    def test_partial_closure_json_after_power_loss_is_not_rewritten_or_trusted(self):
        marker, closure = self.run / 'stop.flag', self.run / 'cierre.json'
        marker.write_text('Owned shutdown interrupted', encoding='utf-8')
        partial = '{"private_canary":"' + self.canary
        closure.write_text(partial, encoding='utf-8')
        context, closed = self.recovery()
        self.assertFalse(closed)
        self.assertFalse(context['restart_recovery']['previous_closure_verified'])
        self.assertEqual(closure.read_text(encoding='utf-8'), partial)
        self.assertNotIn(self.canary, json.dumps(context['restart_recovery']))

    def start_until_database_identity(self, *, recover):
        self.private_files()
        cluster = self.backup / 'ensayo_aislado_fixture/cluster'
        cluster.mkdir(parents=True)
        admin = cluster.parent / 'conexion_aislada.env'
        admin.write_text('# Synthetic fixture only', encoding='utf-8')
        connection = self.backup / 'conexion_privada.env'
        connection.write_text('# Synthetic fixture only', encoding='utf-8')
        pg_bin = self.backup / 'bin'
        pg_bin.mkdir()
        (pg_bin / 'pg_ctl.exe').write_text('Never executed', encoding='utf-8')
        cfg = {'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '57647', 'POSTGRES_DB': 'skilly',
            'POSTGRES_SCHEMA': 'skilly', 'POSTGRES_USER': 'skilly_app', 'POSTGRES_PASSWORD': self.canary}
        dotenv = SimpleNamespace(dotenv_values=lambda file: cfg)
        psycopg = SimpleNamespace(connect=Mock(side_effect=StopBeforeDatabase))
        args = SimpleNamespace(reanudar_tras_reinicio=recover, reutilizar_contexto=str(self.file),
            respaldo=str(self.backup), cluster=str(cluster), conexion=str(connection), admin=str(admin),
            cache_contexto=None, cache_db=15, workers=1, backend_port=49123, backend2_port=0,
            frontend_port=49124, frontend_lan_host=None, frontend_lan_port=0, pg_bin=str(pg_bin), node='not-used')
        transport = Mock(side_effect=lambda command, **kw: SimpleNamespace(returncode=3 if command[-1] == 'status' else 0))
        with patch.dict(sys.modules, {'dotenv': dotenv, 'psycopg': psycopg}), \
                patch.object(TOOL, 'free_port', side_effect=[49123, 49124]), \
                patch.object(TOOL.subprocess, 'run', transport), \
                patch.object(TOOL.subprocess, 'Popen', side_effect=AssertionError('No service process may be started')):
            with self.assertRaises(StopBeforeDatabase if recover else ValueError):
                TOOL.start(args)
        return transport, psycopg

    def test_verified_restart_allows_same_cluster_start_then_requires_database_identity(self):
        transport, psycopg = self.start_until_database_identity(recover=True)
        commands = [call.args[0] for call in transport.call_args_list]
        self.assertEqual([command[-1] for command in commands], ['status', 'start', 'stop'])
        self.assertTrue(all(command[2] == str(self.backup / 'ensayo_aislado_fixture/cluster') for command in commands))
        psycopg.connect.assert_called_once()
        self.assertEqual(psycopg.connect.call_args.kwargs['port'], 57647)
        self.assertEqual(list(self.backup.glob('local_activo_*/backend_files/media')), [self.run / 'backend_files/media'])

    def test_existing_default_does_not_restart_cluster_for_an_unclosed_context(self):
        transport, psycopg = self.start_until_database_identity(recover=False)
        self.assertEqual([call.args[0][-1] for call in transport.call_args_list], ['status'])
        psycopg.connect.assert_not_called()

    def test_restart_flag_requires_an_explicit_previous_context_before_any_start(self):
        with patch.dict(sys.modules, {'dotenv': SimpleNamespace(dotenv_values=Mock()), 'psycopg': SimpleNamespace(connect=Mock())}), \
                patch.object(TOOL.subprocess, 'run') as transport:
            with self.assertRaises(TOOL.RestartRecoveryError) as error:
                TOOL.start(SimpleNamespace(reanudar_tras_reinicio=True, reutilizar_contexto=None))
        self.assertEqual(error.exception.reason, 'restart_recovery_requires_previous_context')
        transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()
