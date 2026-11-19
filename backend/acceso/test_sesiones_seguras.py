"""Sesiones ligadas a contrasena: modelos simulados y sesiones sin BD."""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import SimpleTestCase
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .authentication import SesionSkillyAuthentication
from .sesiones import (
    _CLAVE_VINCULO_CONTRASENA,
    _sesion_contrasena_vigente,
    _vincular_sesion_con_contrasena,
)
from .views import InicioSesionView


class SesionesContrasenaTests(SimpleTestCase):
    """Comprueba invalidación de sesiones después de cambiar la contraseña."""

    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.usuario = self.usuario_simulado("hash-sintetico-v1")

    def usuario_simulado(self, password_hash, pk=7):
        return SimpleNamespace(
            pk=pk, id_usuario=pk, correo="prueba@example.invalid",
            rol="PROFESIONAL", estado="ACTIVO", password_hash=password_hash,
        )

    def solicitud(self, metodo="GET"):
        raw = self.factory.generic(
            metodo, "/api/acceso/sesion-actual/", data="{}", content_type="application/json",
        )
        raw.session = SessionStore()
        raw.session["id_usuario"] = self.usuario.pk
        return Request(raw, parsers=[JSONParser()])

    def autenticar(self, solicitud, usuario):
        with patch("acceso.authentication.Usuario.objects") as usuarios:
            usuarios.filter.return_value.first.return_value = usuario
            return SesionSkillyAuthentication().authenticate(solicitud)

    def iniciar_sesion_simulada(self, solicitud, usuario_validado):
        with patch("acceso.views.InicioSesionSerializer") as serializer:
            serializer.return_value.is_valid.return_value = True
            serializer.return_value.validated_data = {"usuario": usuario_validado}
            return InicioSesionView().post(solicitud)

    def test_login_nuevo_guarda_vinculo_privado_sin_cambiar_respuesta(self):
        solicitud = self.solicitud("POST")

        respuesta = self.iniciar_sesion_simulada(solicitud, self.usuario)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(solicitud.session["id_usuario"], self.usuario.pk)
        self.assertEqual(solicitud.session["rol"], self.usuario.rol)
        self.assertTrue(_sesion_contrasena_vigente(solicitud.session, self.usuario))
        marca = solicitud.session[_CLAVE_VINCULO_CONTRASENA]
        self.assertNotEqual(marca, self.usuario.password_hash)
        self.assertNotIn(self.usuario.password_hash, solicitud.session.values())
        self.assertEqual(set(respuesta.data), {"mensaje", "usuario"})
        self.assertEqual(set(respuesta.data["usuario"]), {"id_usuario", "correo", "rol"})
        self.assertNotIn(marca, str(respuesta.data))

    def test_sesion_vinculada_con_contrasena_actual_se_autentica(self):
        solicitud = self.solicitud()
        _vincular_sesion_con_contrasena(solicitud.session, self.usuario)

        self.assertEqual(self.autenticar(solicitud, self.usuario), (self.usuario, None))

    def test_hash_cambiado_revoca_la_sesion_en_la_siguiente_solicitud(self):
        solicitud = self.solicitud()
        _vincular_sesion_con_contrasena(solicitud.session, self.usuario)
        usuario_actual = self.usuario_simulado("hash-sintetico-v2")

        self.assertIsNone(self.autenticar(solicitud, usuario_actual))

        self.assertNotIn("id_usuario", solicitud.session)
        self.assertNotIn(_CLAVE_VINCULO_CONTRASENA, solicitud.session)

    def test_login_validado_antes_del_reset_y_guardado_despues_no_sobrevive(self):
        # El serializer conserva el usuario leido antes del cambio de contrasena.
        usuario_validado_antes = self.usuario
        usuario_actual = self.usuario_simulado("hash-sintetico-v2")
        solicitud = self.solicitud("POST")
        self.iniciar_sesion_simulada(solicitud, usuario_validado_antes)
        siguiente_solicitud = self.solicitud()
        siguiente_solicitud._request.session = solicitud.session

        self.assertIsNone(self.autenticar(siguiente_solicitud, usuario_actual))

        self.assertNotIn("id_usuario", solicitud.session)

    def test_login_no_valido_no_agrega_vinculo(self):
        solicitud = self.solicitud("POST")
        with patch("acceso.views.InicioSesionSerializer") as serializer:
            serializer.return_value.is_valid.return_value = False
            serializer.return_value.errors = {"non_field_errors": ["Solicitud simulada no valida."]}

            respuesta = InicioSesionView().post(solicitud)

        self.assertEqual(respuesta.status_code, 400)
        self.assertNotIn(_CLAVE_VINCULO_CONTRASENA, solicitud.session)

    def test_sesion_legacy_sin_marca_conserva_compatibilidad(self):
        solicitud = self.solicitud()

        self.assertEqual(self.autenticar(solicitud, self.usuario), (self.usuario, None))

        self.assertNotIn(_CLAVE_VINCULO_CONTRASENA, solicitud.session)

    def test_marca_presente_pero_invalida_no_se_trata_como_legacy(self):
        solicitud = self.solicitud()
        solicitud.session[_CLAVE_VINCULO_CONTRASENA] = None

        self.assertIsNone(self.autenticar(solicitud, self.usuario))

        self.assertNotIn("id_usuario", solicitud.session)

    def test_vinculo_no_se_puede_reutilizar_para_otro_usuario_con_mismo_hash(self):
        solicitud = self.solicitud()
        _vincular_sesion_con_contrasena(solicitud.session, self.usuario)
        otro_usuario = self.usuario_simulado(self.usuario.password_hash, pk=8)

        self.assertFalse(_sesion_contrasena_vigente(solicitud.session, otro_usuario))
