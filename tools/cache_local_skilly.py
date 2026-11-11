"""Memurai local dedicado: no instala servicios, no limpia claves ni muestra credenciales."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.1'
FORBIDDEN = {8000, 5173, 5432, 9000}


def require(condition):
    if not condition:
        raise ValueError('Dedicated local cache configuration rejected')


def native(path):
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' and not str(path).startswith('\\\\?\\') else path


def read_json(path):
    file = native(path)
    require(file.stat().st_size <= 65536)
    return json.loads(file.read_text(encoding='utf-8'))


def validate_backup(path):
    require(Path(path).is_absolute())
    backup = Path(path).resolve(strict=True)
    require(backup.is_dir() and backup.name.startswith('SKILLY_recuperacion_')
            and not backup.is_relative_to(ROOT) and not any(char in str(backup) for char in '\r\n"'))
    return backup


def context_paths(config, backup):
    require(all(isinstance(config.get(name), str) and Path(config[name]).is_absolute()
                for name in ('run_dir', 'binary', 'config')))
    run, binary, file = [Path(config[name]).resolve(strict=True) for name in ('run_dir', 'binary', 'config')]
    require(run.parent == backup and run.name.startswith('cache_activa_') and file.parent == run and file.is_file())
    require(binary.is_relative_to(backup) and binary.name.casefold() == 'memurai.exe' and binary.is_file())
    require(config['host'] == HOST and type(config['port']) is int
            and 1024 <= config['port'] <= 65535 and config['port'] not in FORBIDDEN)
    require(type(config['pid']) is int and config['pid'] > 0
            and math.isfinite(float(config['created'])))
    require(isinstance(config['password'], str) and re.fullmatch(r'[a-f0-9]{64}', config['password']) is not None)
    expected = config.get('binary_sha256')
    if not expected:
        # Compatibilidad con la instancia verificada por el auxiliar anterior;
        # solo se consulta su informe sanitizado dentro del mismo RUN.
        expected = read_json(run / 'inicio_sanitizado.json').get('binary_sha256')
    require(isinstance(expected, str) and re.fullmatch(r'[a-fA-F0-9]{64}', expected) is not None)
    require(hashlib.sha256(binary.read_bytes()).hexdigest() == expected.lower())
    return run, binary, file


def cache_process(config, backup):
    import psutil
    run, binary, file = context_paths(config, Path(backup).resolve())
    process = psutil.Process(config['pid'])
    require(Path(process.exe()).resolve() == binary)
    require(abs(process.create_time() - float(config['created'])) < 5)
    require(any(Path(argument).resolve() == file for argument in process.cmdline()[1:] if not argument.startswith('-')))
    return process


def redis_connection(config):
    import redis
    from redis.backoff import NoBackoff
    from redis.retry import Retry
    require(config['host'] == HOST and type(config['port']) is int and config['port'] not in FORBIDDEN)
    return redis.Redis(host=HOST, port=config['port'], password=config['password'], db=0,
                       socket_connect_timeout=.5, socket_timeout=.5,
                       retry=Retry(NoBackoff(), 0), decode_responses=True)


def load_context(path):
    file = Path(path).resolve(strict=True)
    config = read_json(file)
    backup = validate_backup(Path(config['run_dir']).resolve().parent)
    run, _, _ = context_paths(config, backup)
    require(file.parent == run and file.name == 'conexion_privada.json')
    return file, config, backup


def authenticated_state(config, backup):
    process = cache_process(config, backup)
    client = redis_connection(config)
    try:
        require(client.ping() is True)
        info = client.info('server')
        require(int(info.get('process_id', 0)) == process.pid)
        expected = {'bind': HOST, 'protected-mode': 'yes', 'maxmemory': str(64 * 1024 * 1024),
                    'maxmemory-policy': 'noeviction', 'save': '', 'appendonly': 'no'}
        for setting, value in expected.items():
            require(str(client.config_get(setting).get(setting)) == value)
        version = info.get('redis_version', '')
        require(isinstance(version, str) and re.fullmatch(r'[0-9.]+', version) is not None)
        return {'completed': True, 'pid': process.pid, 'host': HOST, 'port': config['port'],
                'authenticated_ping': True, 'server_pid_matches': True,
                'binary_sha256': hashlib.sha256(Path(config['binary']).read_bytes()).hexdigest(),
                'redis_version': version, 'persistence': False, 'memory_cap_mib': 64}
    finally:
        client.close()


def free_port(requested):
    require(type(requested) is int and (requested == 0 or 1024 <= requested <= 65535) and requested not in FORBIDDEN)
    for _ in range(30):
        with socket.socket() as listener:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((HOST, requested))
            port = listener.getsockname()[1]
        if port not in FORBIDDEN:
            return port
        require(requested == 0)
    raise ValueError('No dedicated cache port')


def start(args):
    import psutil
    backup = validate_backup(args.respaldo)
    require(Path(args.binario).is_absolute())
    binary = Path(args.binario).resolve(strict=True)
    require(binary.is_relative_to(backup) and binary.name.casefold() == 'memurai.exe')
    require(isinstance(args.sha256, str) and re.fullmatch(r'[a-fA-F0-9]{64}', args.sha256) is not None)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    require(digest == args.sha256.lower())
    if args.contexto:
        file, config, existing_backup = load_context(args.contexto)
        require(existing_backup == backup and Path(config['binary']).resolve() == binary)
        report = authenticated_state(config, backup)
        print(json.dumps({**report, 'reused_existing': True, 'context': str(file)}))
        return
    port = free_port(args.puerto)
    run = backup / ('cache_activa_' + uuid4().hex[:16])
    run.mkdir(exist_ok=False)
    password = secrets.token_hex(32)
    config = run / 'memurai.conf'
    lines = [
        'bind ' + HOST, 'port ' + str(port), 'protected-mode yes', 'requirepass ' + password,
        'maxmemory 64mb', 'maxmemory-policy noeviction', 'save ""', 'appendonly no',
        'winlog-level off', 'loglevel warning', 'logfile "' + (run / 'memurai.log').as_posix() + '"',
        'dir "' + run.as_posix() + '"', 'instance-name skilly-aislado',
    ]
    with config.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines) + '\n')
    process = subprocess.Popen([str(binary), str(config)], cwd=str(run), stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    context = {'pid': process.pid, 'host': HOST, 'port': port, 'password': password,
               'run_dir': str(run), 'binary': str(binary), 'config': str(config),
               'prefix': 'skilly-lab-' + uuid4().hex, 'created': psutil.Process(process.pid).create_time(),
               'binary_sha256': digest}
    context_file = run / 'conexion_privada.json'
    with context_file.open('x', encoding='utf-8') as stream:
        json.dump(context, stream)
    try:
        until = time.monotonic() + 12
        while time.monotonic() < until:
            require(process.poll() is None)
            try:
                report = authenticated_state(context, backup)
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Dedicated cache not ready')
        report.update(context=str(context_file), reused_existing=False, no_global_service_installed=True)
        with (run / 'inicio_sanitizado.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report))
    except Exception:
        if process.poll() is None:
            cache_process(context, backup).terminate()
            process.wait(timeout=10)
        raise


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Dedicated local cache arguments rejected')


def main():
    parser = PrivateArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    starting = commands.add_parser('iniciar')
    for name in ('respaldo', 'binario', 'sha256'):
        starting.add_argument('--' + name, required=True)
    starting.add_argument('--puerto', type=int, default=0)
    starting.add_argument('--contexto')
    for action in ('estado', 'detener'):
        commands.add_parser(action).add_argument('--contexto', required=True)
    args = parser.parse_args()
    if args.action == 'iniciar':
        return start(args)
    file, config, backup = load_context(args.contexto)
    report = authenticated_state(config, backup)
    if args.action == 'detener':
        process = cache_process(config, backup)
        process.terminate()
        process.wait(timeout=10)
        report.update(stopped=True, other_processes_touched=False)
        with (Path(config['run_dir']) / ('cierre_' + uuid4().hex[:12] + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps({**report, 'context': str(file)}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        kind = type(error).__name__ if type(error).__name__ in ['ValueError', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError'] else 'LocalCacheError'
        print(json.dumps({'completed': False, 'error_type': kind}), flush=True)
        raise SystemExit(1) from None
