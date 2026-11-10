"""Retornos y destinos configurados; proveedor simulado, sin pagos ni BD."""
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, override_settings

from pagos.webpay_cliente_e3 import ErrorWebpay, iniciar, url_retorno_webpay_valida
from pagos.webpay_empresa_e3 import ambiente_disponible, redireccion, retorno_webpay


RUTA = "/api/pagos/webpay/retorno/"


class RetornoWebpayConfiguradoTests(SimpleTestCase):
    @override_settings(FRONTEND_ORIGIN="http://127.0.0.2:53171", DEBUG=True)
    @patch("pagos.webpay_cliente_e3.peticion_webpay")
    def test_inicio_alternativo_conserva_importe_identificadores_y_retorno_exacto(self, proveedor):
        proveedor.return_value = {
            "token": "token-sintetico", "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
        }
        iniciar("orden-sintetica", "sesion-sintetica", 15000, retorno_webpay())
        proveedor.assert_called_once_with("POST", datos={
            "buy_order": "orden-sintetica", "session_id": "sesion-sintetica", "amount": 15000,
            "return_url": "http://127.0.0.2:53171" + RUTA,
        })

    def test_construye_retorno_en_cada_uso_sin_capturar_settings_al_importar(self):
        with override_settings(FRONTEND_ORIGIN="http://localhost:5173"):
            self.assertEqual(retorno_webpay(), "http://localhost:5173" + RUTA)
        with override_settings(FRONTEND_ORIGIN="https://[::1]:53175/"):
            self.assertEqual(retorno_webpay(), "https://[::1]:53175" + RUTA)

    @override_settings(FRONTEND_ORIGIN="http://127.0.0.2:53171/")
    @patch("pagos.webpay_empresa_e3.crear_referencia_seguimiento")
    def test_redirect_seguimiento_solo_usa_origen_configurado_y_codifica_query(self, referencia):
        referencia.return_value = "referencia-sintetica&next=https://otro.invalid/"
        pago = SimpleNamespace(id_prestacion=SimpleNamespace(id_solicitud=object()))
        respuesta = redireccion(pago, "aprobado&next=//otro.invalid")
        destino = urlsplit(respuesta["Location"])
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual((destino.scheme, destino.netloc, destino.path),
                         ("http", "127.0.0.2:53171", "/seguimiento"))
        self.assertEqual(parse_qs(destino.query), {
            "referencia": [referencia.return_value], "webpay": ["aprobado&next=//otro.invalid"],
        })

    def test_origen_invalido_no_genera_redireccion(self):
        pago = SimpleNamespace(id_prestacion=SimpleNamespace(id_solicitud=object()))
        with patch("pagos.webpay_empresa_e3.crear_referencia_seguimiento", return_value="sintetica"):
            for origen in ("//otro.invalid", "http://usuario@127.0.0.2:53171", "http://127.0.0.2:53171/otra"):
                with self.subTest(origen=origen), override_settings(FRONTEND_ORIGIN=origen):
                    with self.assertRaises(ErrorWebpay):
                        redireccion(pago, "aprobado")

    def test_retorno_solo_acepta_loopback_puerto_explicito_y_ruta_exacta(self):
        for origen in ("http://localhost:5173", "http://127.0.0.2:53171", "https://127.12.3.4:53171",
                       "http://[::1]:53171"):
            with self.subTest(origen=origen):
                self.assertTrue(url_retorno_webpay_valida(origen + RUTA))

    @patch("pagos.webpay_cliente_e3.peticion_webpay")
    def test_retornos_maliciosos_o_ambiguos_se_rechazan_antes_de_contactar_proveedor(self, proveedor):
        origen = "http://localhost:5173"
        for retorno in (
            origen + RUTA + "extra", origen + RUTA + "?", origen + RUTA + "#",
            origen + RUTA + "?next=https://otro.invalid", origen + RUTA + "../otra",
            origen + "/api/pagos/webpay/%72etorno/", origen + RUTA[:-1],
            "http://localhost:5173.evil.invalid" + RUTA, "http://localhost.evil.invalid:5173" + RUTA,
            "http://127.0.0.2@otro.invalid:53171" + RUTA, "http://usuario@127.0.0.2:53171" + RUTA,
            "http://127.0.0.2:53171\\@otro.invalid" + RUTA,
            "http://127.0.0.2:0" + RUTA, "http://127.0.0.2:65536" + RUTA,
            "http://127.0.0.2" + RUTA, "http://127.1:53171" + RUTA,
            "http://2130706434:53171" + RUTA, "http://192.168.1.2:53171" + RUTA,
            "https://frontend.example.invalid:53171" + RUTA, "ftp://127.0.0.2:53171" + RUTA,
            "http://[::1%25zona]:53171" + RUTA, "http://127.0.0.2:\n53171" + RUTA,
        ):
            with self.subTest(retorno=retorno):
                with self.assertRaises(ErrorWebpay):
                    iniciar("orden-sintetica", "sesion-sintetica", 15000, retorno)
        proveedor.assert_not_called()

    @override_settings(DEBUG=False, FRONTEND_ORIGIN="http://127.0.0.2:53171")
    def test_origen_alternativo_no_habilita_webpay_en_produccion(self):
        self.assertFalse(ambiente_disponible())
