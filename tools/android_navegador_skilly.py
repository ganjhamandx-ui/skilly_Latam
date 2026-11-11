"""Control acotado de un AVD de ensayo propio; no instala ni controla telefonos ajenos."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import time
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
POINTER = ROOT / '.skilly-android-actual.tmp'
FORBIDDEN = {8000, 5173, 5432, 9000}
STAGE = 'arguments'


def require(condition):
    if not condition:
        raise ValueError('Android de ensayo no validado')


def read_json(path):
    path = Path(path)
    require(path.is_file() and path.stat().st_size < 65536)
    return json.loads(path.read_text(encoding='utf-8'))


def save_context(file, context):
    temporary = file.parent / ('contexto_' + uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(context, stream, indent=2)
    os.replace(temporary, file)


def context_from(value):
    file = Path(value).resolve(strict=True)
    require(file.is_absolute() and file.name == 'contexto_android.json')
    ctx = read_json(file)
    run = Path(ctx['run_dir']).resolve(strict=True)
    backup = run.parent
    require(run.name.startswith('android_ejecucion_') and backup.name.startswith('SKILLY_recuperacion_')
            and not run.is_relative_to(ROOT) and file.parent == run)
    require(ctx.get('read_only_avd') is True and ctx.get('memory_mib') == 2048 and ctx.get('cores') == 2)
    require(isinstance(ctx.get('avd'), str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', ctx['avd']))
    require(isinstance(ctx.get('serial'), str) and re.fullmatch(r'emulator-\d{4}', ctx['serial']))
    port = int(ctx['serial'].split('-')[1])
    require(5554 <= port <= 5682 and port % 2 == 0)
    adb, emulator = Path(ctx['adb']).resolve(strict=True), Path(ctx['emulator']).resolve(strict=True)
    require(adb.name.lower() == 'adb.exe' and adb.parent.name == 'platform-tools'
            and emulator.name.lower() == 'emulator.exe' and emulator.parent.name == 'emulator'
            and adb.parent.parent == emulator.parent.parent)
    require(type(ctx.get('launcher_pid')) is int and ctx['launcher_pid'] > 0)
    return file, ctx


def own_process(ctx):
    import psutil
    process = psutil.Process(ctx['launcher_pid'])
    require(process.is_running() and Path(process.exe()).resolve() == Path(ctx['emulator']).resolve())
    arguments = process.cmdline()[1:]
    def flag(name, expected):
        return name in arguments and arguments.index(name) + 1 < len(arguments) and arguments[arguments.index(name) + 1] == expected
    require(flag('-avd', ctx['avd']) and flag('-port', ctx['serial'].split('-')[1])
            and flag('-memory', '2048') and flag('-cores', '2')
            and all(value in arguments for value in ('-read-only', '-no-snapshot-save', '-no-snapshot-load', '-no-window')))
    if 'created' in ctx:
        created = float(ctx['created'])
    else:
        # Compatibilidad con el primer arranque: log creado antes del Popen.
        metadata = (Path(ctx['run_dir']) / 'emulator_privado.log').stat()
        created = getattr(metadata, 'st_birthtime', metadata.st_ctime)
    require(abs(process.create_time() - created) < 30)
    return process


def adb_call(ctx, *arguments, timeout=20):
    return subprocess.run([ctx['adb'], '-s', ctx['serial'], *arguments],
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def require_device(ctx):
    own_process(ctx)
    state = adb_call(ctx, 'get-state')
    require(state.returncode == 0 and state.stdout.strip() == b'device')
    avd = adb_call(ctx, 'emu', 'avd', 'name')
    lines = avd.stdout.decode('utf-8', errors='replace').splitlines()
    require(avd.returncode == 0 and lines and lines[0].strip() == ctx['avd'])


def safe_version(raw):
    text = raw.decode('utf-8', errors='replace').strip()
    require(re.fullmatch(r'[0-9A-Za-z._-]{1,80}', text) is not None)
    return text


def status(ctx):
    require_device(ctx)
    boot = adb_call(ctx, 'shell', 'getprop', 'sys.boot_completed')
    version = adb_call(ctx, 'shell', 'getprop', 'ro.build.version.release')
    api = adb_call(ctx, 'shell', 'getprop', 'ro.build.version.sdk')
    chrome = adb_call(ctx, 'shell', 'dumpsys', 'package', 'com.android.chrome')
    match = re.search(rb'versionName=([0-9.]+)', chrome.stdout)
    require(version.returncode == api.returncode == 0)
    return {'completed': True, 'serial': ctx['serial'], 'avd': ctx['avd'],
            'launcher_pid': ctx['launcher_pid'], 'boot_completed': boot.stdout.strip() == b'1',
            'android_version': safe_version(version.stdout), 'api': safe_version(api.stdout),
            'chrome_version': match.group(1).decode() if match else None,
            'physical_device': False, 'environment': 'Android emulator',
            'read_only_avd': True, 'main_skilly_touched': False}


def png_metadata(payload):
    require(32 <= len(payload) <= 32_000_000 and payload[:8] == b'\x89PNG\r\n\x1a\n'
            and payload[12:16] == b'IHDR')
    width, height = struct.unpack('>II', payload[16:24])
    require(0 < width <= 8192 and 0 < height <= 8192)
    return {'width': width, 'height': height, 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def capture(ctx):
    require_device(ctx)
    result = adb_call(ctx, 'exec-out', 'screencap', '-p')
    require(result.returncode == 0)
    metadata = png_metadata(result.stdout)
    folder = Path(ctx['run_dir']) / 'capturas_privadas'
    folder.mkdir(exist_ok=True)
    target = folder / ('android_' + uuid4().hex + '.png')
    with target.open('xb') as stream:
        stream.write(result.stdout)
    return {'completed': True, 'screenshot': str(target), **metadata,
            'environment': 'Android emulator', 'physical_device': False}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


def cdp_json(port, endpoint):
    require(type(port) is int and 1024 <= port <= 65535 and port not in FORBIDDEN
            and endpoint in ('/json/version', '/json/protocol'))
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open('http://127.0.0.1:' + str(port) + endpoint, timeout=5) as response:
        require(response.status == 200)
        data = response.read(8_000_001)
        require(len(data) <= 8_000_000)
        return json.loads(data)


def forward_ports(ctx):
    result = adb_call(ctx, 'forward', '--list')
    require(result.returncode == 0)
    ports = []
    for line in result.stdout.decode('utf-8', errors='replace').splitlines():
        fields = line.split()
        if (len(fields) == 3 and fields[0] == ctx['serial']
                and fields[2] == 'localabstract:chrome_devtools_remote'):
            require(re.fullmatch(r'tcp:[0-9]+', fields[1]) is not None)
            port = int(fields[1].split(':')[1])
            require(1024 <= port <= 65535 and port not in FORBIDDEN)
            ports.append(port)
    return sorted(set(ports))


def forward_matches(ctx, port):
    require(type(port) is int and 1024 <= port <= 65535 and port not in FORBIDDEN)
    return port in forward_ports(ctx)


def connect_browser(file, ctx, launch=False):
    require_device(ctx)
    port = ctx.get('cdp_port')
    if port is None or not forward_matches(ctx, port):
        existing = forward_ports(ctx)
        require(len(existing) <= 1)
        if existing:
            port = existing[0]
        else:
            pid = adb_call(ctx, 'shell', 'pidof', 'com.android.chrome')
            if pid.returncode != 0 or not pid.stdout.strip():
                require(launch)
                started = adb_call(ctx, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
                                   '-d', 'about:blank', '-p', 'com.android.chrome')
                require(started.returncode == 0)
            mapping = adb_call(ctx, 'forward', 'tcp:0', 'localabstract:chrome_devtools_remote')
            require(mapping.returncode == 0)
            port = int(mapping.stdout.strip())
            require(port not in FORBIDDEN and forward_matches(ctx, port))
        ctx['cdp_port'] = port
        save_context(file, ctx)
    info = cdp_json(port, '/json/version')
    require(isinstance(info.get('Browser'), str) and info['Browser'].startswith('Chrome/'))
    return {'completed': True, 'cdp_host': '127.0.0.1', 'cdp_port': port,
            'browser': info['Browser'], 'protocol_version': info.get('Protocol-Version'),
            'physical_device': False, 'environment': 'Android emulator'}


def capabilities(file, ctx):
    report = connect_browser(file, ctx)
    protocol = cdp_json(report['cdp_port'], '/json/protocol')
    wanted = {'Target.createBrowserContext', 'Target.disposeBrowserContext', 'Target.createTarget',
              'Page.captureScreenshot', 'Input.dispatchTouchEvent', 'Runtime.evaluate'}
    declared = {domain.get('domain', '') + '.' + command.get('name', '')
                for domain in protocol.get('domains', []) for command in domain.get('commands', [])}
    return {**report, 'methods_declared_by_protocol': sorted(wanted.intersection(declared)),
            'methods_executed_by_this_check': False,
            'note': 'La declaracion del protocolo no acredita que Android permita crear contextos.'}


def close(file, ctx):
    process = own_process(ctx)
    require_device(ctx)
    # Nunca kill-server, remove-all, borrar datos ni detener emuladores ajenos.
    if ctx.get('cdp_port') is not None and forward_matches(ctx, ctx['cdp_port']):
        require(adb_call(ctx, 'forward', '--remove', 'tcp:' + str(ctx['cdp_port'])).returncode == 0)
    for port in ctx.get('reverse_ports', []):
        require(type(port) is int and 1024 <= port <= 65535 and port not in FORBIDDEN)
        require(adb_call(ctx, 'reverse', '--remove', 'tcp:' + str(port)).returncode == 0)
    require(adb_call(ctx, 'emu', 'kill').returncode == 0)
    import psutil
    try:
        process.wait(timeout=20)
    except psutil.TimeoutExpired:
        # Si el cierre normal no termina, no matar procesos sin otra revision.
        raise ValueError('Cierre Android no confirmado') from None
    report = {'completed': True, 'own_emulator_closed': True, 'serial': ctx['serial'],
              'other_devices_touched': False, 'avd_saved': False, 'main_skilly_touched': False}
    marker = Path(ctx['run_dir']) / ('cierre_android_' + uuid4().hex + '.json')
    marker.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def available_console_port(requested):
    candidates = [requested] if requested else range(5554, 5683, 2)
    for port in candidates:
        require(type(port) is int and 5554 <= port <= 5682 and port % 2 == 0)
        sockets = []
        try:
            for candidate in (port, port + 1):
                listener = socket.socket()
                sockets.append(listener)
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                listener.bind(('127.0.0.1', candidate))
            return port
        except OSError:
            if requested:
                raise ValueError('Puertos del AVD ocupados') from None
        finally:
            for listener in sockets:
                listener.close()
    raise ValueError('Sin puertos libres para AVD')


def start(args):
    import psutil
    backup, sdk = Path(args.respaldo).resolve(strict=True), Path(args.sdk).resolve(strict=True)
    require(backup.name.startswith('SKILLY_recuperacion_') and not backup.is_relative_to(ROOT))
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', args.avd) is not None)
    adb, emulator = sdk / 'platform-tools/adb.exe', sdk / 'emulator/emulator.exe'
    require(adb.is_file() and emulator.is_file())
    if POINTER.exists():
        file, existing = context_from(read_json(POINTER)['context'])
        if psutil.pid_exists(existing['launcher_pid']):
            own_process(existing)
            return {**status(existing), 'reused_existing': True, 'context': str(file)}
    port = available_console_port(args.puerto)
    run = backup / ('android_ejecucion_' + uuid4().hex[:16])
    run.mkdir(exist_ok=False)
    command = [str(emulator), '-avd', args.avd, '-read-only', '-no-snapshot-save',
               '-no-snapshot-load', '-no-window', '-memory', '2048', '-cores', '2',
               '-gpu', 'swiftshader', '-port', str(port)]
    environment = os.environ.copy()
    environment['ANDROID_SDK_ROOT'] = str(sdk)
    with (run / 'emulator_privado.log').open('xb') as log:
        child = subprocess.Popen(command, env=environment, cwd=str(run), stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=log,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    ctx = {'run_dir': str(run), 'launcher_pid': child.pid, 'created': psutil.Process(child.pid).create_time(),
           'avd': args.avd, 'serial': 'emulator-' + str(port), 'adb': str(adb),
           'emulator': str(emulator), 'read_only_avd': True, 'memory_mib': 2048,
           'cores': 2, 'main_skilly_untouched': True}
    file = run / 'contexto_android.json'
    with file.open('x', encoding='utf-8') as stream:
        json.dump(ctx, stream, indent=2)
    POINTER.write_text(json.dumps({'context': str(file)}), encoding='utf-8')
    return {'completed': True, 'started': True, 'boot_completed_verified': False,
            'context': str(file), 'launcher_pid': child.pid, 'serial': ctx['serial'],
            'note': 'Consultar estado hasta que boot_completed sea true; no inicia ni altera SKILLY.'}


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Argumentos Android no validos')


def main():
    global STAGE
    parser = PrivateParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    initial = commands.add_parser('iniciar')
    initial.add_argument('--respaldo', required=True)
    initial.add_argument('--sdk', default=str(Path.home() / 'AppData/Local/Android/Sdk'))
    initial.add_argument('--avd', default='Medium_Phone_API_37.0')
    initial.add_argument('--puerto', type=int, default=0)
    for action in ('estado', 'captura', 'conectar', 'capacidades', 'cerrar'):
        sub = commands.add_parser(action)
        sub.add_argument('--contexto', required=True)
        if action == 'conectar':
            sub.add_argument('--abrir-chrome', action='store_true')
    args = parser.parse_args()
    STAGE = args.action
    if args.action == 'iniciar':
        return start(args)
    file, ctx = context_from(args.contexto)
    return {'estado': lambda: status(ctx), 'captura': lambda: capture(ctx),
            'conectar': lambda: connect_browser(file, ctx, args.abrir_chrome),
            'capacidades': lambda: capabilities(file, ctx),
            'cerrar': lambda: close(file, ctx)}[args.action]()


if __name__ == '__main__':
    try:
        print(json.dumps(main()))
    except Exception:
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': 'AndroidControlRejected'}))
        raise SystemExit(1) from None
