"""Pruebas focalizadas sin conexión real, sin DB y sin tarjetas."""
import unittest
from unittest.mock import patch
from pagos.webpay_cliente_e3 import ErrorWebpay, url_pago_valida, iniciar, autorizacion_valida

class WebpayIntegracionE3Test(unittest.TestCase):
    """Comprueba destinos, importes y correspondencia de autorizaciones sin contactar al proveedor."""
    def test_acepta_url_oficial(self):
        """Admite el destino HTTPS del entorno de integración de Transbank."""
        self.assertTrue(url_pago_valida('https://webpay3gint.transbank.cl/webpayserver/initTransaction'))
    def test_no_permite_host_similar_malicioso(self):
        """Rechaza dominios que añaden un sufijo al nombre permitido."""
        self.assertFalse(url_pago_valida('https://webpay3gint.transbank.cl.evil.test/x'))
    def test_no_permite_http(self):
        """Exige HTTPS en el destino de pago del proveedor."""
        self.assertFalse(url_pago_valida('http://webpay3gint.transbank.cl/x'))
    def test_no_permite_usuario_incrustado(self):
        """Rechaza credenciales incrustadas en la URL de pago."""
        self.assertFalse(url_pago_valida('https://user@webpay3gint.transbank.cl/x'))
    def test_autorizacion_valida(self):
        """Admite una autorización cuyo importe, orden y sesión coinciden con lo esperado."""
        d={'status':'AUTHORIZED','response_code':0,'buy_order':'SKWE312','session_id':'SKSE312','amount':15000}
        self.assertTrue(autorizacion_valida(d,monto=15000,buy_order='SKWE312',session_id='SKSE312'))
    def test_no_acepta_monto_cambiado(self):
        """Rechaza una autorización con importe distinto del solicitado."""
        d={'status':'AUTHORIZED','response_code':0,'buy_order':'SKWE312','session_id':'SKSE312','amount':12000}
        self.assertFalse(autorizacion_valida(d,monto=15000,buy_order='SKWE312',session_id='SKSE312'))
    def test_no_acepta_orden_distinta(self):
        """Rechaza una autorización asociada a otra orden de compra."""
        d={'status':'AUTHORIZED','response_code':0,'buy_order':'OTRA','session_id':'SKSE312','amount':15000}
        self.assertFalse(autorizacion_valida(d,monto=15000,buy_order='SKWE312',session_id='SKSE312'))
    def test_no_acepta_rechazo(self):
        """Comprueba que una respuesta fallida del proveedor no se considere autorizada."""
        d={'status':'FAILED','response_code':-1,'buy_order':'SKWE312','session_id':'SKSE312','amount':15000}
        self.assertFalse(autorizacion_valida(d,monto=15000,buy_order='SKWE312',session_id='SKSE312'))
    @patch('pagos.webpay_cliente_e3.peticion_webpay')
    def test_creacion_vigila_url(self, solicitud):
        """Rechaza una URL de pago ajena aunque el proveedor simulado entregue un token.

        Args:
            solicitud: Transporte Webpay sustituido por patch.
        """
        solicitud.return_value={'url':'https://evil.test/payment','token':'abc123token'}
        with self.assertRaises(ErrorWebpay):
            iniciar('SKWE312','SKSE312',15000,'http://localhost:5173/api/pagos/webpay/retorno/')
    @patch('pagos.webpay_cliente_e3.peticion_webpay')
    def test_creacion_correcta(self, solicitud):
        """Conserva el token válido y el importe entero enviado al proveedor simulado.

        Args:
            solicitud: Transporte Webpay sustituido por patch.
        """
        solicitud.return_value={'url':'https://webpay3gint.transbank.cl/webpayserver/initTransaction','token':'abc123token'}
        datos=iniciar('SKWE312','SKSE312',15000,'http://localhost:5173/api/pagos/webpay/retorno/')
        self.assertEqual(datos['token'],'abc123token')
        self.assertEqual(solicitud.call_args.kwargs['datos']['amount'],15000)
    def test_no_permite_monto_decimal(self):
        """Impide iniciar una transacción con fracciones de peso."""
        with self.assertRaises(ErrorWebpay):
            iniciar('SKWE312','SKSE312',15000.5,'http://localhost:5173/api/pagos/webpay/retorno/')
