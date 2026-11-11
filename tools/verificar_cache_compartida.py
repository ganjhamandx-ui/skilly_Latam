"""Integracion HTTP/Django/PostgreSQL/Redis de copia con dos procesos, sin mocks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from uuid import uuid4

from cache_local_skilly import cache_process, redis_connection

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.2'
FORBIDDEN = {8000, 5173, 5432}
STAGE = 'arguments'
PATHS = {name: '/api/acceso/' + path + '/' for name, path in {
    'csrf': 'csrf', 'login': 'iniciar-sesion', 'recover': 'solicitar-recuperacion',
    'reset': 'restablecer-contrasena', 'logout': 'cerrar-sesion', 'session': 'sesion-actual',
}.items()}


def require(condition):
    if not condition:
        raise ValueError('Shared cache verification rejected')


def native(path):
    path = Path(path)
    return Path('\\\\?\\' + str(path)) if os.name == 'nt' and not str(path).startswith('\\\\?\\') else path


def read_json(path):
    file = native(path)
    require(file.stat().st_size < 4_000_000)
    return json.loads(file.read_text(encoding='utf-8'))


def free_port(excluded):
    for _ in range(30):
        with socket.socket() as server:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            server.bind((HOST, 0))
            port = server.getsockname()[1]
        if port not in FORBIDDEN | set(excluded):
            return port
    raise ValueError('No isolated port')


def worker(path):
    """Solo el padre validado crea estos descriptores privados; sin endpoints de ensayo."""
    global STAGE
    config = read_json(path)
    run = Path(config['run_dir']).resolve()
    require(Path(path).resolve().parent == run and config['host'] == HOST)
    require(run.name.startswith('cache_compartida_') and run.parent.name.startswith('SKILLY_recuperacion_'))
    from dotenv import dotenv_values
    database = dotenv_values(config['database_config'])
    require((database['POSTGRES_DB'], database['POSTGRES_SCHEMA'], database['POSTGRES_USER']) == ('skilly', 'skilly', 'skilly_app'))
    port = int(database['POSTGRES_PORT'])
    require(port == config['database_port'] and port not in FORBIDDEN)
    cache = read_json(config['cache_config'])
    require(cache['host'] == '127.0.0.1' and cache['port'] not in FORBIDDEN)
    require(1024 <= config['port'] <= 65535 and config['port'] not in FORBIDDEN | {port, cache['port']})
    for name in list(os.environ):
        if name.startswith(('PG', 'POSTGRES_')):
            os.environ.pop(name)
    os.environ.update({key: str(value) for key, value in database.items() if value is not None})
    origin = f'http://{HOST}:{config["port"]}'
    os.environ.update({
        'POSTGRES_HOST': '127.0.0.1', 'DJANGO_SETTINGS_MODULE': 'cache_shared_settings',
        'DJANGO_DEBUG': 'true', 'DJANGO_ALLOWED_HOSTS': HOST, 'FRONTEND_ORIGIN': origin,
        'ACCESO_CACHE_BACKEND': 'acceso.cache.RedisIntentosCache',
        'ACCESO_CACHE_LOCATION': 'redis://:' + quote(cache['password'], safe='') + '@127.0.0.1:' + str(cache['port']) + '/0',
        'ACCESO_CACHE_KEY_PREFIX': config['namespace'], 'ACCESO_CACHE_TIMEOUT': '0.5',
    })
    for scope in ('LOGIN', 'RECUPERAR', 'RESTABLECER'):
        for suffix in ('IP', 'IDENTIDAD_IP'):
            os.environ['ACCESO_' + scope + '_' + suffix] = '3/5'
    sys.path[:0] = [str(run), str(ROOT / 'backend')]
    connect = socket.socket.connect
    def guarded(stream, address):
        require(isinstance(address, tuple) and address[0] in ('127.0.0.1', 'localhost', '::1')
                and address[1] in (port, cache['port']))
        return connect(stream, address)
    socket.socket.connect = guarded
    STAGE = 'worker_django'
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    require(settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()')
        require(cursor.fetchone() == ('skilly', 'skilly', 'skilly_app', port))
    from config.wsgi import application
    import config.wsgi as module
    require(Path(module.__file__).resolve() == ROOT / 'backend/config/wsgi.py')
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        request_queue_size = 64
    with make_server(HOST, config['port'], application, server_class=Server, handler_class=Quiet) as httpd:
        ready = {'pid': os.getpid(), 'port': config['port'], 'database_port': port,
                 'cache_backend': settings.CACHES['acceso_intentos']['BACKEND'],
                 'namespace': config['namespace'], 'wsgi_file': str(Path(module.__file__).resolve()),
                 'settings_sha256': hashlib.sha256((run / 'cache_shared_settings.py').read_bytes()).hexdigest()}
        (run / ('worker_ready_' + str(config['port']) + '.json')).write_text(json.dumps(ready), encoding='utf-8')
        httpd.serve_forever()


class Session:
    def __init__(self, origin):
        url = urlsplit(origin)
        require(url.scheme == 'http' and url.hostname == HOST and url.port is not None
                and 1024 <= url.port <= 65535 and url.port not in FORBIDDEN
                and not (url.username or url.password or url.query or url.fragment) and url.path in ('', '/'))
        self.origin, self.csrf = origin, None
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, endpoint, data=None):
        require(endpoint in PATHS.values())
        headers = {'Accept': 'application/json', 'Origin': self.origin}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers.update({'Content-Type': 'application/json', 'X-CSRFToken': self.csrf or ''})
        req = Request(self.origin + endpoint, data=body, headers=headers, method='POST' if body is not None else 'GET')
        try:
            response = self.opener.open(req, timeout=12)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read(16385)
            require(len(payload) <= 16384)
            parsed = json.loads(payload)
            status, wait = response.status, response.headers.get('Retry-After')
        if endpoint == PATHS['csrf'] and status == 200:
            self.csrf = parsed['csrfToken']
        return status, parsed, wait

    def token(self):
        require(self.request(PATHS['csrf'])[0] == 200)
        return self


def wait_window(client, window=5):
    seconds, micros = client.time()
    remaining = window - (seconds % window) - micros / 1_000_000
    if remaining < window - .2:
        time.sleep(remaining + .08)


def stop_workers(records):
    import psutil
    for process, descriptor in reversed(records):
        candidates = []
        try:
            candidates = [*psutil.Process(process.pid).children(recursive=True), psutil.Process(process.pid)]
        except psutil.Error:
            pass
        for candidate in candidates:
            try:
                if any(Path(arg).resolve() == descriptor for arg in candidate.cmdline()[1:] if not arg.startswith('-')):
                    candidate.terminate()
                    try:
                        candidate.wait(5)
                    except psutil.TimeoutExpired:
                        candidate.kill()
                        candidate.wait(5)
            except psutil.NoSuchProcess:
                pass
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def verify(args):
    global STAGE
    from dotenv import dotenv_values
    import psycopg
    import psutil
    from entorno_local_skilly import context_from, validate_database
    context_path = Path(args.contexto).resolve(strict=True)
    context = context_from(context_path)
    backup = Path(context['backup_root']).resolve()
    cache_file = Path(args.cache_contexto).resolve(strict=True)
    cache = read_json(cache_file)
    require(cache_file.is_relative_to(backup) and cache_file.parent == Path(cache['run_dir']).resolve())
    cache_process(cache, backup)
    actor_file = Path(args.actores).resolve(strict=True)
    db_file = Path(args.conexion).resolve(strict=True)
    require(actor_file.is_relative_to(backup) and db_file.is_relative_to(backup))
    actor = read_json(actor_file)['professional']
    require(actor['email'].endswith('@example.invalid') and bool(actor['password']))
    database = dotenv_values(db_file)
    database_port = validate_database(database)
    require(database_port == context['database_port'] and database_port != cache['port'])
    admin_files = list(backup.glob('ensayo_aislado_*/conexion_aislada.env'))
    require(len(admin_files) == 1)
    admin_file = admin_files[0]
    admin = dotenv_values(admin_file)
    require(int(admin['POSTGRES_PORT']) == database_port)
    with psycopg.connect(dbname='postgres', user=admin['POSTGRES_USER'], password=admin['POSTGRES_PASSWORD'], host='127.0.0.1', port=database_port, connect_timeout=5) as connection:
        require(Path(connection.execute('SHOW data_directory').fetchone()[0]).resolve() == admin_file.parent / 'cluster')
    client = redis_connection(cache)
    require(client.ping() is True and client.dbsize() == 0
            and all(int(stats.get('keys', 0)) == 0 for stats in client.info('keyspace').values()))
    require(int(client.info('server').get('process_id', 0)) == cache['pid'])
    namespace = 'skilly-cache-test-' + uuid4().hex[:24]
    require(namespace != cache.get('prefix'))
    run = backup / ('cache_compartida_' + uuid4().hex[:16])
    run.mkdir(exist_ok=False)
    source_files = [ROOT / path for path in ['backend/acceso/cache.py', 'backend/acceso/intentos.py', 'backend/acceso/checks.py', 'backend/config/cache_acceso.py', 'backend/config/settings.py']]
    source_hashes = {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest() for file in source_files}
    checks, errors, records = [], [], []
    stopped, restarted = False, False
    binary_digest = hashlib.sha256(Path(cache['binary']).read_bytes()).hexdigest()
    config_digest = hashlib.sha256(Path(cache['config']).read_bytes()).hexdigest()
    def check(name, condition, **metadata):
        checks.append({'name': name, 'passed': bool(condition), **metadata})
        require(condition)
    def restart_cache():
        nonlocal cache, restarted
        binary, config = Path(cache['binary']).resolve(), Path(cache['config']).resolve()
        require(hashlib.sha256(binary.read_bytes()).hexdigest() == binary_digest
                and hashlib.sha256(config.read_bytes()).hexdigest() == config_digest)
        process = subprocess.Popen([str(binary), str(config)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        updated = {**cache, 'pid': process.pid, 'created': psutil.Process(process.pid).create_time()}
        until = time.monotonic() + 15
        while time.monotonic() < until:
            require(process.poll() is None)
            try:
                connection = redis_connection(updated)
                if connection.ping():
                    connection.close()
                    break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Own cache restart failed')
        cache_process(updated, backup)
        replacement = cache_file.parent / ('contexto_reinicio_' + uuid4().hex + '.tmp')
        with replacement.open('x', encoding='utf-8') as stream:
            json.dump(updated, stream)
        os.replace(replacement, cache_file)
        cache, restarted = updated, True
    try:
        STAGE = 'workers'
        settings_source = '\n'.join([
            'from config.settings import *',
            'from pathlib import Path',
            'EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"',
            'BASE_DIR=Path(' + repr(str(run / 'backend_files')) + ')',
            'MEDIA_ROOT=BASE_DIR/"media"',
            'LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"null":{"class":"logging.NullHandler"}},"root":{"handlers":["null"],"level":"CRITICAL"}}',
        ]) + '\n'
        compile(settings_source, 'cache_shared_settings', 'exec')
        (run / 'cache_shared_settings.py').write_text(settings_source, encoding='utf-8')
        ports = []
        for index in range(2):
            port = free_port([database_port, cache['port'], *ports])
            ports.append(port)
            descriptor = run / ('worker_' + str(index) + '.json')
            descriptor.write_text(json.dumps({'run_dir': str(run), 'host': HOST, 'port': port,
                'database_port': database_port, 'database_config': str(db_file),
                'cache_config': str(cache_file), 'namespace': namespace}), encoding='utf-8')
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', str(descriptor)],
                cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            records.append((process, descriptor))
        identities = []
        for port in ports:
            ready = run / ('worker_ready_' + str(port) + '.json')
            until = time.monotonic() + 20
            while time.monotonic() < until:
                require(all(process.poll() is None for process, _ in records))
                if ready.is_file():
                    identities.append(read_json(ready))
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('Workers not ready')
        check('dos_procesos_http_producto_real', len({item['pid'] for item in identities}) == 2
              and all(item['wsgi_file'] == str(ROOT / 'backend/config/wsgi.py') and item['namespace'] == namespace for item in identities))
        origins = [f'http://{HOST}:{port}' for port in ports]
        sessions = [Session(origin).token() for origin in origins]
        wrong = secrets.token_urlsafe(24)
        login_missing = {'correo': 'missing-' + uuid4().hex + '@example.invalid', 'contrasena': wrong}
        STAGE = 'shared_quota'
        wait_window(client)
        sequence = [sessions[index % 2].request(PATHS['login'], login_missing) for index in range(3)]
        before_ttl = {key: client.pttl(key) for key in client.scan_iter(match=namespace + ':*')}
        sequence.append(sessions[1].request(PATHS['login'], login_missing))
        after_ttl = {key: client.pttl(key) for key in before_ttl}
        check('cuota_login_compartida_y_bloqueo_temporal', [row[0] for row in sequence] == [400, 400, 400, 429]
              and 1 <= int(sequence[-1][2]) <= 5, statuses=[row[0] for row in sequence])
        tracked_ttl = {key: value for key, value in before_ttl.items() if value > 0}
        check('rechazo_no_prolonga_ttl', bool(tracked_ttl) and all(
              after_ttl[key] == -2 or 0 <= after_ttl[key] <= value for key, value in tracked_ttl.items()),
              keys_compared=len(tracked_ttl))
        STAGE = 'concurrency'
        concurrent_sessions = [Session(origins[index % 2]).token() for index in range(30)]
        wait_window(client)
        with ThreadPoolExecutor(max_workers=30) as pool:
            results = list(pool.map(lambda session: session.request(PATHS['login'], login_missing)[0], concurrent_sessions))
        check('treinta_intentos_concurrentes_exactamente_tres_admitidos', results.count(400) == 3 and results.count(429) == 27,
              admitted=results.count(400), blocked=results.count(429), total=len(results))
        wait_window(client)
        check('login_recuperado_tras_caducidad_real', sessions[1].request(PATHS['login'], login_missing)[0] == 400)
        STAGE = 'recovery_uniformity'
        recovery_bodies, recovery_statuses = [], []
        for email in [actor['email'], login_missing['correo']]:
            wait_window(client)
            rows = [sessions[index % 2].request(PATHS['recover'], {'correo': email}) for index in range(4)]
            recovery_statuses.append([row[0] for row in rows])
            recovery_bodies.append([row[1] for row in rows[:3]])
        check('recuperacion_sin_enumeracion_entre_workers', recovery_statuses == [[200, 200, 200, 429]] * 2
              and recovery_bodies[0] == recovery_bodies[1], statuses=recovery_statuses)
        STAGE = 'reset_quota'
        reset = {'token': 'invalid-synthetic-' + uuid4().hex, 'nueva_contrasena': wrong, 'confirmar_contrasena': wrong}
        wait_window(client)
        reset_statuses = [sessions[index % 2].request(PATHS['reset'], reset)[0] for index in range(4)]
        check('reset_comparte_limite_sin_cambiar_password', reset_statuses == [400, 400, 400, 429], statuses=reset_statuses)
        STAGE = 'legitimate_session'
        wait_window(client)
        real_login = {'correo': actor['email'], 'contrasena': actor['password']}
        logged = sessions[0].request(PATHS['login'], real_login)
        user = logged[1].get('usuario', {})
        check('login_legitimo_real', logged[0] == 200 and type(user.get('id_usuario')) is int
              and user.get('correo', '').casefold() == actor['email'].casefold() and user.get('rol') == 'PROFESIONAL')
        sessions[0].origin = origins[1]
        current_session = sessions[0].request(PATHS['session'])
        check('sesion_compartida_en_otro_proceso', current_session[0] == 200
              and current_session[1].get('usuario', {}).get('id_usuario') == user['id_usuario']
              and current_session[1].get('usuario', {}).get('correo', '').casefold() == actor['email'].casefold())
        sessions[0].token()
        check('logout_real', sessions[0].request(PATHS['logout'], {})[0] == 200)
        check('sesion_revocada_tras_logout', sessions[0].request(PATHS['session'])[0] == 403)
        ttl = [client.pttl(key) for key in client.scan_iter(match=namespace + ':*')]
        check('claves_limitadas_por_ttl_real', bool(ttl) and any(value >= 0 for value in ttl)
              and all(value == -2 or 0 <= value <= 5000 for value in ttl), keys=len(ttl))
        STAGE = 'cache_failure'
        (run / 'cache_context_before.json').write_text(json.dumps(cache), encoding='utf-8')
        owned = cache_process(cache, backup)
        require(int(client.info('server').get('process_id', 0)) == owned.pid)
        # Un servidor dedicado vacio al principio; no limpiar bases ni claves ajenas.
        require(all(database == 'db0' or int(stats.get('keys', 0)) == 0
                    for database, stats in client.info('keyspace').items()))
        require(all(key.startswith(namespace + ':') for key in client.scan_iter()))
        client.close()
        owned.terminate()
        owned.wait(10)
        stopped = True
        down_rows = []
        for endpoint, data in [(PATHS['login'], login_missing), (PATHS['recover'], {'correo': login_missing['correo']}), (PATHS['reset'], reset)]:
            status, body, wait = sessions[1].request(endpoint, data)
            serialized = json.dumps(body)
            down_rows.append((status, wait))
            require(cache['password'] not in serialized and 'redis://' not in serialized and 'Traceback' not in serialized)
        check('cache_caida_falla_cerrado_login_recuperar_reset', down_rows == [(503, '30')] * 3,
              statuses=[row[0] for row in down_rows])
        STAGE = 'cache_restart'
        restart_cache()
        client = redis_connection(cache)
        check('cache_propia_reiniciada_y_autenticada', client.ping() is True)
        recovered_status = sessions[1].request(PATHS['login'], real_login)[0]
        check('login_legitimo_recuperado_despues_reinicio', recovered_status == 200, status=recovered_status)
        sessions[1].token()
        check('logout_despues_reinicio', sessions[1].request(PATHS['logout'], {})[0] == 200)
        STAGE = 'complete'
    except Exception as error:
        errors.append({'stage': STAGE, 'error_type': type(error).__name__ if type(error).__name__ in ['ValueError', 'TimeoutError', 'ConnectionError'] else 'VerificationError'})
    finally:
        if stopped and not restarted:
            try:
                restart_cache()
            except Exception:
                errors.append({'stage': 'restore_cache', 'error_type': 'CacheRestoreFailed'})
        stop_workers(records)
        unchanged = all(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest for relative, digest in source_hashes.items())
        result = {'completed': not errors and all(row['passed'] for row in checks) and unchanged,
                  'passed': sum(row['passed'] for row in checks), 'failed': sum(not row['passed'] for row in checks),
                  'checks': checks, 'errors': errors, 'product_sources_unchanged': unchanged, 'source_hashes': source_hashes,
                  'workers_closed': True, 'cache_restored': not stopped or restarted,
                  'scope': 'Dos procesos Django HTTP, PostgreSQL de copia y Redis/Memurai reales; sin mocks; correo locmem, reset invalido sin cambiar contrasena.',
                  'normal_cache_namespace_modified': False, 'original_database_modified': False,
                  'external_payments': False, 'external_mail': False}
        (run / 'resultado.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'completed': result['completed'], 'passed': result['passed'], 'failed': result['failed'],
                          'errors': errors, 'cache_restored': result['cache_restored'], 'evidence': str(run)}))
    return 0 if result['completed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contexto')
    parser.add_argument('--cache-contexto')
    parser.add_argument('--actores')
    parser.add_argument('--conexion')
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    require(all([args.contexto, args.cache_contexto, args.actores, args.conexion]))
    return verify(args)


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': type(error).__name__ if type(error).__name__ in ['ValueError', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError'] else 'VerificationSetupError'}), flush=True)
        raise SystemExit(1) from None
