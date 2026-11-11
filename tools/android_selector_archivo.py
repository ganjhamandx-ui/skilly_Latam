"""Selecciona un adjunto sintetico ya copiado mediante el selector nativo del AVD.

No abre Chrome, no concede permisos y no admite dispositivos fisicos. El caller
debe abrir antes un input[type=file] real. No acredita por si solo la subida.
"""
import argparse
import hashlib
import json
import re
import time
import unicodedata
from uuid import uuid4
import xml.etree.ElementTree as ET

import android_navegador_skilly as android


DOCUMENTS = {'com.android.documentsui', 'com.google.android.documentsui'}
PERMISSIONS = {'com.android.permissioncontroller', 'com.google.android.permissioncontroller'}
CHOOSERS = {'android', 'com.android.intentresolver', 'com.google.android.intentresolver'}
DENY_IDS = {'permission_deny_button', 'permission_deny_and_dont_ask_again_button'}
STAGE = 'arguments'


def require(condition):
    if not condition:
        raise ValueError('Selector Android no validado')


def normalized(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', value)
                            if unicodedata.category(c) != 'Mn').lower().split())


def checked_filename(value):
    require(isinstance(value, str) and len(value) <= 240
            and re.fullmatch(r'skilly_[A-Za-z0-9][A-Za-z0-9_.-]*', value) is not None
            and '..' not in value)
    return value


def screen_size(payload):
    require(len(payload) <= 4096)
    matches = re.findall(rb'(?:Physical|Override) size: ([0-9]{2,5})x([0-9]{2,5})', payload)
    require(bool(matches))
    width, height = map(int, matches[-1])
    require(100 <= width <= 8192 and 100 <= height <= 16384)
    return width, height


def bounds_center(raw, size):
    match = re.fullmatch(r'\[([0-9]{1,5}),([0-9]{1,5})\]\[([0-9]{1,5}),([0-9]{1,5})\]', raw)
    require(match is not None)
    left, top, right, bottom = map(int, match.groups())
    require(0 <= left < right <= size[0] and 0 <= top < bottom <= size[1])
    return (left + right) // 2, (top + bottom) // 2


def parse_hierarchy(payload):
    require(isinstance(payload, bytes) and 0 < len(payload) <= 2_000_000
            and b'<!DOCTYPE' not in payload.upper() and b'<!ENTITY' not in payload.upper())
    tree = ET.fromstring(payload)
    require(tree.tag == 'hierarchy')
    nodes = list(tree.iter('node'))
    require(0 < len(nodes) <= 10000)
    return tree, nodes, {child: parent for parent in tree.iter() for child in parent}


def actionable(node, parents, size):
    package = node.get('package', '')
    current = node
    while current is not None and current.tag == 'node' and current.get('package', '') == package:
        if current.get('enabled', 'true') == 'false' or current.get('visible-to-user', 'true') == 'false':
            return None
        if current.get('clickable') == 'true':
            try:
                return bounds_center(current.get('bounds', ''), size)
            except ValueError:
                return None
        current = parents.get(current)
    return None


def unique_target(nodes, parents, size):
    targets = {point for node in nodes if (point := actionable(node, parents, size)) is not None}
    require(len(targets) <= 1)
    return next(iter(targets), None)


def next_action(payload, filename, size, *, selected=False, permission_denied=False):
    """Solo devuelve una accion acotada; nunca expone texto/XML en el resultado."""
    checked_filename(filename)
    _, nodes, parents = parse_hierarchy(payload)
    packages = {node.get('package', '') for node in nodes}
    if packages.intersection(PERMISSIONS):
        messages = ' '.join(normalized(node.get('text', '')) for node in nodes
                            if node.get('package') in PERMISSIONS)
        # Ningun permiso de archivos, ubicacion u otra clase se responde aqui.
        camera_or_mic = any(word in messages for word in (
            'camera', 'camara', 'record video', 'grabar video', 'microphone',
            'microfono', 'record audio', 'grabar audio', 'take pictures', 'tomar fotos'))
        require(camera_or_mic)
        deny = [node for node in nodes if node.get('package') in PERMISSIONS
                and node.get('resource-id', '').rsplit('/', 1)[-1] in DENY_IDS]
        point = unique_target(deny, parents, size)
        require(point is not None)
        return {'kind': 'deny_camera_microphone', 'point': point}
    if selected and not packages.intersection(DOCUMENTS | CHOOSERS):
        require('com.android.chrome' in packages)
        return {'kind': 'completed'}
    if permission_denied and 'com.android.chrome' in packages and not packages.intersection(DOCUMENTS | CHOOSERS):
        return {'kind': 'retry_file_input_required'}
    if packages.intersection(DOCUMENTS):
        file_nodes = [node for node in nodes if node.get('package') in DOCUMENTS
                      and filename in (node.get('text', ''), node.get('content-desc', ''))]
        point = unique_target(file_nodes, parents, size)
        if point is not None:
            return {'kind': 'select_exact_file', 'point': point}
        downloads = [node for node in nodes if node.get('package') in DOCUMENTS
                     and normalized(node.get('text', '')) in ('downloads', 'descargas')]
        point = unique_target(downloads, parents, size)
        if point is not None:
            return {'kind': 'open_downloads', 'point': point}
        roots = [node for node in nodes if node.get('package') in DOCUMENTS
                 and (normalized(node.get('content-desc', '')) in (
                     'show roots', 'mostrar raices', 'open navigation drawer',
                     'abrir menu de navegacion', 'navigate up', 'navegar hacia arriba')
                      or node.get('resource-id') == 'android:id/home')]
        point = unique_target(roots, parents, size)
        return {'kind': 'open_roots', 'point': point} if point is not None else {'kind': 'wait'}
    if packages.intersection(CHOOSERS):
        files = [node for node in nodes if node.get('package') in CHOOSERS
                 and normalized(node.get('text', '')) in ('files', 'archivos', 'documents', 'documentos')]
        point = unique_target(files, parents, size)
        return {'kind': 'open_files', 'point': point} if point is not None else {'kind': 'wait'}
    # No pulsar controles de Chrome ni de otras aplicaciones por coincidencia textual.
    return {'kind': 'wait'}


def select_file(ctx, filename, max_seconds=25):
    filename = checked_filename(filename)
    require(type(max_seconds) is int and 1 <= max_seconds <= 25)
    android.require_device(ctx)
    result = android.adb_call(ctx, 'shell', 'wm', 'size', timeout=5)
    require(result.returncode == 0)
    size = screen_size(result.stdout)
    exists = android.adb_call(ctx, 'shell', 'test', '-f', '/sdcard/Download/' + filename, timeout=5)
    require(exists.returncode == 0)
    remote = '/sdcard/skilly_picker_' + uuid4().hex + '.xml'
    require(re.fullmatch(r'/sdcard/skilly_picker_[a-f0-9]{32}\.xml', remote) is not None)
    deadline = time.monotonic() + max_seconds
    actions, selected, permission_denied, previous, repeated = [], False, False, None, 0
    try:
        while time.monotonic() < deadline:
            remaining = max(1, min(8, deadline - time.monotonic()))
            dumped = android.adb_call(ctx, 'shell', 'uiautomator', 'dump', '--compressed', remote, timeout=remaining)
            require(dumped.returncode == 0)
            result = android.adb_call(ctx, 'exec-out', 'cat', remote, timeout=max(1, min(3, deadline - time.monotonic())))
            require(result.returncode == 0)
            action = next_action(result.stdout, filename, size, selected=selected,
                                 permission_denied=permission_denied)
            kind = action['kind']
            if kind == 'retry_file_input_required':
                return {'completed': False, 'native_picker_automated': False,
                        'physical_device': False, 'serial': ctx['serial'], 'actions': actions,
                        'retry_file_input_required': True, 'upload_verified': False}
            if kind == 'completed':
                return {'completed': True, 'native_picker_automated': True,
                        'physical_device': False, 'serial': ctx['serial'], 'actions': actions,
                        'filename_sha256': hashlib.sha256(filename.encode()).hexdigest(),
                        'upload_verified': False}
            signature = (kind, action.get('point'))
            repeated = repeated + 1 if signature == previous and kind != 'wait' else 0
            previous = signature
            require(repeated <= 2 and len(actions) < 12)
            if 'point' in action:
                x, y = action['point']
                tapped = android.adb_call(ctx, 'shell', 'input', 'tap', str(x), str(y), timeout=3)
                require(tapped.returncode == 0)
                actions.append(kind)
                selected = selected or kind == 'select_exact_file'
                permission_denied = permission_denied or kind == 'deny_camera_microphone'
            time.sleep(min(.35, max(0, deadline - time.monotonic())))
        raise ValueError('Selector Android no completado')
    finally:
        # Ruta UUID propia exacta; no se borran archivos subidos ni otros dumps.
        android.adb_call(ctx, 'shell', 'rm', '-f', remote, timeout=3)


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Argumentos del selector Android no validos')


def main():
    global STAGE
    parser = PrivateParser(description=__doc__)
    parser.add_argument('--contextoAndroid', '--contexto-android', dest='context', required=True)
    parser.add_argument('--archivo', required=True)
    parser.add_argument('--max-segundos', type=int, default=25)
    args = parser.parse_args()
    checked_filename(args.archivo)
    STAGE = 'context'
    _, ctx = android.context_from(args.context)
    STAGE = 'native_picker'
    return select_file(ctx, args.archivo, args.max_segundos)


if __name__ == '__main__':
    try:
        print(json.dumps(main()))
    except Exception:
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': 'AndroidPickerRejected'}))
        raise SystemExit(1) from None
