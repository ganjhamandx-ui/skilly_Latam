"""Identidades y cierre offline: no inicia ni termina procesos reales."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('_worker_launcher_tested', Path(__file__).resolve().parents[1] / 'entorno_local_skilly.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class FakePsutilError(Exception):
    pass


class FakeNoSuchProcess(FakePsutilError):
    pass


class FakeTimeout(FakePsutilError):
    pass


class WorkerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='skilly-worker-identity-')
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name) / 'local_activo_fixture'
        self.run.mkdir()
        self.file = self.run / 'backend_local.py'
        self.file.write_text('# fixture only\n', encoding='utf-8')
        self.parent = self.candidate(101, started=100)
        self.child = self.candidate(102, started=101)
        self.supervisor = self.candidate(100, started=90)
        self.parent.children.return_value = [self.child]
        self.launcher = Mock(pid=101)
        self.launcher.poll.return_value = None
        self.module = SimpleNamespace(Process=Mock(side_effect=lambda pid: self.supervisor if pid == TOOL.os.getpid() else self.parent), Error=FakePsutilError,
                                      NoSuchProcess=FakeNoSuchProcess, TimeoutExpired=FakeTimeout)
        self.patch = patch.dict(sys.modules, {'psutil': self.module})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def candidate(self, pid, started):
        candidate = Mock(pid=pid)
        candidate.is_running.return_value = True
        candidate.create_time.return_value = started
        candidate.exe.return_value = TOOL.sys.executable
        candidate.cwd.return_value = str(TOOL.ROOT / 'backend')
        candidate.cmdline.return_value = [TOOL.sys.executable, '-B', str(self.file)]
        candidate.children.return_value = []
        return candidate

    def identity(self, pid):
        return {'pid': pid, 'project_root': str(TOOL.ROOT), 'wsgi_file': str(TOOL.ROOT / 'backend/config/wsgi.py')}

    def test_pid_directo_valido_se_conserva(self):
        self.assertIs(TOOL.validar_worker_identity(self.launcher, self.file, self.identity(101)), self.parent)

    def test_interprete_hijo_windows_valido_no_se_confunde_con_wrapper(self):
        self.assertIs(TOOL.validar_worker_identity(self.launcher, self.file, self.identity(102)), self.child)
        self.parent.children.assert_called_once_with(recursive=True)

    def test_alias_windows_store_admite_solo_imagen_real_del_supervisor(self):
        image = str(self.run / 'installed/python3.13.exe')
        self.supervisor.exe.return_value = image
        self.child.exe.return_value = image
        with patch.object(TOOL.sys, '_base_executable', str(self.run / 'alias/python.exe'), create=True):
            self.assertIs(TOOL.validar_worker_identity(self.launcher, self.file, self.identity(102)), self.child)

    def test_otro_python_ajeno_no_se_admite_aunque_su_argv_parezca_runner(self):
        self.child.exe.return_value = str(self.run / 'other/python3.11.exe')
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, self.identity(102))

    def test_pid_ajeno_o_ruta_distinta_no_se_acepta(self):
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, self.identity(999))
        self.child.cmdline.return_value = [TOOL.sys.executable, '-B', str(self.run / 'different.py')]
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, self.identity(102))
        self.child.terminate.assert_not_called()

    def test_interprete_anterior_o_launcher_terminado_no_suplanta_identidad(self):
        self.child.create_time.return_value = 99
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, self.identity(102))
        self.launcher.poll.return_value = 0
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, self.identity(101))
        self.assertFalse(TOOL.close_owned_workers([(self.launcher, self.file)]))

    def test_manifiesto_de_otra_raiz_se_rechaza_antes_de_buscar_procesos(self):
        identity = self.identity(102)
        identity['project_root'] = str(self.run)
        with self.assertRaises(ValueError):
            TOOL.validar_worker_identity(self.launcher, self.file, identity)
        self.module.Process.assert_not_called()

    def test_cierre_parcial_sin_ready_solo_termina_hijo_del_runner_propio(self):
        unrelated = self.candidate(103, 101)
        unrelated.cmdline.return_value = [TOOL.sys.executable, '-B', str(self.run / 'unrelated.py')]
        self.parent.children.return_value = [self.child, unrelated]
        self.assertTrue(TOOL.close_owned_workers([(self.launcher, self.file)]))
        self.child.terminate.assert_called_once()
        self.child.wait.assert_called_once_with(timeout=10)
        unrelated.terminate.assert_not_called()
        self.parent.terminate.assert_not_called()  # Lo hace el handle Popen original.

    def test_cierre_no_afirma_exito_si_no_puede_verificar_el_arbol(self):
        self.parent.children.side_effect = FakePsutilError('private canary not logged')
        self.assertFalse(TOOL.close_owned_workers([(self.launcher, self.file)]))
        self.child.terminate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
