"""Arranque local de SKILLY sobre una copia PostgreSQL verificada, sin tocar otros servicios."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.2'
FORBIDDEN_PORTS = {8000, 5173, 5432}
STAGE = 'arguments'


def require(condition):
    if not condition:
        raise ValueError('Local configuration rejected')


def native(path):
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' and not str(path).startswith('\\\\?\\') else path


def read_json(path):
    file = native(path)
    require(file.stat().st_size < 4_000_000)
    return json.loads(file.read_text(encoding='utf-8'))


def free_port(requested=0, excluded=()):
    require(type(requested) is int and 0 <= requested <= 65535 and requested not in FORBIDDEN_PORTS)
    for _ in range(30):
        with socket.socket() as listener:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((HOST, requested))
            port = listener.getsockname()[1]
        if port not in FORBIDDEN_PORTS and port not in excluded:
            return port
        require(requested == 0)
    raise ValueError('No free local port')


def validate_database(cfg):
    require(cfg.get('POSTGRES_HOST') in ('127.0.0.1', 'localhost'))
    port = int(cfg['POSTGRES_PORT'])
    require(1024 <= port <= 65535 and port not in FORBIDDEN_PORTS)
    require((cfg.get('POSTGRES_DB'), cfg.get('POSTGRES_SCHEMA'), cfg.get('POSTGRES_USER')) == ('skilly', 'skilly', 'skilly_app'))
    return port


def copy_private_files(backup, runtime):
    report = []
    for group in ('media', 'entregas_privadas_e3'):
        source_root = backup / group
        require(source_root.is_dir())
        target_root = runtime / 'backend_files' / group
        count = 0
        for source in source_root.rglob('*'):
            if not source.is_file():
                continue
            require(not source.is_symlink() and source.resolve().is_relative_to(source_root.resolve()))
            target = target_root / source.relative_to(source_root)
            require(target.resolve().is_relative_to(runtime.resolve()))
            native(target.parent).mkdir(parents=True, exist_ok=True)
            with source.open('rb') as reader, native(target).open('xb') as writer:
                writer.write(reader.read())
            require(hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(native(target).read_bytes()).digest())
            count += 1
        report.append({'group': group, 'files': count, 'hashes_verified': True})
    return report


def context_from(path):
    file = Path(path)
    require(file.is_absolute())
    ctx = read_json(file)
    run = Path(ctx['run_dir']).resolve()
    backup = Path(ctx['backup_root']).resolve()
    require(backup.name.startswith('SKILLY_recuperacion_') and run.parent == backup and run.name.startswith('local_activo_') and not run.is_relative_to(ROOT))
    require(file.resolve() == run / 'contexto.json')
    require(Path(ctx['source_identity_file']).resolve() == run / 'backend_ready.json')
    require(ctx['project_root'] == str(ROOT) and ctx['isolated_database'] is True and ctx['host'] == HOST)
    for name in ('backend_origin', 'frontend_origin'):
        url = urlsplit(ctx[name])
        require(url.scheme == 'http' and url.hostname == HOST and url.port is not None and 1024 <= url.port <= 65535 and url.port not in FORBIDDEN_PORTS
                and not (url.username or url.password or url.query or url.fragment) and url.path in ('', '/'))
    return ctx


def start(args):
    global STAGE
    from dotenv import dotenv_values
    import psycopg
    backup = Path(args.respaldo).resolve(strict=True)
    cluster = Path(args.cluster).resolve(strict=True)
    config_file, admin_file = Path(args.conexion).resolve(strict=True), Path(args.admin).resolve(strict=True)
    require(backup.name.startswith('SKILLY_recuperacion_') and not backup.is_relative_to(ROOT))
    require(cluster.is_relative_to(backup) and cluster.name == 'cluster' and cluster.parent.name.startswith('ensayo_aislado_'))
    require(config_file.is_relative_to(backup) and admin_file.is_relative_to(cluster.parent))
    cfg, admin = dotenv_values(config_file), dotenv_values(admin_file)
    database_port = validate_database(cfg)
    require(int(admin['POSTGRES_PORT']) == database_port)
    backend_port = free_port(args.backend_port, {database_port})
    frontend_port = free_port(args.frontend_port, {database_port, backend_port})
    runtime = backup / ('local_activo_' + uuid4().hex[:16])
    runtime.mkdir(exist_ok=False)
    backend, frontend = f'http://{HOST}:{backend_port}', f'http://{HOST}:{frontend_port}'
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith(('PG', 'POSTGRES_')):
            environment.pop(name)
    pg_bin = Path(args.pg_bin)
    require((pg_bin / 'pg_ctl.exe').is_file())
    children, started = [], False
    ctx = {'project_root': str(ROOT), 'run_dir': str(runtime), 'backup_root': str(backup),
           'host': HOST, 'backend_origin': backend, 'frontend_origin': frontend,
           'database_port': database_port, 'isolated_database': True,
           'operational_env_modified': False, 'external_payments_and_mail': False}
    def pg(command):
        process = subprocess.run([str(pg_bin / 'pg_ctl.exe'), '-D', str(cluster), *command],
                                 env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        require(process.returncode == 0)
    try:
        STAGE = 'cluster_start'
        existing = subprocess.run([str(pg_bin / 'pg_ctl.exe'), '-D', str(cluster), 'status'],
                                  capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        if existing.returncode == 3:
            pg(['-l', str(runtime / 'postgres.log'), '-o', f'-h 127.0.0.1 -p {database_port} -c log_min_messages=panic -c log_min_error_statement=panic -c log_statement=none', '-w', 'start'])
            started = True
        else:
            require(existing.returncode == 0)
        STAGE = 'database_identity'
        with psycopg.connect(dbname='postgres', user=admin['POSTGRES_USER'], password=admin['POSTGRES_PASSWORD'], host='127.0.0.1', port=database_port, connect_timeout=5) as connection:
            require(Path(connection.execute('SHOW data_directory').fetchone()[0]).resolve() == cluster)
        with psycopg.connect(dbname='skilly', user=cfg['POSTGRES_USER'], password=cfg['POSTGRES_PASSWORD'], host='127.0.0.1', port=database_port, options='-c search_path=skilly,public -c default_transaction_read_only=on', connect_timeout=5) as connection:
            require(connection.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()').fetchone() == ('skilly', 'skilly', 'skilly_app', database_port))
        ctx['private_files'] = copy_private_files(backup, runtime)
        environment.update({key: value for key, value in cfg.items() if value is not None})
        environment.update({'POSTGRES_HOST': '127.0.0.1', 'DJANGO_SETTINGS_MODULE': 'skilly_local',
                            'DJANGO_DEBUG': 'true', 'DJANGO_ALLOWED_HOSTS': HOST, 'FRONTEND_ORIGIN': frontend,
                            'SKILLY_API_PROXY_TARGET': backend, 'PYTHONDONTWRITEBYTECODE': '1',
                            'PYTHONPATH': str(runtime) + os.pathsep + str(ROOT / 'backend')})
        settings = ('from config.settings import *\nfrom pathlib import Path\n'
                    'assert (DATABASES["default"]["NAME"],DATABASES["default"]["USER"],DATABASES["default"]["HOST"],str(DATABASES["default"]["PORT"])) == ("skilly","skilly_app","127.0.0.1",' + repr(str(database_port)) + '), "Isolated local database required"\n'
                    'EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"\n'
                    'BASE_DIR=Path(' + repr(str(runtime / 'backend_files')) + ')\nMEDIA_ROOT=BASE_DIR/"media"\n'
                    'LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"null":{"class":"logging.NullHandler"}},"root":{"handlers":["null"],"level":"CRITICAL"}}\n')
        compile(settings, 'skilly_local_settings', 'exec')
        (runtime / 'skilly_local.py').write_text(settings, encoding='utf-8')
        runner = '''import hashlib,json,os,socket,sys
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server,WSGIServer,WSGIRequestHandler
root=Path(PROJECT_ROOT)
sys.path.insert(0,str(root/'backend'))
original_connect=socket.socket.connect
def guarded(self,address):
 if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','localhost','::1') or address[1]!=int(os.environ['POSTGRES_PORT']):raise OSError('Outbound network disabled in isolated local environment')
 return original_connect(self,address)
socket.socket.connect=guarded
from config.wsgi import application
import config.wsgi as module
assert Path(module.__file__).resolve()==root/'backend/config/wsgi.py'
class Quiet(WSGIRequestHandler):
 def log_message(self,*args):pass
class Server(ThreadingMixIn,WSGIServer):daemon_threads=True
with make_server(HOST,PORT,application,server_class=Server,handler_class=Quiet) as httpd:
 files=[p for p in (root/'backend').rglob('*.py') if not p.name.startswith('test') and '__pycache__' not in p.parts]
 identity={'pid':os.getpid(),'wsgi_file':str(Path(module.__file__).resolve()),'project_root':str(root),'product_sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
 (Path(__file__).parent/'backend_ready.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
 httpd.serve_forever()
'''
        runner = 'PROJECT_ROOT=' + repr(str(ROOT)) + '\nHOST=' + repr(HOST) + '\nPORT=' + str(backend_port) + '\n' + runner
        compile(runner, 'skilly_local_runner', 'exec')
        (runtime / 'backend_local.py').write_text(runner, encoding='utf-8')
        STAGE = 'backend_start'
        children.append(subprocess.Popen([sys.executable, '-B', str(runtime / 'backend_local.py')], cwd=str(ROOT / 'backend'), env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
        node = args.node
        STAGE = 'frontend_start'
        children.append(subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', HOST, '--port', str(frontend_port), '--strictPort'], cwd=str(ROOT / 'frontend'), env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
        opener = build_opener(ProxyHandler({}))
        STAGE = 'readiness'
        for _ in range(150):
            require(all(process.poll() is None for process in children))
            try:
                identity = read_json(runtime / 'backend_ready.json')
                with opener.open(frontend + '/', timeout=1) as response:
                    require(response.status == 200)
                break
            except (OSError, ValueError):
                time.sleep(.1)
        else:
            raise RuntimeError('Local services did not become ready')
        ctx.update(backend_pid=identity['pid'], frontend_pid=children[1].pid,
                   source_identity_file=str(runtime / 'backend_ready.json'), supervisor_pid=os.getpid())
        (runtime / 'contexto.json').write_text(json.dumps(ctx, indent=2), encoding='utf-8')
        (ROOT / '.skilly-local-activo.tmp').write_text(json.dumps(ctx), encoding='utf-8')
        print(json.dumps({'completed': True, 'backend': backend, 'frontend': frontend, 'context': str(runtime / 'contexto.json'), 'isolated_database': True}), flush=True)
        STAGE = 'running'
        while not (runtime / 'stop.flag').exists():
            require(all(process.poll() is None for process in children))
            time.sleep(.5)
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        if started:
            pg(['-m', 'fast', '-w', 'stop'])
        (runtime / 'cierre.json').write_text(json.dumps({'own_children_closed': True, 'own_cluster_stopped': started, 'other_processes_touched': False}), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    start_parser = sub.add_parser('iniciar')
    for name in ('respaldo', 'cluster', 'conexion', 'admin'):
        start_parser.add_argument('--' + name, required=True)
    start_parser.add_argument('--backend-port', type=int, default=0)
    start_parser.add_argument('--frontend-port', type=int, default=0)
    start_parser.add_argument('--pg-bin', default=r'C:\Program Files\PostgreSQL\18\bin')
    start_parser.add_argument('--node', default=r'C:\Program Files\nodejs\node.exe')
    for action in ('estado', 'detener'):
        sub.add_parser(action).add_argument('--contexto', required=True)
    args = parser.parse_args()
    if args.action == 'iniciar':
        return start(args)
    ctx = context_from(args.contexto)
    if args.action == 'detener':
        with (Path(ctx['run_dir']) / 'stop.flag').open('x', encoding='utf-8') as marker:
            marker.write('Stop only this owned SKILLY local environment.\n')
        print(json.dumps({'stop_requested': True}))
        return
    identity = read_json(ctx['source_identity_file'])
    require(identity.get('project_root') == str(ROOT) and identity.get('wsgi_file') == str(ROOT / 'backend/config/wsgi.py') and identity.get('pid') == ctx['backend_pid'])
    require(isinstance(identity.get('product_sources'), dict) and bool(identity['product_sources']))
    for name in identity['product_sources']:
        require(not Path(name).is_absolute() and '..' not in Path(name).parts)
        source = (ROOT / name).resolve()
        require(source.is_relative_to(ROOT / 'backend') and source.suffix == '.py')
        require(isinstance(identity['product_sources'][name], str) and re.fullmatch(r'[a-f0-9]{64}', identity['product_sources'][name]))
    source_current = all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in identity['product_sources'].items())
    print(json.dumps({'backend': ctx['backend_origin'], 'frontend': ctx['frontend_origin'], 'backend_pid': ctx['backend_pid'], 'frontend_pid': ctx['frontend_pid'], 'product_sources_current': source_current, 'isolated_database': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        kind = type(error).__name__ if type(error).__name__ in ('ValueError', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError') else 'LocalEnvironmentError'
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': kind}), flush=True)
        raise SystemExit(1) from None
