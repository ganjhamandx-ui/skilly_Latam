"""Cliente REST Webpay Plus exclusivo para integración académica.
No contiene rutas ni credenciales de producción. No recibe datos de tarjetas.
"""
import ipaddress
import json
import ssl
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

HOST = 'https://webpay3gint.transbank.cl'
RUTA = '/rswebpaytransaction/api/webpay/v1.2/transactions'
CODIGO = '597055555532'
# Llave común del sandbox, publicada oficialmente por Transbank.
CLAVE = '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C'


class ErrorWebpay(Exception):
    pass


def url_pago_valida(url):
    partes = urlsplit(str(url))
    return (partes.scheme == 'https' and partes.hostname == 'webpay3gint.transbank.cl'
            and partes.port in (None, 443) and not partes.username and not partes.password
            and not partes.fragment and partes.path.startswith('/') and not partes.path.startswith('//'))


RUTA_RETORNO_WEBPAY = '/api/pagos/webpay/retorno/'


def url_retorno_webpay_valida(valor):
    """Retorno académico exacto: loopback explícito, sin ambigüedades de URL."""
    if (not isinstance(valor, str) or not valor
            or any(ord(caracter) <= 32 or ord(caracter) == 127 for caracter in valor)
            or any(caracter in valor for caracter in ('\\', '?', '#'))):
        return False
    try:
        partes = urlsplit(valor)
        host, puerto = partes.hostname, partes.port
        if (partes.scheme not in {'http', 'https'} or not host or '%' in host
                or partes.username is not None or partes.password is not None
                or puerto is None or not 1 <= puerto <= 65535
                or partes.path != RUTA_RETORNO_WEBPAY):
            return False
        return host == 'localhost' or ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def contexto_tls_webpay():
    """Verificacion de CA/hostname y TLS >= 1.2 explicitos para el proveedor."""
    contexto = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    contexto.check_hostname = True
    contexto.verify_mode = ssl.CERT_REQUIRED
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    return contexto


def peticion_webpay(metodo, token=None, datos=None):
    """Toda comunicación real utiliza TLS certificado, 12s máximo y endpoint fijo."""
    if token is not None and (not isinstance(token, str) or len(token) > 200
                              or not token or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-.' for c in token)):
        raise ErrorWebpay('Token Webpay inválido.')
    direccion = HOST + RUTA + (('/' + token) if token else '')
    cuerpo = json.dumps(datos).encode('utf-8') if datos is not None else None
    req = Request(direccion, data=cuerpo, method=metodo, headers={
        'Tbk-Api-Key-Id': CODIGO, 'Tbk-Api-Key-Secret': CLAVE,
        'Accept': 'application/json', 'Content-Type': 'application/json',
    })
    try:
        with urlopen(req, timeout=12, context=contexto_tls_webpay()) as r:
            payload = r.read(65536)
            respuesta = json.loads(payload)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as e:
        raise ErrorWebpay('No se pudo confirmar la operación con Webpay de integración.') from e
    if not isinstance(respuesta, dict):
        raise ErrorWebpay('Respuesta inválida del proveedor Webpay.')
    return respuesta


def iniciar(buy_order, session_id, monto, retorno):
    try:
        valor = Decimal(str(monto))
    except (ValueError, TypeError, InvalidOperation):
        raise ErrorWebpay('Monto de pago inválido.')
    if not valor.is_finite() or valor <= 0 or valor != valor.to_integral_value():
        raise ErrorWebpay('Webpay solo acepta montos CLP enteros positivos.')
    if len(buy_order) > 26 or len(session_id) > 61:
        raise ErrorWebpay('Identificadores de pago demasiado largos.')
    if not url_retorno_webpay_valida(retorno):
        raise ErrorWebpay('URL de retorno fuera del entorno académico habilitado.')
    respuesta = peticion_webpay('POST', datos={
        'buy_order': buy_order, 'session_id': session_id,
        'amount': int(valor), 'return_url': retorno,
    })
    token, url = respuesta.get('token'), respuesta.get('url')
    if not isinstance(token,str) or not 5 <= len(token) <= 200 or not url_pago_valida(url):
        raise ErrorWebpay('Webpay devolvió un destino o token no válido.')
    return {'token':token, 'url':url}


def confirmar(token):
    return peticion_webpay('PUT',token)


def autorizacion_valida(resultado, *, monto, buy_order, session_id):
    """Nunca aceptar el navegador como comprobante de autorización."""
    if not isinstance(resultado, dict): return False
    try:
        importe = Decimal(str(resultado.get('amount')))
        esperado = Decimal(str(monto))
    except (InvalidOperation, TypeError, ValueError):return False
    return (resultado.get('status') == 'AUTHORIZED'
            and type(resultado.get('response_code')) is int
            and resultado.get('response_code') == 0
            and resultado.get('buy_order') == buy_order
            and resultado.get('session_id') == session_id
            and importe.is_finite() and importe == esperado)
