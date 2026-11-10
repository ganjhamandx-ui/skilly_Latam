"""Consulta GET del sandbox desde un checkout privado externo; nunca confirma pagos."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://webpay3gint.transbank.cl'
API = '/rswebpaytransaction/api/webpay/v1.2/transactions/'
STATES = {'INITIALIZED', 'AUTHORIZED', 'REVERSED', 'FAILED', 'NULLIFIED', 'PARTIALLY_NULLIFIED', 'CAPTURED'}


class InvalidCheckout(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirect rejected', headers, fp)


def load_checkout(value):
    file = Path(value)
    if not file.is_absolute() or (os.name == 'nt' and not re.fullmatch(r'[A-Za-z]:', file.drive)):
        raise InvalidCheckout()
    # Las evidencias superan MAX_PATH. El prefijo es local a esta operación;
    # no se cambian políticas de Windows ni se permiten rutas UNC de red.
    native = Path('\\\\?\\' + str(file.absolute())) if os.name == 'nt' else file
    file = native.resolve(strict=True)
    logical = Path(str(file).removeprefix('\\\\?\\')) if os.name == 'nt' else file
    if logical.is_relative_to(ROOT) or logical.name != 'checkout_privado.json' or file.stat().st_size > 65536:
        raise InvalidCheckout()
    data = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('ambiente') != 'TRANSBANK_INTEGRACION':
        raise InvalidCheckout()
    token = data.get('token')
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{5,200}', token):
        raise InvalidCheckout()
    url = urlsplit(data.get('url', ''))
    if url.scheme != 'https' or url.hostname != 'webpay3gint.transbank.cl' or url.port not in (None, 443) or url.username or url.password or url.fragment:
        raise InvalidCheckout()
    return file, token


def client_module():
    spec = importlib.util.spec_from_file_location('_skilly_webpay_client', ROOT / 'backend/pagos/webpay_cliente_e3.py')
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    if client.HOST != HOST or client.RUTA + '/' != API:
        raise InvalidCheckout()
    return client


def query_state(token, client, opener=None):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{5,200}', token):
        raise InvalidCheckout()
    context = client.contexto_tls_webpay()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname or context.minimum_version < ssl.TLSVersion.TLSv1_2:
        raise InvalidCheckout()
    transport = opener or build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=context))
    request = Request(HOST + API + token, method='GET', headers={
        'Tbk-Api-Key-Id': client.CODIGO, 'Tbk-Api-Key-Secret': client.CLAVE,
        'Accept': 'application/json',
    })
    result = {'completed': False, 'read_only': True, 'method': 'GET', 'provider': HOST,
              'production_provider': False, 'http_status': None, 'transaction_status': None,
              'authorization_verified': False}
    try:
        with transport.open(request, timeout=12) as response:
            result['http_status'] = response.status
            body = response.read(65537)
        if len(body) > 65536:
            result['error_code'] = 'RESPONSE_TOO_LARGE'
            return result
        result['response_sha256'] = hashlib.sha256(body).hexdigest()
        data = json.loads(body)
        state = data.get('status') if isinstance(data, dict) else None
        if state not in STATES:
            result['error_code'] = 'UNRECOGNIZED_STATE'
            return result
        result.update(completed=True, transaction_status=state)
        # Un estado AUTHORIZED no verifica monto, identidad o callback de SKILLY.
        return result
    except HTTPError as error:
        result.update(http_status=error.code, error_code='HTTP_ERROR')
    except (URLError, TimeoutError, OSError):
        result['error_code'] = 'TRANSPORT_ERROR'
    except (ValueError, TypeError):
        result['error_code'] = 'INVALID_RESPONSE'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', help='Ruta absoluta al checkout_privado.json externo; nunca el token.')
    args = parser.parse_args(argv)
    try:
        checkout, token = load_checkout(args.checkout)
        result = query_state(token, client_module())
        output = checkout.parent / ('estado_sandbox_' + uuid4().hex)
        output.mkdir(exist_ok=False)
        (output / 'resultado.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({**result, 'evidence': str(output)}, ensure_ascii=False))
        return 0 if result['completed'] else 1
    except Exception as error:
        kind = type(error).__name__ if type(error).__name__ in {'InvalidCheckout', 'FileNotFoundError', 'PermissionError', 'JSONDecodeError'} else 'SetupError'
        print(json.dumps({'completed': False, 'read_only': True, 'error_code': kind}))
        return 1


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
