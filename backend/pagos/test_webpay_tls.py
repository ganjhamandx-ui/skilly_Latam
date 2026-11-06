"""Politica TLS real y transporte simulado; nunca se contacta al proveedor."""
import io
import ssl
import unittest
from unittest.mock import patch

from .webpay_cliente_e3 import contexto_tls_webpay, peticion_webpay, ErrorWebpay


class WebpayTlsTests(unittest.TestCase):
    def test_verifica_certificado_y_hostname_con_tls_moderno(self):
        contexto = contexto_tls_webpay()
        self.assertTrue(contexto.check_hostname)
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreaterEqual(contexto.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(contexto.maximum_version, ssl.TLSVersion.MAXIMUM_SUPPORTED)

    @patch('pagos.webpay_cliente_e3.urlopen')
    def test_transporte_recibe_contexto_verificado_y_timeout(self, abrir):
        abrir.return_value.__enter__.return_value = io.BytesIO(b'{"status":"test"}')
        self.assertEqual(peticion_webpay('GET', token='token-sintetico'), {'status': 'test'})
        contexto = abrir.call_args.kwargs['context']
        self.assertTrue(contexto.check_hostname)
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreaterEqual(contexto.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(abrir.call_args.kwargs['timeout'], 12)

    @patch('pagos.webpay_cliente_e3.urlopen', side_effect=ssl.SSLCertVerificationError('certificado de prueba no confiable'))
    def test_fallo_de_certificado_no_se_reintenta_sin_verificacion(self, abrir):
        with self.assertRaises(ErrorWebpay):
            peticion_webpay('GET', token='token-sintetico')
        abrir.assert_called_once()
