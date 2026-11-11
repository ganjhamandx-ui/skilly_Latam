"""Arranque local de SKILLY sobre una copia PostgreSQL verificada, sin tocar otros servicios."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit
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


def lan_host(value):
    require(isinstance(value, str))
    address = ipaddress.IPv4Address(value)
    require(str(address) == value and any(address in ipaddress.IPv4Network(network)
            for network in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
    return str(address)


def free_port(requested=0, excluded=(), host=HOST):
    require(host == HOST or lan_host(host) == host)
    require(type(requested) is int and 0 <= requested <= 65535 and requested not in FORBIDDEN_PORTS)
    for _ in range(30):
        with socket.socket() as listener:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((host, requested))
            port = listener.getsockname()[1]
        if port not in FORBIDDEN_PORTS and port not in excluded:
            return port
        require(requested == 0)
    raise ValueError('No free local port')


def cache_configuration(context_path, backup, runtime, database_port, database=15):
    if context_path is None:
        return None
    require(type(database) is int and 0 <= database <= 15)
    file = Path(context_path)
    require(file.is_absolute())
    file = file.resolve(strict=True)
    require(file.is_relative_to(backup) and not file.is_relative_to(ROOT))
    private = read_json(file)
    port = private.get('port')
    require(private.get('host') == '127.0.0.1' and type(port) is int
            and 1024 <= port <= 65535 and port not in FORBIDDEN_PORTS and port != database_port)
    password, prefix = private.get('password'), private.get('prefix')
    require(isinstance(password, str) and 16 <= len(password) <= 256 and not any(ord(value) <= 32 or ord(value) == 127 for value in password))
    require(isinstance(prefix, str) and re.fullmatch(r'[A-Za-z0-9:_-]{1,100}', prefix))
    return {'host': '127.0.0.1', 'port': port, 'database': database, 'password': password,
            'key_prefix': 'skilly-local-' + hashlib.sha256((prefix + '\0' + runtime.name).encode()).hexdigest()[:40],
            'location': 'redis://:' + quote(password, safe='') + '@127.0.0.1:' + str(port) + '/' + str(database)}


def validate_worker_count(count, cache):
    require(type(count) is int and count in (1, 2))
    require(count == 1 or (isinstance(cache, dict) and isinstance(cache.get('location'), str)
                          and cache['location'].startswith('redis://')))
    return count


def private_root_for(backup, runtime, reuse_context, database_port):
    if reuse_context is None:
        return runtime / 'backend_files', copy_private_files(backup, runtime), None
    previous, _closed = reuse_context_details(reuse_context)
    require(Path(previous['backup_root']).resolve() == backup and previous['database_port'] == database_port)
    private_root = Path(previous.get('private_root', str(Path(previous['run_dir']) / 'backend_files'))).resolve(strict=True)
    require(private_root.is_relative_to(backup) and not private_root.is_relative_to(ROOT)
            and private_root.name == 'backend_files' and private_root.parent.name.startswith('local_activo_')
            and all(native(private_root / group).is_dir() for group in ('media', 'entregas_privadas_e3')))
    return private_root, [{'mode': 'reused_existing_runtime', 'source_context': str(Path(reuse_context).resolve()),
                           'source_root': str(private_root), 'files_copied': 0}], previous


def reuse_context_details(path):
    context = context_from(path)
    run = Path(context['run_dir'])
    marker, closure_file = native(run / 'stop.flag'), native(run / 'cierre.json')
    if marker.exists():
        require(marker.is_file() and closure_file.is_file())
        closure = read_json(closure_file)
        require(closure.get('own_children_closed') is True and closure.get('other_processes_touched') is False)
        return context, True
    require(not closure_file.exists())
    return context, False


def generated_settings(private_root, database_port, frontend_origins, cache_prefix):
    return ('from config.settings import *\nfrom pathlib import Path\n'
            'assert (DATABASES["default"]["NAME"],DATABASES["default"]["USER"],DATABASES["default"]["HOST"],str(DATABASES["default"]["PORT"])) == ("skilly","skilly_app","127.0.0.1",' + repr(str(database_port)) + '), "Isolated local database required"\n'
            'EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"\n'
            'BASE_DIR=Path(' + repr(str(private_root)) + ')\nMEDIA_ROOT=BASE_DIR/"media"\n'
            'CORS_ALLOWED_ORIGINS=' + repr(frontend_origins) + '\nCSRF_TRUSTED_ORIGINS=' + repr(frontend_origins) + '\n'
            'CACHES[ACCESO_CACHE_ALIAS]["KEY_PREFIX"]=' + repr(cache_prefix) + '\n'
            'LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"null":{"class":"logging.NullHandler"}},"root":{"handlers":["null"],"level":"CRITICAL"}}\n')


def generated_runner(port, identity_name, allowed_outbound):
    runner = '''import hashlib,json,os,socket,sys
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server,WSGIServer,WSGIRequestHandler
root=Path(PROJECT_ROOT)
sys.path.insert(0,str(root/'backend'))
original_connect=socket.socket.connect
def guarded(self,address):
 if not isinstance(address,tuple) or tuple(address[:2]) not in ALLOWED_OUTBOUND:raise OSError('Outbound network disabled in isolated local environment')
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
 (Path(__file__).parent/IDENTITY_NAME).write_text(json.dumps(identity,indent=2),encoding='utf-8')
 httpd.serve_forever()
'''
    return ('PROJECT_ROOT=' + repr(str(ROOT)) + '\nHOST=' + repr(HOST) + '\nPORT=' + str(port)
            + '\nIDENTITY_NAME=' + repr(identity_name) + '\nALLOWED_OUTBOUND=' + repr(allowed_outbound) + '\n' + runner)


def owned_worker_processes(process, runner_file):
    """El launcher venv de Windows puede mantener un interprete hijo real."""
    import psutil
    require(process.poll() is None)
    file = Path(runner_file).resolve(strict=True)
    require(file.parent.name.startswith('local_activo_')
            and file.name in ('backend_local.py', 'backend_local_2.py'))
    allowed = {Path(sys.executable).resolve(), Path(getattr(sys, '_base_executable', sys.executable)).resolve(),
               Path(psutil.Process(os.getpid()).exe()).resolve()}
    parent = psutil.Process(process.pid)
    started = parent.create_time()

    def belongs(candidate):
        try:
            return (candidate.is_running() and candidate.create_time() >= started
                    and Path(candidate.exe()).resolve() in allowed
                    and Path(candidate.cwd()).resolve() == (ROOT / 'backend').resolve()
                    and any(Path(argument).resolve() == file for argument in candidate.cmdline()[1:]
                            if not argument.startswith('-')))
        except psutil.NoSuchProcess:
            return False

    require(belongs(parent))
    # children() comprueba la ascendencia y la identidad temporal del padre.
    return [parent, *(child for child in parent.children(recursive=True) if belongs(child))]


def validar_worker_identity(process, runner_file, identity):
    require(isinstance(identity, dict) and type(identity.get('pid')) is int and identity['pid'] > 0
            and identity.get('project_root') == str(ROOT)
            and identity.get('wsgi_file') == str(ROOT / 'backend/config/wsgi.py'))
    owned = owned_worker_processes(process, runner_file)
    matches = [candidate for candidate in owned if candidate.pid == identity['pid']]
    require(len(matches) == 1)
    return matches[0]


def close_owned_workers(records):
    """Cerrar solo procesos propios comprobados, incluso antes de publicar READY."""
    import psutil
    closed = True
    for process, file in reversed(records):
        if process.poll() is not None:
            # Los handles guardados por Popen no se sustituyen por PID reutilizados.
            closed = False
            continue
        try:
            owned = owned_worker_processes(process, file)
            for child in reversed(owned):
                if child.pid == process.pid:
                    continue
                try:
                    # psutil conserva create_time y rechaza un PID reutilizado.
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                except psutil.NoSuchProcess:
                    pass
        except (psutil.Error, OSError, ValueError):
            closed = False
    return closed


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
    require(type(ctx['database_port']) is int and 1024 <= ctx['database_port'] <= 65535 and ctx['database_port'] not in FORBIDDEN_PORTS)
    for name in ('backend_origin', 'frontend_origin'):
        url = urlsplit(ctx[name])
        require(url.scheme == 'http' and url.hostname == HOST and url.port is not None and 1024 <= url.port <= 65535 and url.port not in FORBIDDEN_PORTS
                and not (url.username or url.password or url.query or url.fragment) and url.path in ('', '/'))
    if 'frontend_lan_origin' in ctx:
        ip = lan_host(ctx.get('frontend_lan_host'))
        url = urlsplit(ctx['frontend_lan_origin'])
        require(url.scheme == 'http' and url.hostname == ip and url.port is not None and 1024 <= url.port <= 65535
                and url.port not in FORBIDDEN_PORTS and not (url.username or url.password or url.query or url.fragment) and url.path in ('', '/'))
    workers = ctx.get('backend_workers', [{'origin': ctx['backend_origin'], 'pid': ctx['backend_pid'], 'source_identity_file': ctx['source_identity_file']}])
    require(isinstance(workers, list) and 1 <= len(workers) <= 2)
    require(workers[0] == {'origin': ctx['backend_origin'], 'pid': ctx['backend_pid'], 'source_identity_file': ctx['source_identity_file']})
    for index, worker in enumerate(workers):
        url = urlsplit(worker['origin'])
        require(url.scheme == 'http' and url.hostname == HOST and url.port is not None and 1024 <= url.port <= 65535 and url.port not in FORBIDDEN_PORTS
                and url.path in ('', '/') and not (url.username or url.password or url.query or url.fragment))
        require(type(worker['pid']) is int and worker['pid'] > 0)
        expected = run / ('backend_ready.json' if index == 0 else 'backend_ready_2.json')
        require(Path(worker['source_identity_file']).resolve() == expected)
    require(len({worker['origin'] for worker in workers}) == len(workers))
    require(len({worker['pid'] for worker in workers}) == len(workers))
    if len(workers) == 2:
        require(isinstance(ctx.get('access_cache'), dict))
    if 'access_cache' in ctx:
        cache = ctx['access_cache']
        require(set(cache) == {'host', 'port', 'database', 'key_prefix'} and cache['host'] == '127.0.0.1'
                and type(cache['port']) is int and 1024 <= cache['port'] <= 65535 and cache['port'] not in FORBIDDEN_PORTS
                and type(cache['database']) is int and 0 <= cache['database'] <= 15
                and isinstance(cache['key_prefix'], str) and re.fullmatch(r'[A-Za-z0-9:_-]{1,64}', cache['key_prefix']))
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
    runtime = backup / ('local_activo_' + uuid4().hex[:16])
    runtime.mkdir(exist_ok=False)
    cache = cache_configuration(args.cache_contexto, backup, runtime, database_port, args.cache_db)
    validate_worker_count(args.workers, cache)
    excluded = {database_port} | ({cache['port']} if cache else set())
    backend_ports = [free_port(args.backend_port, excluded)]
    if args.workers == 2:
        backend_ports.append(free_port(args.backend2_port, excluded | set(backend_ports)))
    backend_port = backend_ports[0]
    frontend_port = free_port(args.frontend_port, excluded | set(backend_ports))
    lan = lan_host(args.frontend_lan_host) if args.frontend_lan_host else None
    require(lan is not None or args.frontend_lan_port == 0)
    require(args.workers == 2 or args.backend2_port == 0)
    lan_port = free_port(args.frontend_lan_port, excluded | set(backend_ports) | {frontend_port}, host=lan) if lan else None
    backend, frontend = f'http://{HOST}:{backend_port}', f'http://{HOST}:{frontend_port}'
    lan_origin = f'http://{lan}:{lan_port}' if lan else None
    frontend_origins = [frontend] + ([lan_origin] if lan_origin else [])
    _reuse_previous, reuse_closed = reuse_context_details(args.reutilizar_contexto) if args.reutilizar_contexto else (None, False)
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith(('PG', 'POSTGRES_')):
            environment.pop(name)
    pg_bin = Path(args.pg_bin)
    require((pg_bin / 'pg_ctl.exe').is_file())
    children, worker_records, started = [], [], False
    ctx = {'project_root': str(ROOT), 'run_dir': str(runtime), 'backup_root': str(backup),
           'host': HOST, 'backend_origin': backend, 'frontend_origin': frontend,
           'database_port': database_port, 'isolated_database': True,
           'operational_env_modified': False, 'external_payments_and_mail': False}
    if lan:
        ctx.update(frontend_lan_host=lan, frontend_lan_origin=lan_origin)
    if cache:
        ctx['access_cache'] = {name: cache[name] for name in ('host', 'port', 'database', 'key_prefix')}
    def pg(command):
        process = subprocess.run([str(pg_bin / 'pg_ctl.exe'), '-D', str(cluster), *command],
                                 env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        require(process.returncode == 0)
    try:
        STAGE = 'cluster_start'
        existing = subprocess.run([str(pg_bin / 'pg_ctl.exe'), '-D', str(cluster), 'status'],
                                  capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        if args.reutilizar_contexto and not reuse_closed:
            require(existing.returncode == 0)
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
        private_root, ctx['private_files'], previous = private_root_for(backup, runtime, args.reutilizar_contexto, database_port)
        ctx['private_root'] = str(private_root)
        ctx['cluster_started_by_this_supervisor'] = started
        ctx['owns_cluster'] = started
        if previous:
            ctx['reused_context'] = str(Path(args.reutilizar_contexto).resolve())
            ctx['reused_context_closed'] = reuse_closed
            if not reuse_closed:
                ctx['cluster_dependency_context'] = str(Path(args.reutilizar_contexto).resolve())
        if cache:
            STAGE = 'cache_readiness'
            import redis
            client = redis.Redis(host=cache['host'], port=cache['port'], password=cache['password'], db=cache['database'], socket_timeout=3, socket_connect_timeout=3)
            try:
                require(client.ping() is True)
            finally:
                client.connection_pool.disconnect()
        environment.update({key: value for key, value in cfg.items() if value is not None})
        environment.update({'POSTGRES_HOST': '127.0.0.1', 'DJANGO_SETTINGS_MODULE': 'skilly_local',
                            'DJANGO_DEBUG': 'true', 'DJANGO_ALLOWED_HOSTS': HOST, 'FRONTEND_ORIGIN': frontend,
                            'SKILLY_API_PROXY_TARGET': backend, 'PYTHONDONTWRITEBYTECODE': '1',
                            'PYTHONPATH': str(runtime) + os.pathsep + str(ROOT / 'backend')})
        environment.update({'ACCESO_CACHE_BACKEND': 'django.core.cache.backends.redis.RedisCache' if cache else 'django.core.cache.backends.locmem.LocMemCache',
                            'ACCESO_CACHE_LOCATION': cache['location'] if cache else runtime.name})
        settings = generated_settings(private_root, database_port, frontend_origins, cache['key_prefix'] if cache else runtime.name)
        compile(settings, 'skilly_local_settings', 'exec')
        (runtime / 'skilly_local.py').write_text(settings, encoding='utf-8')
        allowed_outbound = [('127.0.0.1', database_port), ('localhost', database_port), ('::1', database_port)]
        if cache:
            allowed_outbound.append((cache['host'], cache['port']))
        worker_files, identity_files = [], []
        for number, port in enumerate(backend_ports, 1):
            name = 'backend_local.py' if number == 1 else 'backend_local_2.py'
            identity_name = 'backend_ready.json' if number == 1 else 'backend_ready_2.json'
            runner = generated_runner(port, identity_name, allowed_outbound)
            compile(runner, 'skilly_local_runner', 'exec')
            (runtime / name).write_text(runner, encoding='utf-8')
            worker_files.append(runtime / name)
            identity_files.append(runtime / identity_name)
        public_startup = {'project_root': str(ROOT), 'backend_origins': [f'http://{HOST}:{port}' for port in backend_ports],
                          'frontend_origins': frontend_origins, 'database_port': database_port}
        (runtime / 'startup.json').write_text(json.dumps(public_startup), encoding='utf-8')
        STAGE = 'backend_start'
        for file in worker_files:
            process = subprocess.Popen([sys.executable, '-B', str(file)], cwd=str(ROOT / 'backend'), env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            children.append(process)
            worker_records.append((process, file))
        node = args.node
        STAGE = 'frontend_start'
        children.append(subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', HOST, '--port', str(frontend_port), '--strictPort'], cwd=str(ROOT / 'frontend'), env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
        if lan:
            children.append(subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', lan, '--port', str(lan_port), '--strictPort'], cwd=str(ROOT / 'frontend'), env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
        public_startup['launcher_pids'] = [process.pid for process in children]
        (runtime / 'startup.json').write_text(json.dumps(public_startup), encoding='utf-8')
        opener = build_opener(ProxyHandler({}))
        STAGE = 'readiness'
        for _ in range(150):
            require(all(process.poll() is None for process in children))
            try:
                STAGE = 'worker_manifest_readiness'
                identities = [read_json(file) for file in identity_files]
                for index, identity in enumerate(identities):
                    STAGE = 'worker_identity_' + str(index + 1)
                    validar_worker_identity(children[index], worker_files[index], identity)
                for index, origin in enumerate(frontend_origins):
                    STAGE = 'frontend_desktop_readiness' if index == 0 else 'frontend_lan_readiness'
                    with opener.open(origin + '/', timeout=1) as response:
                        require(response.status == 200)
                break
            except (OSError, ValueError):
                time.sleep(.1)
        else:
            raise RuntimeError('Local services did not become ready')
        ctx.update(backend_pid=identities[0]['pid'], frontend_pid=children[args.workers].pid,
                   source_identity_file=str(runtime / 'backend_ready.json'), supervisor_pid=os.getpid())
        ctx['backend_workers'] = [{'origin': f'http://{HOST}:{port}', 'pid': identity['pid'], 'source_identity_file': str(file)}
                                  for port, identity, file in zip(backend_ports, identities, identity_files)]
        if lan:
            ctx['frontend_lan_pid'] = children[args.workers + 1].pid
        (runtime / 'contexto.json').write_text(json.dumps(ctx, indent=2), encoding='utf-8')
        (ROOT / '.skilly-local-activo.tmp').write_text(json.dumps(ctx), encoding='utf-8')
        print(json.dumps({'completed': True, 'backend': backend, 'backend_workers': [item['origin'] for item in ctx['backend_workers']],
                          'frontend': frontend, 'frontend_lan': lan_origin, 'shared_access_cache': cache is not None,
                          'context': str(runtime / 'contexto.json'), 'isolated_database': True}), flush=True)
        STAGE = 'running'
        while not (runtime / 'stop.flag').exists():
            require(all(process.poll() is None for process in children))
            time.sleep(.5)
    finally:
        workers_closed = close_owned_workers(worker_records)
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        if started:
            pg(['-m', 'fast', '-w', 'stop'])
        (runtime / 'cierre.json').write_text(json.dumps({'own_children_closed': workers_closed, 'own_cluster_stopped': started, 'other_processes_touched': False}), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    start_parser = sub.add_parser('iniciar')
    for name in ('respaldo', 'cluster', 'conexion', 'admin'):
        start_parser.add_argument('--' + name, required=True)
    start_parser.add_argument('--backend-port', type=int, default=0)
    start_parser.add_argument('--frontend-port', type=int, default=0)
    start_parser.add_argument('--workers', type=int, choices=(1, 2), default=1)
    start_parser.add_argument('--backend2-port', type=int, default=0)
    start_parser.add_argument('--frontend-lan-host')
    start_parser.add_argument('--frontend-lan-port', type=int, default=0)
    start_parser.add_argument('--reutilizar-contexto')
    start_parser.add_argument('--cache-contexto')
    start_parser.add_argument('--cache-db', type=int, default=15)
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
    workers = ctx.get('backend_workers', [{'origin': ctx['backend_origin'], 'pid': ctx['backend_pid'], 'source_identity_file': ctx['source_identity_file']}])
    summaries = []
    for worker in workers:
        identity = read_json(worker['source_identity_file'])
        require(identity.get('project_root') == str(ROOT) and identity.get('wsgi_file') == str(ROOT / 'backend/config/wsgi.py') and identity.get('pid') == worker['pid'])
        require(isinstance(identity.get('product_sources'), dict) and bool(identity['product_sources']))
        for name in identity['product_sources']:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts)
            source = (ROOT / name).resolve()
            require(source.is_relative_to(ROOT / 'backend') and source.suffix == '.py')
            require(isinstance(identity['product_sources'][name], str) and re.fullmatch(r'[a-f0-9]{64}', identity['product_sources'][name]))
        current = all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in identity['product_sources'].items())
        summaries.append({'origin': worker['origin'], 'pid': worker['pid'], 'product_sources_current': current})
    print(json.dumps({'backend': ctx['backend_origin'], 'frontend': ctx['frontend_origin'], 'frontend_lan': ctx.get('frontend_lan_origin'),
                      'backend_pid': ctx['backend_pid'], 'frontend_pid': ctx['frontend_pid'], 'backend_workers': summaries,
                      'product_sources_current': all(item['product_sources_current'] for item in summaries), 'isolated_database': True,
                      'shared_access_cache': ctx.get('access_cache'), 'owns_cluster': ctx.get('owns_cluster'),
                      'cluster_dependency_context': ctx.get('cluster_dependency_context')}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        kind = type(error).__name__ if type(error).__name__ in ('ValueError', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError') else 'LocalEnvironmentError'
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': kind}), flush=True)
        raise SystemExit(1) from None
