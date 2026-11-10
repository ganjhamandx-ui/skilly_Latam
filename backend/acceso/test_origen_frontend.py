"""Configuración y middleware reales, sin base de datos ni servicios externos."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from corsheaders.middleware import CorsMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views.decorators.csrf import csrf_protect

from config.origenes import normalizar_origen_frontend


ORIGEN_ALTERNATIVO = "http://127.0.0.2:53171"


class ConfiguracionOrigenFrontendTests(SimpleTestCase):
    def cargar_configuracion(self, origen=None):
        # Ejecutar la configuración real con entorno ficticio y sin leer .env.
        ruta = Path(__file__).resolve().parents[1] / "config" / "settings.py"
        spec = importlib.util.spec_from_file_location("config._settings_prueba_origen", ruta)
        modulo = importlib.util.module_from_spec(spec)
        entorno = {
            "DJANGO_SECRET_KEY": "clave-ficticia-para-prueba-de-configuracion",
            "POSTGRES_PASSWORD": "dato-ficticio-sin-conexion",
        }
        if origen is not None:
            entorno["FRONTEND_ORIGIN"] = origen
        with patch.dict(os.environ, entorno, clear=True), patch("dotenv.load_dotenv") as cargar:
            spec.loader.exec_module(modulo)
            cargar.assert_called_once()
        return modulo

    def test_origen_alternativo_es_el_unico_confiable_sin_alias_legacy(self):
        configuracion = self.cargar_configuracion(ORIGEN_ALTERNATIVO)
        self.assertEqual(configuracion.FRONTEND_ORIGIN, ORIGEN_ALTERNATIVO)
        self.assertEqual(configuracion.CORS_ALLOWED_ORIGINS, [ORIGEN_ALTERNATIVO])
        self.assertEqual(configuracion.CSRF_TRUSTED_ORIGINS, [ORIGEN_ALTERNATIVO])
        self.assertTrue(configuracion.CORS_ALLOW_CREDENTIALS)

    def test_default_legacy_se_conserva_solo_si_no_hay_configuracion(self):
        configuracion = self.cargar_configuracion()
        self.assertEqual(configuracion.FRONTEND_ORIGIN, "http://localhost:5173")
        self.assertEqual(configuracion.CORS_ALLOWED_ORIGINS, [configuracion.FRONTEND_ORIGIN])
        self.assertEqual(configuracion.CSRF_TRUSTED_ORIGINS, [configuracion.FRONTEND_ORIGIN])

    def test_configuracion_publica_https_y_puerto_default_siguen_admitidos(self):
        configuracion = self.cargar_configuracion("https://frontend.example.invalid:443/")
        self.assertEqual(configuracion.FRONTEND_ORIGIN, "https://frontend.example.invalid")
        self.assertEqual(configuracion.CORS_ALLOWED_ORIGINS, [configuracion.FRONTEND_ORIGIN])
        self.assertEqual(configuracion.CSRF_TRUSTED_ORIGINS, [configuracion.FRONTEND_ORIGIN])

    def test_normaliza_slash_final_y_conserva_ipv6_y_puerto_alternativo(self):
        self.assertEqual(normalizar_origen_frontend(ORIGEN_ALTERNATIVO + "/"), ORIGEN_ALTERNATIVO)
        self.assertEqual(normalizar_origen_frontend("http://[::1]:53171/"), "http://[::1]:53171")

    def test_origen_malformado_falla_sin_revelar_el_valor(self):
        for origen in (
            "http://usuario:canario-privado@127.0.0.2:53171",
            ORIGEN_ALTERNATIVO + "/seguimiento", ORIGEN_ALTERNATIVO + "?dato=canario-privado",
            ORIGEN_ALTERNATIVO + "#canario-privado", "//127.0.0.2:53171",
            "ftp://127.0.0.2:53171", "http://127.0.0.2:0", "http://127.0.0.2:65536",
            "http://127.0.0.2:53171\\@otro.invalid", "http://127.0.0.2:\n53171",
        ):
            with self.subTest(caso=origen.split(":", 1)[0]):
                with self.assertRaises(ImproperlyConfigured) as error:
                    self.cargar_configuracion(origen)
                self.assertNotIn("canario-privado", str(error.exception))
                self.assertNotIn(origen, str(error.exception))


@override_settings(
    ALLOWED_HOSTS=["127.0.0.2"],
    CSRF_TRUSTED_ORIGINS=[ORIGEN_ALTERNATIVO],
    CORS_ALLOWED_ORIGINS=[ORIGEN_ALTERNATIVO],
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOW_CREDENTIALS=True,
)
class MiddlewareOrigenFrontendTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def escritura(self, origen, token="valido"):
        emisor = self.factory.get("/api/acceso/csrf/")
        valor = get_token(emisor)
        solicitud = self.factory.post(
            "/api/acceso/iniciar-sesion/", data="{}", content_type="application/json",
            HTTP_HOST="127.0.0.2:53172", HTTP_ORIGIN=origen,
        )
        if token != "ausente":
            solicitud.COOKIES["csrftoken"] = emisor.META["CSRF_COOKIE"]
            solicitud.META["HTTP_X_CSRFTOKEN"] = valor if token == "valido" else "x" * len(valor)
        return csrf_protect(lambda request: HttpResponse("permitido"))(solicitud)

    def test_csrf_nuevo_origen_con_cookie_y_token_es_admitido(self):
        self.assertEqual(self.escritura(ORIGEN_ALTERNATIVO).status_code, 200)

    def test_csrf_rechaza_legacy_otro_puerto_y_host_enganoso_con_token_valido(self):
        for origen in ("http://localhost:5173", "http://127.0.0.2:53173",
                       "http://127.0.0.2.evil.invalid:53171"):
            with self.subTest(origen=origen):
                self.assertEqual(self.escritura(origen).status_code, 403)

    def test_csrf_no_se_desactiva_en_origen_nuevo(self):
        for token in ("ausente", "incorrecto"):
            with self.subTest(token=token):
                self.assertEqual(self.escritura(ORIGEN_ALTERNATIVO, token).status_code, 403)

    def test_cors_solo_autoriza_origen_configurado_y_conserva_credenciales(self):
        middleware = CorsMiddleware(lambda request: HttpResponse())
        for origen in (ORIGEN_ALTERNATIVO, "http://localhost:5173", "https://otro.invalid"):
            solicitud = self.factory.options(
                "/api/acceso/iniciar-sesion/", HTTP_HOST="127.0.0.2:53172",
                HTTP_ORIGIN=origen, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            )
            respuesta = middleware(solicitud)
            with self.subTest(origen=origen):
                if origen == ORIGEN_ALTERNATIVO:
                    self.assertEqual(respuesta["Access-Control-Allow-Origin"], origen)
                    self.assertEqual(respuesta["Access-Control-Allow-Credentials"], "true")
                else:
                    self.assertNotIn("Access-Control-Allow-Origin", respuesta)
