"""HTTP local real por Vite/WSGI: sesiones, CSRF, CORS y catalogo preservado.

No prueba un telefono fisico. Solo escribe sesiones sinteticas y las cierra;
no accede a Webpay ni modifica servicios, documentos o reglas de negocio.
"""
import argparse
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import socket
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from uuid import uuid4

import entorno_local_skilly as launcher

ROOT = Path(__file__).resolve().parents[1]
CSRF = '/api/acceso/csrf/'
LOGIN = '/api/acceso/iniciar-sesion/'
LOGOUT = '/api/acceso/cerrar-sesion/'
SESSION = '/api/acceso/sesion-actual/'
CATALOG = '/api/marketplace/servicios/'
APP = '/src/App.jsx'
ALLOWED_PATHS = {'/', CSRF, LOGIN, LOGOUT, SESSION, CATALOG, APP,
                 CATALOG + '1/', CATALOG + '2/'}
FORBIDDEN_PORTS = {8000, 5173, 5432, 9000, 57647}


class VerificationRejected(Exception):
    pass


def require(condition):
    if not condition:
        raise VerificationRejected()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


class LocalHttp:
    def __init__(self, origins):
        self.origins = frozenset(origins)
        self.cookies = CookieJar()
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.cookies), NoRedirect())

    def request(self, origin, path, *, method='GET', headers=None, payload=None):
        require(origin in self.origins and path in ALLOWED_PATHS)
        require(method == 'GET' or (method == 'POST' and path in {LOGIN, LOGOUT}))
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(origin + path, data=body, method=method,
                          headers={'Accept': 'application/json', **(headers or {})})
        try:
            response = self.opener.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            content = response.read(2_000_001)
            require(len(content) <= 2_000_000)
            parsed = json.loads(content) if 'application/json' in response.headers.get('Content-Type', '') else None
            return response.code, response.headers, parsed, content


def validated_origin(value, host):
    url = urlsplit(value)
    require(url.scheme == 'http' and url.hostname == host and url.port is not None
            and 1024 <= url.port <= 65535 and url.port not in FORBIDDEN_PORTS
            and url.path == '' and not (url.username or url.password or url.query or url.fragment))
    return url


def current_sources(identity, pid):
    require(identity.get('project_root') == str(ROOT) and identity.get('pid') == pid
            and identity.get('wsgi_file') == str(ROOT / 'backend/config/wsgi.py'))
    sources = identity.get('product_sources')
    require(isinstance(sources, dict) and bool(sources))
    expected = {str(path.relative_to(ROOT)) for path in (ROOT / 'backend').rglob('*.py')
                if not path.name.startswith('test') and '__pycache__' not in path.parts}
    require(set(sources) == expected)
    for name, digest in sources.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts)
        source = (ROOT / name).resolve(strict=True)
        require(source.is_relative_to(ROOT / 'backend') and source.suffix == '.py'
                and isinstance(digest, str) and re.fullmatch(r'[a-f0-9]{64}', digest)
                and hashlib.sha256(source.read_bytes()).hexdigest() == digest)
    return sources


def tcp_bound_to(connection, host, port, *, windows):
    """Windows puede enumerar un TCP bound sin peer como CONN_NONE.

    Esto comprueba propiedad del extremo TCP, no afirma un estado LISTEN que
    el SO no haya comunicado. Las comprobaciones HTTP posteriores prueban que
    realmente sirve la aplicacion. Ninguna conexion con peer remoto se acepta.
    """
    return (connection.family == socket.AF_INET and connection.type == socket.SOCK_STREAM
            and (connection.status == 'LISTEN' or (windows and connection.status == 'NONE'))
            and not connection.raddr and connection.laddr
            and connection.laddr.ip == host and connection.laddr.port == port)


def owned_tcp_endpoint(pid, expected_argument, cwd, origin):
    """Verificar proceso/codigo y propiedad TCP local antes de enviar HTTP."""
    import psutil
    process = psutil.Process(pid)
    require(process.pid == pid and process.is_running() and Path(process.cwd()).resolve() == cwd.resolve())
    command = process.cmdline()
    executable = Path(process.exe()).resolve()
    if expected_argument.name == 'vite.js':
        require(executable.name.casefold() == 'node.exe' and bool(command)
                and Path(command[0]).resolve() == executable)
    else:
        allowed = {Path(sys.executable).resolve(), Path(getattr(sys, '_base_executable', sys.executable)).resolve(),
                   Path(psutil.Process(os.getpid()).exe()).resolve()}
        require(executable in allowed)
    require(any(Path(argument).resolve() == expected_argument.resolve()
                for argument in command[1:] if not argument.startswith('-')))
    url = urlsplit(origin)
    require(any(tcp_bound_to(connection, url.hostname, url.port, windows=os.name == 'nt')
                for connection in process.net_connections(kind='tcp')))


def checked_context(value):
    context = launcher.context_from(value)
    require(context.get('database_port') == 57647 and context.get('external_payments_and_mail') is False)
    run = Path(context['run_dir']).resolve()
    require(not launcher.native(run / 'stop.flag').exists())
    workers = context.get('backend_workers')
    require(isinstance(workers, list) and len(workers) == 2)
    manifests = []
    for index, worker in enumerate(workers):
        validated_origin(worker['origin'], '127.0.0.2')
        manifest = launcher.read_json(worker['source_identity_file'])
        manifests.append(current_sources(manifest, worker['pid']))
        runner = run / ('backend_local.py' if index == 0 else 'backend_local_2.py')
        owned_tcp_endpoint(worker['pid'], runner, ROOT / 'backend', worker['origin'])
    require(manifests[0] == manifests[1])
    fronts = [context['frontend_origin'], context['frontend_lan_origin']]
    validated_origin(fronts[0], '127.0.0.2')
    lan = launcher.lan_host(context['frontend_lan_host'])
    validated_origin(fronts[1], lan)
    vite = ROOT / 'frontend/node_modules/vite/bin/vite.js'
    for pid, origin in zip((context['frontend_pid'], context['frontend_lan_pid']), fronts):
        owned_tcp_endpoint(pid, vite, ROOT / 'frontend', origin)
    require(len({urlsplit(origin).port for origin in [*fronts, *(w['origin'] for w in workers)]}) == 4)
    return context, fronts, manifests[0]


def run(args):
    context, fronts, sources = checked_context(args.contexto)
    backup, runtime = Path(context['backup_root']).resolve(), Path(context['run_dir']).resolve()
    actor_path = Path(args.actores).resolve(strict=True)
    require(actor_path.is_relative_to(backup) and actor_path.name == 'fixture_privado.json')
    actor = launcher.read_json(actor_path).get('professional', {})
    require(isinstance(actor.get('email'), str) and actor['email'].endswith('@example.invalid')
            and isinstance(actor.get('password'), str) and bool(actor['password']))
    output = runtime / ('verificacion_acceso_' + uuid4().hex)
    launcher.native(output).mkdir(exist_ok=False)
    checks, errors, active = [], [], []
    stage = 'catalogue'

    def check(name, condition, status=None):
        checks.append({'name': name, 'passed': bool(condition), **({'status': status} if status is not None else {})})
        require(condition)

    def csrf(client, origin):
        status, _, body, _ = client.request(origin, CSRF)
        require(status == 200 and isinstance(body, dict) and isinstance(body.get('csrfToken'), str))
        return body['csrfToken']

    try:
        for index, origin in enumerate(fronts):
            label = 'desktop' if index == 0 else 'lan'
            client = LocalHttp([*fronts, *(worker['origin'] for worker in context['backend_workers'])])
            status, _, body, _ = client.request(origin, CATALOG)
            services = body.get('servicios', []) if isinstance(body, dict) else []
            ids = {service.get('id_servicio') for service in services}
            check(label + '_catalogo_preservado_sin_sinteticos', status == 200 and {1, 2} <= ids
                  and not ids.intersection(range(3, 11)), status)
            # Contrato actual del serializer de lista. La presentación del nombre
            # profesional en tarjetas se comprueba por UI, no por metadatos API.
            check(label + '_listado_sin_referencia_precio', bool(services)
                  and all('referencia_precio' not in service for service in services))
            for service_id in (1, 2):
                status, _, detail, _ = client.request(origin, CATALOG + str(service_id) + '/')
                check(label + '_detalle_con_precio_y_profesional_' + str(service_id), status == 200
                      and isinstance(detail, dict) and detail.get('id_servicio') == service_id
                      and bool(detail.get('referencia_precio')) and bool(detail.get('profesional', {}).get('nombres')), status)
            status, _, _, content = client.request(origin, APP)
            check(label + '_app_real_sin_texto_tecnico', status == 200 and b'solicitudEnCurso' in content
                  and b'Datos obtenidos de Django REST' not in content, status)
            stage = label + '_authentication'
            token = csrf(client, origin)
            credentials = {'correo': actor['email'], 'contrasena': actor['password']}
            unknown = 'http://192.0.2.99:' + str(urlsplit(origin).port)
            for suffix, request_origin, header in (
                ('sin_token', origin, None), ('token_incorrecto', origin, 'x' * len(token)),
                ('origen_ajeno', unknown, token),
            ):
                headers = {'Content-Type': 'application/json', 'Origin': request_origin}
                if header is not None:
                    headers['X-CSRFToken'] = header
                status, _, _, _ = client.request(origin, LOGIN, method='POST', headers=headers, payload=credentials)
                check(label + '_login_rechaza_' + suffix, status == 403, status)
            status, _, body, _ = client.request(origin, LOGIN, method='POST', payload=credentials,
                headers={'Content-Type': 'application/json', 'Origin': origin, 'X-CSRFToken': token})
            if status == 200:
                active.append((client, origin))
            check(label + '_login_real', status == 200 and isinstance(body, dict)
                  and body.get('usuario', {}).get('rol') == 'PROFESIONAL'
                  and body.get('usuario', {}).get('correo') == actor['email'], status)
            user_id = body['usuario']['id_usuario']
            cookies = [cookie for cookie in client.cookies if cookie.name == 'skilly_session']
            check(label + '_cookie_sesion_protegida', len(cookies) == 1
                  and cookies[0].domain == urlsplit(origin).hostname and cookies[0].path == '/'
                  and cookies[0].has_nonstandard_attr('HttpOnly')
                  and cookies[0].get_nonstandard_attr('SameSite', '').lower() == 'lax')
            status, _, session, _ = client.request(origin, SESSION)
            check(label + '_sesion_autenticada', status == 200 and session.get('usuario', {}).get('id_usuario') == user_id, status)
            if index == 0:
                status, _, session, _ = client.request(context['backend_workers'][1]['origin'], SESSION)
                check('sesion_compartida_entre_workers', status == 200 and session.get('usuario', {}).get('id_usuario') == user_id, status)
            backend = context['backend_origin']
            status, headers, _, _ = client.request(backend, CSRF, headers={'Origin': origin})
            check(label + '_cors_exacto', status == 200 and headers.get('Access-Control-Allow-Origin') == origin
                  and headers.get('Access-Control-Allow-Credentials') == 'true', status)
            status, headers, _, _ = client.request(backend, CSRF, headers={'Origin': unknown})
            check(label + '_cors_ajeno_no_autorizado', status == 200 and headers.get('Access-Control-Allow-Origin') is None, status)
            token = csrf(client, origin)
            status, _, _, _ = client.request(origin, LOGOUT, method='POST', payload={},
                headers={'Content-Type': 'application/json', 'Origin': origin, 'X-CSRFToken': 'x' * len(token)})
            check(label + '_logout_sin_csrf_valido_rechazado', status == 403, status)
            status, _, session, _ = client.request(origin, SESSION)
            check(label + '_sesion_conservada_tras_rechazo', status == 200 and session.get('usuario', {}).get('id_usuario') == user_id, status)
            token = csrf(client, origin)
            status, _, _, _ = client.request(origin, LOGOUT, method='POST', payload={},
                headers={'Content-Type': 'application/json', 'Origin': origin, 'X-CSRFToken': token})
            check(label + '_logout_real', status == 200, status)
            active.remove((client, origin))
            status, _, _, _ = client.request(origin, SESSION)
            check(label + '_sesion_cerrada', status == 403, status)
        stage = 'final_source_check'
        current = checked_context(args.contexto)[2]
        check('fuentes_producto_actuales_sin_cambios', current == sources)
    except Exception as error:
        errors.append({'stage': stage, 'error_type': type(error).__name__ if type(error).__name__ in {
            'VerificationRejected', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError', 'ValueError',
        } else 'LocalHTTPVerificationError'})
    finally:
        for client, origin in active:
            try:
                token = csrf(client, origin)
                status, _, _, _ = client.request(origin, LOGOUT, method='POST', payload={},
                    headers={'Content-Type': 'application/json', 'Origin': origin, 'X-CSRFToken': token})
                require(status == 200)
            except Exception:
                errors.append({'stage': 'session_cleanup', 'error_type': 'SessionCleanupFailed'})
    result = {'completed': not errors, 'passed': sum(item['passed'] for item in checks),
              'failed': sum(not item['passed'] for item in checks), 'checks': checks, 'errors': errors,
              'frontends': fronts, 'source_hashes': sources, 'isolated_database': True,
              'physical_android_verified': False, 'new_payments': 0, 'provider_requests': 0,
              'business_data_writes': 0, 'session_writes_real': True,
              'scope': 'HTTP real desde el PC por frontends desktop/LAN y dos WSGI; no acredita telefono fisico.'}
    with launcher.native(output / 'resultado.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'completed': result['completed'], 'passed': result['passed'], 'failed': result['failed'],
                      'errors': errors, 'output': str(output)}), flush=True)
    return 0 if result['completed'] else 1


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise VerificationRejected()


def main():
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument('--contexto', required=True)
    parser.add_argument('--actores', required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({'completed': False, 'stage': 'arguments_context_or_process', 'error_type': 'LocalVerificationRejected'}), flush=True)
        raise SystemExit(1) from None
