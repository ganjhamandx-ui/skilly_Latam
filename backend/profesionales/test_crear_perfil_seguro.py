"""Despacho real de la creacion de perfil, con ORM simulado y sin PostgreSQL."""
from contextlib import nullcontext
from unittest.mock import patch

from django.conf import settings
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.middleware.csrf import get_token
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from acceso.models import Usuario
from profesionales.models import Profesional
from profesionales.views_crear_perfil import CrearMiPerfilProfesionalView


@override_settings(ALLOWED_HOSTS=["testserver"], CSRF_TRUSTED_ORIGINS=[])
class CrearPerfilSeguroTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.usuario = Usuario(id_usuario=901, estado="ACTIVO", rol="PROFESIONAL")
        self.datos = {"nombres": "Persona", "apellidos": "De Prueba"}

    def solicitud(self, *, sesion=True, csrf="valido", datos=None):
        request = self.factory.post(
            "/api/profesionales/mi-perfil/crear/",
            self.datos if datos is None else datos, format="json",
        )
        request.session = SessionStore()
        if sesion:
            request.session["id_usuario"] = self.usuario.pk
        if csrf != "ausente":
            emisor = self.factory.get("/api/acceso/csrf/")
            token = get_token(emisor)
            request.COOKIES[settings.CSRF_COOKIE_NAME] = emisor.META["CSRF_COOKIE"]
            request.META["HTTP_X_CSRFTOKEN"] = token if csrf == "valido" else "x" * 64
        return request

    def ejecutar(self, request, *, existente=False):
        with (
            patch("acceso.authentication.Usuario.objects") as usuarios,
            patch("profesionales.views_crear_perfil.Profesional.objects") as perfiles,
            patch("profesionales.serializers.ProfesionalCompetencia.objects") as competencias,
            patch("profesionales.views_crear_perfil.transaction.atomic", return_value=nullcontext()),
        ):
            usuarios.filter.return_value.first.return_value = self.usuario
            usuarios.select_for_update.return_value.get.return_value = self.usuario
            perfiles.filter.return_value.exists.return_value = existente
            perfiles.create.return_value = Profesional(
                id_profesional=902, id_usuario=self.usuario,
                nombres=self.datos["nombres"], apellidos=self.datos["apellidos"],
                estado_validacion="PENDIENTE",
            )
            competencias.filter.return_value.select_related.return_value.order_by.return_value = []
            response = CrearMiPerfilProfesionalView.as_view()(request)
            creados = perfiles.create.call_count
            if creados:
                self.assertEqual(perfiles.create.call_args.kwargs["id_usuario"], self.usuario)
                self.assertEqual(perfiles.create.call_args.kwargs["estado_validacion"], "PENDIENTE")
            return response, creados

    def test_sesion_profesional_y_csrf_crean_su_perfil(self):
        response, creados = self.ejecutar(self.solicitud())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(creados, 1)
        self.assertEqual(response.data["perfil"]["id_profesional"], 902)

    def test_sin_sesion_no_crea_perfil(self):
        response, creados = self.ejecutar(self.solicitud(sesion=False))
        self.assertEqual((response.status_code, creados), (403, 0))

    def test_sesion_de_otro_rol_no_crea_perfil(self):
        self.usuario.rol = "ADMIN_SKILLY"
        response, creados = self.ejecutar(self.solicitud())
        self.assertEqual((response.status_code, creados), (403, 0))

    def test_post_sin_csrf_o_incorrecto_no_crea_perfil(self):
        for csrf in ("ausente", "incorrecto"):
            with self.subTest(csrf=csrf):
                response, creados = self.ejecutar(self.solicitud(csrf=csrf))
                self.assertEqual((response.status_code, creados), (403, 0))

    def test_reintento_con_perfil_existente_no_lo_duplica(self):
        response, creados = self.ejecutar(self.solicitud(), existente=True)
        self.assertEqual((response.status_code, creados), (409, 0))

    def test_datos_invalidos_no_crean_perfil(self):
        for datos in ({"nombres": "", "apellidos": "Prueba"}, [], {"nombres": "Persona"}):
            with self.subTest(tipo=type(datos).__name__):
                response, creados = self.ejecutar(self.solicitud(datos=datos))
                self.assertEqual((response.status_code, creados), (400, 0))
