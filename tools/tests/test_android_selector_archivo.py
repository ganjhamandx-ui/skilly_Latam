import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('android_selector_archivo', TOOLS / 'android_selector_archivo.py')
picker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(picker)
FILE = 'skilly_123_abcd_documento-sintetico.pdf'


def hierarchy(body):
    return ('<?xml version="1.0"?><hierarchy rotation="0">' + body + '</hierarchy>').encode()


def node(text='', package='com.google.android.documentsui', *, ident='', clickable=True,
         bounds='[0,100][1080,250]', content='', children=''):
    return (f'<node package="{package}" text="{text}" content-desc="{content}" '
            f'resource-id="{ident}" enabled="true" clickable="{str(clickable).lower()}" '
            f'bounds="{bounds}">{children}</node>')


class AndroidFilePickerTests(unittest.TestCase):
    def test_solo_archivo_sintetico_basename_sin_escape(self):
        self.assertEqual(picker.checked_filename(FILE), FILE)
        for value in ('archivo.pdf', '../skilly_a.pdf', 'skilly_../a', 'skilly_a/otro',
                      'skilly_a;rm', 'skilly_a b', 'skilly_..a', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                picker.checked_filename(value)

    def test_archivo_exacto_en_documentsui_sin_coincidencia_parcial(self):
        body = node(FILE + '.bak') + node(FILE, bounds='[0,300][1080,450]')
        action = picker.next_action(hierarchy(body), FILE, (1080, 2400))
        self.assertEqual(action, {'kind': 'select_exact_file', 'point': (540, 375)})

    def test_texto_descendiente_usa_ancestro_clickable_del_mismo_paquete(self):
        body = node('', children=node(FILE, clickable=False), bounds='[0,100][1080,300]')
        action = picker.next_action(hierarchy(body), FILE, (1080, 2400))
        self.assertEqual(action['point'], (540, 200))

    def test_documentos_con_mismo_nombre_ambiguo_se_rechazan(self):
        body = node(FILE) + node(FILE, bounds='[0,400][1080,550]')
        with self.assertRaises(ValueError):
            picker.next_action(hierarchy(body), FILE, (1080, 2400))

    def test_no_pulsa_nombres_en_chrome_u_otra_app(self):
        for package in ('com.android.chrome', 'otro.paquete'):
            action = picker.next_action(hierarchy(node(FILE, package)), FILE, (1080, 2400))
            self.assertEqual(action['kind'], 'wait')

    def test_chooser_files_raices_y_descargas(self):
        for body, expected in ((node('Files', 'android'), 'open_files'),
                               (node('Descargas'), 'open_downloads'),
                               (node('', content='Show roots'), 'open_roots')):
            with self.subTest(expected=expected):
                self.assertEqual(picker.next_action(hierarchy(body), FILE, (1080, 2400))['kind'], expected)

    def test_deniega_camara_solo_con_permiso_conocido(self):
        package = 'com.google.android.permissioncontroller'
        body = node('Allow Chrome to take pictures and record video?', package, clickable=False)
        body += node('Do not allow', package, ident=package + ':id/permission_deny_button')
        action = picker.next_action(hierarchy(body), FILE, (1080, 2400))
        self.assertEqual(action['kind'], 'deny_camera_microphone')
        body = body.replace('take pictures and record video', 'access your location')
        with self.assertRaises(ValueError):
            picker.next_action(hierarchy(body), FILE, (1080, 2400))

    def test_completion_exige_seleccion_y_retorno_chrome(self):
        page = hierarchy(node('', 'com.android.chrome'))
        self.assertEqual(picker.next_action(page, FILE, (1080, 2400))['kind'], 'wait')
        self.assertEqual(picker.next_action(page, FILE, (1080, 2400), selected=True)['kind'], 'completed')
        self.assertEqual(picker.next_action(page, FILE, (1080, 2400), permission_denied=True)['kind'],
                         'retry_file_input_required')

    def test_bounds_pantalla_y_xml_no_permiten_valores_fuera_de_limites(self):
        for bounds in ('[-1,0][10,10]', '[0,0][2000,2400]', '[10,10][0,0]', 'bad'):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                picker.bounds_center(bounds, (1080, 2400))
        for payload in (b'<!DOCTYPE hierarchy><hierarchy/>', b'not-xml', hierarchy('')):
            with self.subTest(payload=payload[:20]), self.assertRaises((ValueError, picker.ET.ParseError)):
                picker.parse_hierarchy(payload)
        self.assertEqual(picker.screen_size(b'Physical size: 1080x2400\nOverride size: 720x1600'), (720, 1600))

    def test_limite_y_guardia_se_validan_antes_de_adb(self):
        with patch.object(picker.android, 'require_device') as guard, patch.object(picker.android, 'adb_call') as adb:
            for seconds in (0, 26, True):
                with self.assertRaises(ValueError):
                    picker.select_file({}, FILE, seconds)
            guard.assert_not_called()
            adb.assert_not_called()

    def test_flujo_sintetico_seleccion_y_limpieza_solo_xml_propio(self):
        xml = iter((hierarchy(node(FILE)), hierarchy(node('', 'com.android.chrome'))))
        def adb(ctx, *args, **kwargs):
            payload = b''
            if args == ('shell', 'wm', 'size'):
                payload = b'Physical size: 1080x2400'
            elif args[:2] == ('exec-out', 'cat'):
                payload = next(xml)
            return SimpleNamespace(returncode=0, stdout=payload)
        with patch.object(picker.android, 'require_device'), patch.object(picker.android, 'adb_call', side_effect=adb) as calls, \
                patch.object(picker.time, 'sleep'):
            result = picker.select_file({'serial': 'emulator-5554'}, FILE)
        self.assertTrue(result['completed'])
        self.assertFalse(result['upload_verified'])
        self.assertEqual(result['actions'], ['select_exact_file'])
        cleanup = [call.args[1:] for call in calls.call_args_list if call.args[1:4] == ('shell', 'rm', '-f')]
        self.assertEqual(len(cleanup), 1)
        self.assertRegex(cleanup[0][3], r'^/sdcard/skilly_picker_[a-f0-9]{32}\.xml$')
        self.assertNotIn(FILE, cleanup[0][3])


if __name__ == '__main__':
    unittest.main()
