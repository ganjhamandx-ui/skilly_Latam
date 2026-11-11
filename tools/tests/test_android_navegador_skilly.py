import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SPEC = importlib.util.spec_from_file_location('android_navegador_skilly', Path(__file__).resolve().parents[1] / 'android_navegador_skilly.py')
android = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(android)


class AndroidControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        backup = base / 'SKILLY_recuperacion_fixture'
        self.run = backup / 'android_ejecucion_fixture'
        self.run.mkdir(parents=True)
        self.adb = base / 'sdk/platform-tools/adb.exe'
        self.emulator = base / 'sdk/emulator/emulator.exe'
        for file in (self.adb, self.emulator):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'fixture-not-executable')
        self.ctx = {'run_dir': str(self.run), 'launcher_pid': 12345, 'created': 100.,
                    'avd': 'Medium_Phone_API_37.0', 'serial': 'emulator-5554',
                    'adb': str(self.adb), 'emulator': str(self.emulator),
                    'read_only_avd': True, 'memory_mib': 2048, 'cores': 2, 'cdp_port': 52216}
        self.file = self.run / 'contexto_android.json'
        self.file.write_text(json.dumps(self.ctx), encoding='utf-8')
        self.process = Mock()
        self.process.exe.return_value = str(self.emulator)
        self.process.is_running.return_value = True
        self.process.create_time.return_value = 100.
        self.process.cmdline.return_value = [str(self.emulator), '-avd', self.ctx['avd'],
            '-port', '5554', '-memory', '2048', '-cores', '2', '-read-only',
            '-no-snapshot-save', '-no-snapshot-load', '-no-window']

    def test_contexto_solo_admite_avd_de_ensayo_no_telefono_fisico(self):
        _, actual = android.context_from(self.file)
        self.assertEqual(actual['serial'], 'emulator-5554')
        for serial in ('192.168.1.2:5555', 'physical-device-id', 'emulator-5555', 'emulator-8000'):
            self.file.write_text(json.dumps({**self.ctx, 'serial': serial}), encoding='utf-8')
            with self.subTest(serial=serial), self.assertRaises(ValueError):
                android.context_from(self.file)

    def test_contexto_exige_readonly_recursos_limitados_y_sdk_coherente(self):
        for changed in ({'read_only_avd': False}, {'memory_mib': 8192}, {'cores': 16},
                        {'adb': str(self.emulator)}, {'avd': '../foreign'}):
            self.file.write_text(json.dumps({**self.ctx, **changed}), encoding='utf-8')
            with self.subTest(changed=list(changed)), self.assertRaises(ValueError):
                android.context_from(self.file)

    def test_pid_reutilizado_o_proceso_ajeno_no_se_acepta(self):
        fake_psutil = SimpleNamespace(Process=Mock(return_value=self.process))
        with patch.dict(sys.modules, {'psutil': fake_psutil}):
            self.assertIs(android.own_process(self.ctx), self.process)
            self.process.create_time.return_value = 200.
            with self.assertRaises(ValueError):
                android.own_process(self.ctx)
            self.process.create_time.return_value = 100.
            self.process.exe.return_value = str(self.adb)
            with self.assertRaises(ValueError):
                android.own_process(self.ctx)

    def test_no_cierra_si_flags_o_avd_no_pertenecen_al_contexto(self):
        self.process.cmdline.return_value = [str(self.emulator), '-avd', 'Other_AVD']
        fake_psutil = SimpleNamespace(Process=Mock(return_value=self.process))
        with patch.dict(sys.modules, {'psutil': fake_psutil}), patch.object(android, 'adb_call') as adb:
            with self.assertRaises(ValueError):
                android.close(self.file, self.ctx)
            adb.assert_not_called()

    def test_forward_existente_se_reutiliza_sin_crear_otro_ni_cambiar_chrome(self):
        with patch.object(android, 'require_device'), patch.object(android, 'forward_matches', return_value=True), \
                patch.object(android, 'cdp_json', return_value={'Browser': 'Chrome/156.0.8078.79'}), \
                patch.object(android, 'adb_call', side_effect=AssertionError('No duplicate forward')), \
                patch.object(android, 'save_context', side_effect=AssertionError('No rewrite')):
            result = android.connect_browser(self.file, self.ctx)
        self.assertEqual(result['cdp_port'], 52216)
        self.assertFalse(result['physical_device'])

    def test_captura_png_binaria_valida_dimensiones_y_rechaza_texto(self):
        data = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 1080, 2400) + b'\0' * 8
        result = android.png_metadata(data)
        self.assertEqual((result['width'], result['height']), (1080, 2400))
        self.assertEqual(result['bytes'], len(data))
        for payload in (b'private-text-not-a-PNG', data[:16] + struct.pack('>II', 0, 2400) + b'\0' * 8):
            with self.assertRaises(ValueError):
                android.png_metadata(payload)

    def test_cdp_rechaza_puerto_ajeno_y_endpoint_antes_de_red(self):
        with patch.object(android, 'build_opener', side_effect=AssertionError('No network')):
            for port, endpoint in ((8000, '/json/version'), (5432, '/json/protocol'),
                                   (52216, '/api/private'), (True, '/json/version')):
                with self.subTest(port=port), self.assertRaises(ValueError):
                    android.cdp_json(port, endpoint)

    def test_puertos_consola_invalidos_no_abren_socket(self):
        with patch.object(android.socket, 'socket', side_effect=AssertionError('No socket')):
            for port in (8000, 5555, 5684, True):
                with self.assertRaises(ValueError):
                    android.available_console_port(port)

    def test_capacidades_no_presenta_metodos_declarados_como_ejecutados(self):
        protocol = {'domains': [{'domain': 'Target', 'commands': [{'name': 'createBrowserContext'}]}]}
        with patch.object(android, 'connect_browser', return_value={'cdp_port': 52216}), \
                patch.object(android, 'cdp_json', return_value=protocol):
            result = android.capabilities(self.file, self.ctx)
        self.assertEqual(result['methods_declared_by_protocol'], ['Target.createBrowserContext'])
        self.assertFalse(result['methods_executed_by_this_check'])


if __name__ == '__main__':
    unittest.main()
