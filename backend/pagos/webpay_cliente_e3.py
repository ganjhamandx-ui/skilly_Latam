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
    """Comunica fallos de validación o comunicación del cliente de integración."""
    pass


def url_pago_valida(url):
    """Comprueba que el destino de pago pertenezca al host HTTPS de integración.

    Args:
        url (str): URL entregada por Webpay, convertida a texto para analizarla.

    Returns:
        bool: Si usa el host fijo, puerto HTTPS normal, ruta absoluta simple,
        sin credenciales ni fragmento. No restringe la consulta de la URL.

    Raises:
        ValueError: Si urlsplit o el acceso al puerto encuentra una URL mal formada.
    """
    partes = urlsplit(str(url))
    return (partes.scheme == 'https' and partes.hostname == 'webpay3gint.transbank.cl'
            and partes.port in (None, 443) and not partes.username and not partes.password
            and not partes.fragment and partes.path.startswith('/') and not partes.path.startswith('//'))


RUTA_RETORNO_WEBPAY = '/api/pagos/webpay/retorno/'


def url_retorno_webpay_valida(valor):
    """Valida el retorno local exacto del entorno académico.

    Args:
        valor (str): URL HTTP o HTTPS con localhost o IP loopback y puerto explícito.

    Returns:
        bool: Si la ruta coincide con RUTA_RETORNO_WEBPAY y no contiene credenciales,
        controles, espacios, barras inversas, consulta, fragmento ni host ambiguo.
        Las URL mal formadas se rechazan devolviendo ``False``.
    """
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
    """Crea el contexto TLS con validación de certificado y nombre del proveedor.

    Returns:
        ssl.SSLContext: Contexto de autenticación del servidor con CA del sistema
        y TLS 1.2 como versión mínima; no desactiva validaciones para el sandbox.
    """
    contexto = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    contexto.check_hostname = True
    contexto.verify_mode = ssl.CERT_REQUIRED
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    return contexto


def peticion_webpay(metodo, token=None, datos=None):
    """Envía JSON al endpoint fijo de integración y exige una respuesta de objeto.

    Args:
        metodo (str): Método HTTP que urllib enviará al proveedor.
        token (str | None): Identificador opcional de 1 a 200 caracteres seguros
            para incorporarlo a la ruta; ``None`` usa la colección de transacciones.
        datos (dict | None): Cuerpo serializable a JSON, o ``None`` para omitirlo.

    Returns:
        dict: JSON del proveedor, leído con un límite de 65536 bytes.

    Raises:
        ErrorWebpay: Si el token es inválido, falla transporte/HTTP/decodificación
            dentro de la petición, o la respuesta no es un objeto JSON.
        TypeError: Si el cuerpo recibido no puede serializarse a JSON.

    Note:
        Usa validación TLS y timeout de socket de 12 segundos. Ese timeout no
        constituye un límite total de duración ni implica reintentar la operación.
    """
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
    """Crea una transacción de integración con monto CLP entero positivo.

    Args:
        buy_order (str): Orden del servidor, con un máximo de 26 caracteres.
        session_id (str): Identificador de sesión de pago, de hasta 61 caracteres.
        monto (Decimal | str | int): Importe finito, positivo y sin fracción de peso.
        retorno (str): URL local admitida por ``url_retorno_webpay_valida``.

    Returns:
        dict: Token y URL del formulario de pago del proveedor de integración.

    Raises:
        ErrorWebpay: Si la entrada, el destino/token de respuesta o la petición falla.
        ValueError: Si la URL devuelta no puede analizarse para validar su puerto o host.
    """
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
    """Solicita al proveedor la confirmación de una transacción de integración.

    Args:
        token (str): Token de la transacción previamente registrada.

    Returns:
        dict: Respuesta del proveedor; el llamador aún debe validar su autorización.

    Raises:
        ErrorWebpay: Si el token o la respuesta no son válidos o falla la comunicación.
    """
    return peticion_webpay('PUT',token)


def autorizacion_valida(resultado, *, monto, buy_order, session_id):
    """Contrasta la autorización del proveedor con la identidad económica esperada.

    Args:
        resultado (dict): Respuesta obtenida del proveedor, no del navegador.
        monto (Decimal): Importe esperado persistido en el pago.
        buy_order (str): Orden que debe coincidir exactamente con la respuesta.
        session_id (str): Sesión de pago que debe coincidir exactamente.

    Returns:
        bool: Si status es AUTHORIZED, response_code es el entero cero e importe,
        orden y sesión coinciden. Entradas no convertibles o importes no finitos
        se rechazan; el booleano False no equivale por sí solo a rechazo bancario.
    """
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
