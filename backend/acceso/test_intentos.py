"""Bloqueo temporal y recuperacion, sin BD, correo ni servicios de cache reales."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from rest_framework.test import APIRequestFactory

from .checks import cache_acceso_compartida, configuracion_limites_acceso
from .intentos import (
    ControlIntentosNoDisponible, LimiteIntentosAcceso, _direccion_origen,
)
from .views import InicioSesionView, RestablecerContrasenaView, SolicitarRecuperacionView
from .serializers import InicioSesionSerializer


class CacheConReloj:
    """Doble acotado de add/incr/touch con caducidad comprobable."""
    def __init__(self, reloj):
        self.reloj = reloj
        self.valores = {}

    def _leer(self, clave):
        if clave in self.valores and self.valores[clave][1] <= self.reloj[0]:
            self.valores.pop(clave)
        return self.valores.get(clave)

    def add(self, clave, valor, timeout):
        if self._leer(clave) is not None:
            return False
        self.valores[clave] = (valor, self.reloj[0] + timeout)
        return True

    def incr(self, clave):
        registro = self._leer(clave)
        if registro is None:
            raise ValueError("expired")
        self.valores[clave] = (registro[0] + 1, registro[1])
        return registro[0] + 1

    def touch(self, clave, timeout):
        registro = self._leer(clave)
        if registro is not None:
            self.valores[clave] = (registro[0], self.reloj[0] + timeout)
            return True
        return False


def limites(ip=("50/60", "100/600"), identidad=("2/60", "20/600")):
    """Genera límites ficticios comunes para cada alcance protegido."""

    return {alcance: {"ip": list(ip), "identidad_ip": list(identidad)}
            for alcance in ("iniciar_sesion", "recuperar", "restablecer")}


@override_settings(ACCESO_LIMITES=limites(), ACCESO_PROXIES_CONFIABLES=[])
class LimitesTemporalesTests(SimpleTestCase):
    """Comprueba ventanas, expiración y bloqueo de intentos con reloj controlado."""

    def setUp(self):
        self.reloj = [100.0]
        self.cache = CacheConReloj(self.reloj)
        self.factory = APIRequestFactory()
        parche = patch("acceso.intentos.time.time", side_effect=lambda: self.reloj[0])
        parche.start(); self.addCleanup(parche.stop)
        parche = patch("acceso.intentos.caches", {"acceso_intentos": self.cache})
        parche.start(); self.addCleanup(parche.stop)

    def solicitud(self, correo="persona@example.invalid", ip="192.0.2.10", token="token-sintetico"):
        raw = self.factory.post("/", {"correo": correo, "token": token}, format="json", REMOTE_ADDR=ip)
        return Request(raw, parsers=[JSONParser()])

    def permitir(self, request=None, alcance="iniciar_sesion"):
        throttle = LimiteIntentosAcceso()
        return throttle, throttle.allow_request(request or self.solicitud(), SimpleNamespace(alcance_intentos=alcance))

    def test_bloqueo_corto_expira_y_los_rechazos_no_lo_prolongan(self):
        self.assertTrue(self.permitir()[1]); self.assertTrue(self.permitir()[1])
        throttle, permitido = self.permitir()
        self.assertFalse(permitido); self.assertEqual(throttle.wait(), 20)
        self.reloj[0] = 119
        self.assertFalse(self.permitir()[1])
        self.reloj[0] = 120
        self.assertTrue(self.permitir()[1])

    @override_settings(ACCESO_LIMITES=limites(identidad=("2/60", "3/600")))
    def test_ventana_larga_tambien_se_recupera(self):
        self.assertTrue(self.permitir()[1]); self.assertTrue(self.permitir()[1])
        self.reloj[0] = 121
        self.assertTrue(self.permitir()[1])
        throttle, permitido = self.permitir()
        self.assertFalse(permitido); self.assertEqual(throttle.wait(), 479)
        self.reloj[0] = 600
        self.assertTrue(self.permitir()[1])

    @override_settings(ACCESO_LIMITES=limites(ip=("2/60", "20/600"), identidad=("50/60",)))
    def test_variar_correos_o_tokens_no_elude_el_limite_de_ip(self):
        self.assertTrue(self.permitir(self.solicitud(correo="uno@example.invalid"))[1])
        self.assertTrue(self.permitir(self.solicitud(correo="dos@example.invalid"))[1])
        self.assertFalse(self.permitir(self.solicitud(correo="tres@example.invalid"))[1])
        for n in range(2):
            self.assertTrue(self.permitir(self.solicitud(token=f"token-{n}"), "restablecer")[1])
        self.assertFalse(self.permitir(self.solicitud(token="token-distinto"), "restablecer")[1])

    def test_no_existe_veto_global_de_la_cuenta_en_otra_ip(self):
        self.permitir(); self.permitir(); self.assertFalse(self.permitir()[1])
        self.assertTrue(self.permitir(self.solicitud(ip="192.0.2.11"))[1])

    def test_normaliza_correo_y_no_guarda_identificadores_en_cache(self):
        self.permitir(self.solicitud(correo="Persona@EXAMPLE.INVALID"))
        self.permitir(self.solicitud(correo=" persona@example.invalid "))
        self.assertFalse(self.permitir()[1])
        self.permitir(alcance="restablecer")
        claves = " ".join(self.cache.valores)
        for secreto in ("192.0.2.10", "persona", "example.invalid", "token-sintetico"):
            self.assertNotIn(secreto, claves)

    def test_error_de_backend_no_revela_uri_ni_credenciales(self):
        with patch.object(self.cache, "add", side_effect=RuntimeError("backend details")):
            with self.assertRaises(ControlIntentosNoDisponible) as exc:
                self.permitir()
        self.assertEqual(exc.exception.status_code, 503)
        self.assertEqual(exc.exception.wait, 30)
        self.assertNotIn("backend details", str(exc.exception.detail))

    def test_cache_no_inicializable_devuelve_503_temporal_sin_detalles(self):
        with patch("acceso.intentos.caches") as caches_rotas, patch(
            "acceso.views.InicioSesionSerializer",
        ) as serializador:
            caches_rotas.__getitem__.side_effect = RuntimeError("backend initialization details")
            respuesta = InicioSesionView.as_view()(self.factory.post(
                "/", {"correo": "persona@example.invalid"}, format="json", REMOTE_ADDR="192.0.2.10",
            ))
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta["Retry-After"], "30")
        self.assertNotIn("backend initialization details", str(respuesta.data))
        serializador.assert_not_called()

    def test_limita_antes_de_serializar_o_consultar_la_cuenta(self):
        for vista, destino in (
            (InicioSesionView, "InicioSesionSerializer"),
            (SolicitarRecuperacionView, "SolicitarRecuperacionSerializer"),
            (RestablecerContrasenaView, "RestablecerContrasenaSerializer"),
        ):
            with self.subTest(vista=vista.__name__), patch("acceso.views." + destino) as serializador:
                serializador.return_value.is_valid.return_value = False
                serializador.return_value.errors = {"detail": "Entrada invalida."}
                for _ in range(2):
                    respuesta = vista.as_view()(self.factory.post("/", {"correo": "persona@example.invalid", "token": "token-sintetico"}, format="json", REMOTE_ADDR="192.0.2.10"))
                    self.assertEqual(respuesta.status_code, 400)
                respuesta = vista.as_view()(self.factory.post("/", {"correo": "persona@example.invalid", "token": "token-sintetico"}, format="json", REMOTE_ADDR="192.0.2.10"))
                self.assertEqual(respuesta.status_code, 429)
                self.assertEqual(respuesta["Retry-After"], "20")
                self.assertEqual(serializador.call_count, 2)

    def test_recuperacion_responde_igual_para_cuenta_existente_o_ausente(self):
        respuestas = []
        for ip, usuario in (("192.0.2.10", SimpleNamespace()), ("192.0.2.11", None)):
            with patch("acceso.views.Usuario.objects") as usuarios, patch(
                "acceso.views.transaction.atomic", side_effect=lambda: nullcontext(),
            ), patch("acceso.views.crear_recuperacion_acceso", return_value=("token-ficticio", object())), patch(
                "acceso.views.enviar_correo_recuperacion", return_value=1,
            ):
                usuarios.filter.return_value.first.return_value = usuario
                resultados = []
                for _ in range(3):
                    respuesta = SolicitarRecuperacionView.as_view()(self.factory.post("/", {"correo": "persona@example.invalid"}, format="json", REMOTE_ADDR=ip))
                    resultados.append((respuesta.status_code, respuesta.data, respuesta.get("Retry-After")))
                respuestas.append(resultados)
                self.assertEqual(usuarios.filter.call_count, 2)
        self.assertEqual(respuestas[0], respuestas[1])
        self.assertEqual([r[0] for r in respuestas[0]], [200, 200, 429])


class ProxiesYConfiguracionTests(SimpleTestCase):
    """Valida IP efectiva y confianza explícita en proxies configurados."""

    def setUp(self):
        self.factory = APIRequestFactory()

    @override_settings(ACCESO_PROXIES_CONFIABLES=[])
    def test_xff_no_confiable_no_permite_cambiar_identidad(self):
        request = self.factory.get("/", REMOTE_ADDR="192.0.2.10", HTTP_X_FORWARDED_FOR="198.51.100.20")
        self.assertEqual(_direccion_origen(request), "192.0.2.10")

    @override_settings(ACCESO_PROXIES_CONFIABLES=["127.0.0.0/8", "10.0.0.0/8"])
    def test_proxy_confiable_recorta_prefijo_inyectado_desde_la_derecha(self):
        request = self.factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.99, 192.0.2.10, 10.0.0.2")
        self.assertEqual(_direccion_origen(request), "192.0.2.10")

    @override_settings(ACCESO_PROXIES_CONFIABLES=["127.0.0.0/8"])
    def test_cadena_invalida_recae_en_el_peer(self):
        request = self.factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="invalido")
        self.assertEqual(_direccion_origen(request), "127.0.0.1")

    @override_settings(CACHES={"acceso_intentos": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_configuracion_local_avisa_solo_al_revisar_despliegue(self):
        self.assertEqual(configuracion_limites_acceso(None), [])
        self.assertEqual([m.id for m in cache_acceso_compartida(None)], ["acceso.W001"])

    @override_settings(ACCESO_LIMITES=limites(identidad=("0/60",)))
    def test_configuracion_invalida_no_se_acepta(self):
        self.assertIn("acceso.E001", [m.id for m in configuracion_limites_acceso(None)])


class CredencialesSinEnumeracionTests(SimpleTestCase):
    """Comprueba respuestas equivalentes para cuentas ausentes, inactivas o inválidas."""

    def validar(self):
        entrada = InicioSesionSerializer(data={
            "correo": "persona@example.invalid", "contrasena": "entrada-ficticia",
        })
        self.assertFalse(entrada.is_valid())
        return entrada.errors

    def test_usuario_ausente_realiza_hash_dummy_y_mantiene_error_generico(self):
        with patch("acceso.serializers.Usuario.objects") as usuarios, patch(
            "acceso.serializers.make_password",
        ) as hash_dummy, patch("acceso.serializers.check_password") as comprobar:
            usuarios.filter.return_value.first.return_value = None
            ausente = self.validar()
            hash_dummy.assert_called_once_with("entrada-ficticia")
            comprobar.assert_not_called()

        for estado, contrasena_correcta in (("ACTIVO", False), ("INACTIVO", True)):
            with self.subTest(estado=estado), patch(
                "acceso.serializers.Usuario.objects",
            ) as usuarios, patch("acceso.serializers.check_password", return_value=contrasena_correcta):
                usuarios.filter.return_value.first.return_value = SimpleNamespace(
                    password_hash="hash-ficticio", estado=estado,
                )
                self.assertEqual(self.validar(), ausente)

    def test_login_legitimo_no_agrega_hash_dummy_ni_cambia_usuario(self):
        usuario = SimpleNamespace(password_hash="hash-ficticio", estado="ACTIVO")
        with patch("acceso.serializers.Usuario.objects") as usuarios, patch(
            "acceso.serializers.make_password",
        ) as hash_dummy, patch("acceso.serializers.check_password", return_value=True):
            usuarios.filter.return_value.first.return_value = usuario
            entrada = InicioSesionSerializer(data={
                "correo": "persona@example.invalid", "contrasena": "entrada-ficticia",
            })
            self.assertTrue(entrada.is_valid())
            self.assertIs(entrada.validated_data["usuario"], usuario)
            hash_dummy.assert_not_called()
