"""Ensayo Android en una base nueva: no modifica ni detiene el SKILLY activo."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.1'
DATABASE_PORT = 57647
FORBIDDEN_PORTS = {8000, 5173, 5432, 9000, DATABASE_PORT}
STAGE = 'arguments'


def require(condition):
    if not condition:
        raise ValueError('Isolated Android configuration rejected')


def native(path):
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' and not str(path).startswith('\\\\?\\') else path


def read_json(path):
    file = native(path)
    require(file.stat().st_size < 4_000_000)
    return json.loads(file.read_text(encoding='utf-8'))


def free_port(excluded=()):
    for _ in range(30):
        with socket.socket() as listener:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((HOST, 0))
            port = listener.getsockname()[1]
        if port not in FORBIDDEN_PORTS and port not in excluded:
            return port
    raise ValueError('No isolated Android port')


def valid_database_name(name):
    return isinstance(name, str) and re.fullmatch(r'skilly_android_[a-f0-9]{20}', name) is not None


def context_from(path):
    file = Path(path).resolve(strict=True)
    ctx = read_json(file)
    run, backup = Path(ctx['run_dir']).resolve(), Path(ctx['backup_root']).resolve()
    require(file == run / 'contexto.json' and run.parent == backup
            and re.fullmatch(r'android_aislado_[a-f0-9]{20}', run.name) is not None and ctx['run_id'] == run.name
            and backup.name.startswith('SKILLY_recuperacion_')
            and not run.is_relative_to(ROOT) and ctx['project_root'] == str(ROOT)
            and ctx['database_port'] == DATABASE_PORT and valid_database_name(ctx['database_name'])
            and ctx['database_name'] == 'skilly_android_' + ctx['run_id'].removeprefix('android_aislado_'))
    for key in ('cluster', 'admin_file', 'app_file', 'source_dump'):
        require(Path(ctx[key]).resolve(strict=True).is_relative_to(backup))
    return ctx


def environment(ctx):
    from dotenv import dotenv_values
    app = dotenv_values(ctx['app_file'])
    require((app.get('POSTGRES_DB'), app.get('POSTGRES_SCHEMA'), app.get('POSTGRES_USER'),
             app.get('POSTGRES_HOST'), int(app.get('POSTGRES_PORT', 0)))
            == ('skilly', 'skilly', 'skilly_app', HOST, DATABASE_PORT))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('PG', 'POSTGRES_', 'ACCESO_')):
            env.pop(key)
    env.update({key: str(value) for key, value in app.items() if value is not None})
    env.update(POSTGRES_DB=ctx['database_name'], POSTGRES_HOST=HOST,
               DJANGO_SETTINGS_MODULE='android_settings', DJANGO_DEBUG='true',
               DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost,testserver',
               FRONTEND_ORIGIN=ctx['frontend_origin'], SKILLY_API_PROXY_TARGET=ctx['backend_origin'],
               PYTHONPATH=ctx['run_dir'] + os.pathsep + str(ROOT / 'backend'), PYTHONDONTWRITEBYTECODE='1')
    return env


def admin_connection(ctx, dbname='postgres', *, autocommit=False):
    from dotenv import dotenv_values
    import psycopg
    admin = dotenv_values(ctx['admin_file'])
    require(admin.get('POSTGRES_HOST', HOST) in (HOST, 'localhost')
            and int(admin.get('POSTGRES_PORT', 0)) == DATABASE_PORT)
    return psycopg.connect(dbname=dbname, user=admin['POSTGRES_USER'], password=admin['POSTGRES_PASSWORD'],
                           host=HOST, port=DATABASE_PORT, connect_timeout=8, autocommit=autocommit)


def check_cluster(ctx):
    with admin_connection(ctx) as connection:
        require(Path(connection.execute('SHOW data_directory').fetchone()[0]).resolve() == Path(ctx['cluster']).resolve())


def pg_command(ctx, executable, arguments):
    from dotenv import dotenv_values
    admin = dotenv_values(ctx['admin_file'])
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('PG'):
            env.pop(name)
    env.update(PGHOST=HOST, PGPORT=str(DATABASE_PORT), PGUSER=admin['POSTGRES_USER'],
               PGPASSWORD=admin['POSTGRES_PASSWORD'], PGCONNECT_TIMEOUT='8')
    process = subprocess.run([str(Path(ctx['pg_bin']) / executable), '--no-password', *arguments],
                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.PIPE, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    require(process.returncode == 0)


def settings_source(ctx):
    return ('from config.settings import *\nfrom pathlib import Path\n'
            'assert (DATABASES["default"]["NAME"], DATABASES["default"]["USER"], DATABASES["default"]["HOST"], str(DATABASES["default"]["PORT"])) == '
            + repr((ctx['database_name'], 'skilly_app', HOST, str(DATABASE_PORT))) + '\n'
            'EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"\n'
            'BASE_DIR=Path(' + repr(str(Path(ctx['run_dir']) / 'backend_files')) + ')\n'
            'MEDIA_ROOT=BASE_DIR/"media"\nCONN_MAX_AGE=0\nDATABASES["default"]["CONN_MAX_AGE"]=0\n'
            'ALLOWED_HOSTS=["127.0.0.1","localhost","testserver"]\n'
            'CACHES[ACCESO_CACHE_ALIAS]={"BACKEND":"django.core.cache.backends.locmem.LocMemCache","LOCATION":' + repr(ctx['run_id']) + '}\n'
            'LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"null":{"class":"logging.NullHandler"}},"root":{"handlers":["null"],"level":"CRITICAL"}}\n')


def backend_sources():
    excluded = {'venv', '.venv', 'env', '__pycache__', 'node_modules'}
    return {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in (ROOT / 'backend').rglob('*.py')
            if file.is_file() and not file.name.startswith('test')
            and not excluded.intersection(file.relative_to(ROOT / 'backend').parts)}


def seed(ctx):
    global STAGE
    os.environ.update(environment(ctx))
    sys.path[:0] = [ctx['run_dir'], str(ROOT / 'backend')]
    import django
    django.setup()
    from django.db import connection, connections, transaction
    from django.contrib.auth.hashers import make_password
    from django.utils import timezone
    from acceso.models import Usuario
    from profesionales.models import Profesional
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()')
        require(cursor.fetchone() == (ctx['database_name'], 'skilly', 'skilly_app', DATABASE_PORT))
    password, suffix = secrets.token_urlsafe(32), uuid4().hex
    with transaction.atomic():
        admin = Usuario.objects.create(correo='android-admin-' + suffix + '@example.invalid',
            password_hash=make_password(password), rol='ADMIN_SKILLY', estado='ACTIVO',
            fecha_creacion=timezone.now(), fecha_actualizacion=timezone.now())
        user = Usuario.objects.create(correo='android-other-' + suffix + '@example.invalid',
            password_hash=make_password(password), rol='PROFESIONAL', estado='ACTIVO',
            fecha_creacion=timezone.now(), fecha_actualizacion=timezone.now())
        professional = Profesional.objects.create(id_usuario=user, nombres='Profesional', apellidos='Prueba Android',
            titulo_profesional='Prueba aislada', resumen='Perfil auxiliar sintetico para permisos entre actores.',
            ubicacion='Santiago', estado_validacion='APROBADO', fecha_registro=timezone.now())
    fixture = {'admin': {'email': admin.correo, 'password': password, 'id': admin.pk},
               'professional_ui': {'email': user.correo, 'password': password, 'id': user.pk,
                                   'professional_id': professional.pk},
               'origin': ctx['frontend_origin'], 'backend_origin': ctx['backend_origin'],
               'control': secrets.token_urlsafe(36), 'run_id': ctx['run_id']}
    with (Path(ctx['run_dir']) / 'fixture_privado.json').open('x', encoding='utf-8') as stream:
        json.dump(fixture, stream)
    connections.close_all()


def worker(ctx):
    """Controles auxiliares exclusivos de este servidor de ensayo, fuera del producto."""
    os.environ.update(environment(ctx))
    sys.path[:0] = [ctx['run_dir'], str(ROOT / 'backend')]
    connect = socket.socket.connect
    def guarded(stream, address):
        require(isinstance(address, tuple) and address[0] in (HOST, 'localhost', '::1') and address[1] == DATABASE_PORT)
        return connect(stream, address)
    socket.socket.connect = guarded
    import datetime
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()')
        require(cursor.fetchone() == (ctx['database_name'], 'skilly', 'skilly_app', DATABASE_PORT))
    from django.utils import timezone
    real_now, clock = timezone.now, [None]
    timezone.now = lambda: clock[0] or real_now()
    from config.wsgi import application as product
    import config.wsgi as wsgi
    require(Path(wsgi.__file__).resolve() == ROOT / 'backend/config/wsgi.py')
    fixture = read_json(Path(ctx['run_dir']) / 'fixture_privado.json')
    def application(environ, start_response):
        endpoint = environ.get('PATH_INFO', '')
        if endpoint == '/api/__isolated/health' and environ.get('REQUEST_METHOD') == 'GET':
            endpoint = '/__isolated/health'
        if endpoint.startswith('/__isolated/'):
            status, data = '200 OK', {'isolated': True, 'run_id': ctx['run_id'], 'database_port': DATABASE_PORT,
                'database_name': ctx['database_name'], 'database_schema': 'skilly', 'database_role': 'skilly_app',
                'external_mail': False, 'external_payments': False, 'clock_simulated': clock[0] is not None}
            if endpoint == '/__isolated/clock' and environ.get('REQUEST_METHOD') == 'POST':
                if not hmac.compare_digest(environ.get('HTTP_X_ISOLATED_CONTROL', ''), fixture['control']):
                    status, data = '403 Forbidden', {}
                else:
                    try:
                        length = int(environ.get('CONTENT_LENGTH') or 0)
                        require(0 <= length <= 2048)
                        value = json.loads(environ['wsgi.input'].read(length)).get('now')
                        moment = datetime.datetime.fromisoformat(value) if value else None
                        require(moment is None or moment.tzinfo is not None)
                        require(moment is None or abs((moment - real_now()).total_seconds()) <= 366 * 86400)
                        clock[0] = moment
                    except (ValueError, TypeError, AttributeError):
                        status, data = '400 Bad Request', {}
            elif endpoint != '/__isolated/health' or environ.get('REQUEST_METHOD') != 'GET':
                status, data = '404 Not Found', {}
            body = json.dumps(data).encode()
            start_response(status, [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
            return [body]
        return product(environ, start_response)
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        request_queue_size = 64
    with make_server(HOST, ctx['backend_port'], application, server_class=Server, handler_class=Quiet) as server:
        (Path(ctx['run_dir']) / 'backend_ready.json').write_text(json.dumps({'pid': os.getpid(),
            'project_root': str(ROOT), 'wsgi_file': str(Path(wsgi.__file__).resolve()),
            'backend_port': ctx['backend_port'], 'database_name': ctx['database_name'],
            'database_schema': 'skilly', 'database_role': 'skilly_app', 'database_port': DATABASE_PORT,
            'product_sources': backend_sources()}), encoding='utf-8')
        server.serve_forever()


def close_children(records, ctx):
    import psutil
    for process, expected_file, expected_cwd in reversed(records):
        if process.poll() is not None:
            continue
        parent = psutil.Process(process.pid)
        for child in reversed([parent, *parent.children(recursive=True)]):
            try:
                command = child.cmdline()
                belongs = (child.create_time() >= parent.create_time()
                    and Path(child.cwd()).resolve() == expected_cwd.resolve()
                    and any(Path(arg).resolve() == expected_file.resolve() for arg in command[1:] if not arg.startswith('-')))
                if expected_file == Path(__file__).resolve():
                    allowed = {Path(sys.executable).resolve(), Path(sys._base_executable).resolve(),
                               Path(psutil.Process(os.getpid()).exe()).resolve()}
                    belongs = belongs and Path(child.exe()).resolve() in allowed and ctx['run_dir'] in ' '.join(command)
                else:
                    belongs = belongs and Path(child.exe()).resolve() == Path(ctx['node']).resolve()
                if not belongs:
                    continue
                child.terminate()
                try:
                    child.wait(10)
                except psutil.TimeoutExpired:
                    child.kill()
                    child.wait(5)
            except psutil.NoSuchProcess:
                pass


def available_context_ports(ctx):
    ports = (ctx.get('backend_port'), ctx.get('frontend_port'))
    require(all(type(port) is int and 1024 <= port <= 65535 and port not in FORBIDDEN_PORTS for port in ports)
            and ports[0] != ports[1]
            and ctx['backend_origin'] == f'http://{HOST}:{ports[0]}'
            and ctx['frontend_origin'] == f'http://localhost:{ports[1]}')
    listeners = []
    try:
        for port in ports:
            listener = socket.socket()
            listeners.append(listener)
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((HOST, port))
    finally:
        for listener in listeners:
            listener.close()


def resume_guards(ctx):
    """Solo lecturas; ningun seed, restore, migracion ni cambio de datos."""
    import psutil
    require(valid_database_name(ctx.get('database_name'))
            and ctx['database_name'] == 'skilly_android_' + ctx.get('run_id', '').removeprefix('android_aislado_')
            and ctx.get('restore_completed') is True and ctx.get('isolated') is True)
    run = Path(ctx['run_dir'])
    require(not (run / 'limpieza.json').exists())
    closure = read_json(run / 'cierre.json')
    require(closure.get('own_children_closed') is True)
    for key in ('backend_pid', 'backend_launcher_pid', 'frontend_pid', 'supervisor_pid'):
        require(type(ctx.get(key)) is int and ctx[key] > 0 and not psutil.pid_exists(ctx[key]))
    ready = read_json(run / 'backend_ready.json')
    require(ready.get('pid') == ctx['backend_pid'] and ready.get('project_root') == str(ROOT)
            and Path(ready.get('wsgi_file', '')).resolve() == ROOT / 'backend/config/wsgi.py')
    require((run / 'android_settings.py').read_text(encoding='utf-8') == settings_source(ctx))
    fixture = read_json(run / 'fixture_privado.json')
    require(fixture.get('run_id') == ctx['run_id'] and fixture.get('origin') == ctx['frontend_origin']
            and fixture.get('backend_origin') == ctx['backend_origin'])
    node = Path(ctx['node']).resolve(strict=True)
    require(node.name.casefold() == 'node.exe' and node.is_relative_to(Path(ctx['backup_root']).resolve())
            and hashlib.sha256(node.read_bytes()).hexdigest() == ctx['node_sha256'])
    pointer = ROOT / '.skilly-android-activo.tmp'
    if pointer.exists():
        current = read_json(pointer)
        require(current.get('run_id') == ctx['run_id'] and current.get('database_name') == ctx['database_name'])
    available_context_ports(ctx)
    check_cluster(ctx)
    with admin_connection(ctx) as connection:
        marker = connection.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s", [ctx['database_name']]).fetchone()
        require(marker == ('skilly_android:' + ctx['run_id'],))
    env = environment(ctx)
    import psycopg
    with psycopg.connect(dbname=ctx['database_name'], user=env['POSTGRES_USER'],
                        password=env['POSTGRES_PASSWORD'], host=HOST, port=DATABASE_PORT,
                        options='-c search_path=skilly,public -c default_transaction_read_only=on',
                        connect_timeout=8) as connection:
        require(connection.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()').fetchone()
                == (ctx['database_name'], 'skilly', 'skilly_app', DATABASE_PORT))
        preserved = [row[0] for row in connection.execute('SELECT to_jsonb(s)::text FROM skilly.servicio s WHERE id_servicio IN (1,2) ORDER BY id_servicio')]
        require(hashlib.sha256('\n'.join(preserved).encode()).hexdigest() == ctx['preserved_services_sha256'])


def serve_services(ctx, file, records, status):
    """Arranca solamente backend/frontend actuales y mantiene su supervisor vivo."""
    global STAGE
    run, script, env = Path(ctx['run_dir']), Path(__file__).resolve(), environment(ctx)
    STAGE = 'start_services'
    ctx['supervisor_pid'] = os.getpid()
    backend = subprocess.Popen([sys.executable, '-B', str(script), '--worker', str(file)], env=env,
        cwd=str(ROOT / 'backend'), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    records.append((backend, script, ROOT / 'backend'))
    ctx['backend_launcher_pid'] = backend.pid
    vite_file = ROOT / 'frontend/node_modules/vite/bin/vite.js'
    vite = subprocess.Popen([ctx['node'], str(vite_file), '--host', HOST, '--port', str(ctx['frontend_port']), '--strictPort'],
        env=env, cwd=str(ROOT / 'frontend'), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    records.append((vite, vite_file, ROOT / 'frontend'))
    ctx['frontend_pid'] = vite.pid
    file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
    STAGE = 'readiness'
    opener = build_opener(ProxyHandler({}))
    for _ in range(180):
        require(all(process.poll() is None for process, _, _ in records))
        try:
            with opener.open(ctx['backend_origin'] + '/__isolated/health', timeout=1) as response:
                health = json.load(response)
            require(health['run_id'] == ctx['run_id'] and health['database_name'] == ctx['database_name'])
            with opener.open(ctx['frontend_origin'] + '/api/__isolated/health', timeout=1) as response:
                require(json.load(response)['run_id'] == ctx['run_id'])
            break
        except (OSError, ValueError):
            time.sleep(.1)
    else:
        raise RuntimeError('Android services did not become ready')
    identity = read_json(run / 'backend_ready.json')
    ctx.update(backend_pid=identity['pid'], backend_launcher_pid=backend.pid,
               frontend_pid=vite.pid, supervisor_pid=os.getpid())
    file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
    (ROOT / '.skilly-android-activo.tmp').write_text(json.dumps(ctx), encoding='utf-8')
    status['ready'] = True
    print(json.dumps({'completed': True, 'context': str(file), 'backend': ctx['backend_origin'],
                      'frontend': ctx['frontend_origin'], 'database': ctx['database_name'],
                      'database_port': DATABASE_PORT, 'resumed_existing_database': bool(ctx.get('resume_count'))}), flush=True)
    STAGE = 'running'
    while not (run / 'stop.flag').exists():
        require(all(process.poll() is None for process, _, _ in records))
        time.sleep(.25)


def close_runtime(records, ctx, status):
    closed = False
    run = Path(ctx['run_dir'])
    try:
        close_children(records, ctx)
        import psutil
        ready_file = run / 'backend_ready.json'
        real_pid = read_json(ready_file).get('pid') if ready_file.exists() else None
        closed = all(process.poll() is not None for process, _, _ in records) and (real_pid is None or not psutil.pid_exists(real_pid))
    finally:
        (run / 'cierre.json').write_text(json.dumps({'own_children_closed': closed, 'main_environment_touched': False,
            'new_database_retained_for_explicit_cleanup': True, 'was_ready': status['ready']}), encoding='utf-8')


def resume(ctx):
    global STAGE
    STAGE = 'resume_guards'
    resume_guards(ctx)
    run, records, status = Path(ctx['run_dir']), [], {'ready': False}
    file = run / 'contexto.json'
    lock = run / 'reanudar.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        archive = run / ('reanudacion_' + uuid4().hex)
        archive.mkdir(exist_ok=False)
        with (archive / 'contexto_previo.json').open('x', encoding='utf-8') as stream:
            json.dump(ctx, stream, indent=2)
        for name in ('cierre.json', 'stop.flag', 'backend_ready.json'):
            source = run / name
            if source.exists():
                source.rename(archive / name)
        ctx['resume_count'] = int(ctx.get('resume_count', 0)) + 1
        ctx['last_resume_archive'] = str(archive)
        file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
        try:
            return serve_services(ctx, file, records, status)
        finally:
            close_runtime(records, ctx, status)
    finally:
        require(lock.read_text(encoding='utf-8') == str(os.getpid()))
        lock.unlink()


def start(args):
    global STAGE
    from psycopg import sql
    backup, cluster, app_file, admin_file, dump, node = [Path(value).resolve(strict=True)
        for value in (args.respaldo, args.cluster, args.conexion, args.admin, args.respaldo_db, args.node)]
    require(backup.name.startswith('SKILLY_recuperacion_') and not backup.is_relative_to(ROOT))
    require(all(file.is_relative_to(backup) for file in (cluster, app_file, admin_file, dump, node)))
    require(cluster.name == 'cluster' and cluster.parent.name.startswith('ensayo_aislado_')
            and admin_file.parent == cluster.parent and node.name.casefold() == 'node.exe')
    proof = read_json(dump.parent / 'resultado.json')
    require(proof.get('completed') is True and proof.get('restore_verified') is True
            and hashlib.sha256(dump.read_bytes()).hexdigest() == proof.get('dump_sha256'))
    run_id = 'android_aislado_' + uuid4().hex[:20]
    run = backup / run_id
    run.mkdir(exist_ok=False)
    backend_port = free_port()
    frontend_port = free_port({backend_port})
    ctx = {'run_id': run_id, 'run_dir': str(run), 'backup_root': str(backup), 'project_root': str(ROOT),
        'database_name': 'skilly_android_' + run_id.removeprefix('android_aislado_'), 'database_port': DATABASE_PORT,
        'cluster': str(cluster), 'admin_file': str(admin_file), 'app_file': str(app_file), 'source_dump': str(dump),
        'source_dump_sha256': proof['dump_sha256'], 'pg_bin': str(Path(args.pg_bin).resolve(strict=True)),
        'node': str(node), 'node_sha256': hashlib.sha256(node.read_bytes()).hexdigest(),
        'backend_port': backend_port, 'frontend_port': frontend_port,
        'backend_origin': f'http://{HOST}:{backend_port}', 'frontend_origin': f'http://localhost:{frontend_port}',
        'isolated': True, 'original_database_untouched': True, 'external_mail': False, 'external_payments': False}
    file = run / 'contexto.json'
    file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
    records, status = [], {'ready': False}
    try:
        STAGE = 'cluster_identity'
        check_cluster(ctx)
        STAGE = 'new_database'
        with admin_connection(ctx, autocommit=True) as connection:
            require(connection.execute('SELECT 1 FROM pg_database WHERE datname=%s', [ctx['database_name']]).fetchone() is None)
            connection.execute(sql.SQL('CREATE DATABASE {} OWNER skilly_app TEMPLATE template0').format(sql.Identifier(ctx['database_name'])))
            connection.execute(sql.SQL('COMMENT ON DATABASE {} IS {}').format(
                sql.Identifier(ctx['database_name']), sql.Literal('skilly_android:' + run_id)))
        STAGE = 'restore_new_database'
        pg_command(ctx, 'pg_restore.exe', ['--exit-on-error', '--no-privileges', '--dbname=' + ctx['database_name'], str(dump)])
        with admin_connection(ctx, ctx['database_name']) as connection:
            require(connection.execute('SELECT id_servicio FROM skilly.servicio ORDER BY id_servicio').fetchall() == [(1,), (2,)])
            preserved = [row[0] for row in connection.execute('SELECT to_jsonb(s)::text FROM skilly.servicio s WHERE id_servicio IN (1,2) ORDER BY id_servicio')]
            ctx['preserved_services_sha256'] = hashlib.sha256('\n'.join(preserved).encode()).hexdigest()
        with admin_connection(ctx, autocommit=True) as connection:
            connection.execute(sql.SQL('COMMENT ON DATABASE {} IS {}').format(
                sql.Identifier(ctx['database_name']), sql.Literal('skilly_android:' + run_id)))
        ctx['restore_completed'] = True
        file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
        STAGE = 'private_files'
        from entorno_local_skilly import copy_private_files
        ctx['private_files'] = copy_private_files(backup, run)
        (run / 'android_settings.py').write_text(settings_source(ctx), encoding='utf-8')
        file.write_text(json.dumps(ctx, indent=2), encoding='utf-8')
        env = environment(ctx)
        STAGE = 'seed_auxiliary_actors'
        result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--seed', str(file)],
            cwd=str(ROOT / 'backend'), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        require(result.returncode == 0)
        return serve_services(ctx, file, records, status)
    finally:
        close_runtime(records, ctx, status)


def cleanup(ctx):
    global STAGE
    require(valid_database_name(ctx.get('database_name'))
            and ctx.get('run_id', '').startswith('android_aislado_')
            and ctx['database_name'] == 'skilly_android_' + ctx['run_id'].removeprefix('android_aislado_'))
    from psycopg import sql
    import psutil
    run = Path(ctx['run_dir'])
    closure = read_json(run / 'cierre.json')
    require(closure.get('own_children_closed') is True)
    for key in ('backend_pid', 'backend_launcher_pid', 'frontend_pid', 'supervisor_pid'):
        require(not ctx.get(key) or not psutil.pid_exists(ctx[key]))
    check_cluster(ctx)
    STAGE = 'cleanup_database_snapshot'
    with admin_connection(ctx) as connection:
        marker = connection.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s", [ctx['database_name']]).fetchone()
        require(marker == ('skilly_android:' + ctx['run_id'],))
    if ctx.get('restore_completed') is True:
        with admin_connection(ctx, ctx['database_name']) as connection:
            preserved = [row[0] for row in connection.execute('SELECT to_jsonb(s)::text FROM skilly.servicio s WHERE id_servicio IN (1,2) ORDER BY id_servicio')]
            require(hashlib.sha256('\n'.join(preserved).encode()).hexdigest() == ctx['preserved_services_sha256'])
    dump = run / 'datos_android_antes_retirada.dump'
    require(not dump.exists())
    pg_command(ctx, 'pg_dump.exe', ['--format=custom', '--file=' + str(dump), '--dbname=' + ctx['database_name']])
    with admin_connection(ctx, autocommit=True) as connection:
        require(connection.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', [ctx['database_name']]).fetchone()[0] == 0)
        connection.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(ctx['database_name'])))
        require(connection.execute('SELECT 1 FROM pg_database WHERE datname=%s', [ctx['database_name']]).fetchone() is None)
    report = {'completed': True, 'new_database_removed': ctx['database_name'], 'triggers_disabled': False,
              'original_database_touched': False, 'data_snapshot': str(dump),
              'data_snapshot_sha256': hashlib.sha256(dump.read_bytes()).hexdigest(), 'data_snapshot_restore_verified': False,
              'preserved_services_unchanged': True if ctx.get('restore_completed') else None,
              'private_files_and_evidence_retained': True}
    (run / 'limpieza.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Android runtime arguments rejected')


def main():
    global STAGE
    if len(sys.argv) == 3 and sys.argv[1] in ('--worker', '--seed'):
        ctx = context_from(sys.argv[2])
        return worker(ctx) if sys.argv[1] == '--worker' else seed(ctx)
    parser = PrivateParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('iniciar')
    for name in ('respaldo', 'cluster', 'conexion', 'admin', 'respaldo-db', 'node'):
        create.add_argument('--' + name, required=True)
    create.add_argument('--pg-bin', default=r'C:\Program Files\PostgreSQL\18\bin')
    for name in ('describir', 'cerrar', 'limpiar', 'reanudar'):
        command = sub.add_parser(name)
        command.add_argument('--contexto', required=True)
        if name == 'limpiar':
            command.add_argument('--confirmar-base-nueva', action='store_true', required=True)
    args = parser.parse_args()
    if args.action == 'iniciar':
        return start(args)
    ctx = context_from(args.contexto)
    if args.action == 'reanudar':
        return resume(ctx)
    if args.action == 'limpiar':
        return cleanup(ctx)
    if args.action == 'cerrar':
        with (Path(ctx['run_dir']) / 'stop.flag').open('x', encoding='utf-8') as stream:
            stream.write('Close only the dedicated Android rehearsal services.\n')
        print(json.dumps({'stop_requested': True, 'context': args.contexto}))
    else:
        print(json.dumps({key: ctx.get(key) for key in ('run_id', 'database_name', 'database_port', 'backend_origin',
            'frontend_origin', 'backend_pid', 'frontend_pid', 'supervisor_pid')}))


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception as error:
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': 'AndroidEnvironmentError'}), flush=True)
        raise SystemExit(1) from None
