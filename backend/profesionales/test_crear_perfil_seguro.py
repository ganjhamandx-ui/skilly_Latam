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
    """Comprueba sesión, CSRF y unicidad del perfil usando persistencia simulada."""
    def setUp(self):
        """Prepara solicitudes con comprobación CSRF y datos de un profesional activo."""
        self.factory = APIRequestFactory(enforce_csrf_checks=True)
        self.usuario = Usuario(id_usuario=901, estado="ACTIVO", rol="PROFESIONAL")
        self.datos = {"nombres": "Persona", "apellidos": "De Prueba"}

    def solicitud(self, *, sesion=True, csrf="valido", datos=None):
        """Construye una petición con sesión firmada y variantes de protección CSRF.

        Args:
            sesion: Indica si se incorpora el identificador del usuario a la sesión.
            csrf: Usa un token válido, ausente o incorrecto según el escenario.
            datos: Cuerpo alternativo; None utiliza los datos válidos iniciales.

        Returns:
            HttpRequest: Petición preparada para despachar la vista real.
        """
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
        """Despacha la vista con ORM y transacción simulados y comprueba la propiedad del perfil.

        Args:
            request: Petición preparada con sesión y CSRF según el escenario.
            existente: Indica si la consulta simulada encuentra un perfil anterior.

        Returns:
            tuple: Respuesta de la vista y número de llamadas a la creación del perfil.
        """
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
        """Comprueba una única creación y el identificador devuelto para la sesión profesional."""
        response, creados = self.ejecutar(self.solicitud())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(creados, 1)
        self.assertEqual(response.data["perfil"]["id_profesional"], 902)

    def test_sin_sesion_no_crea_perfil(self):
        """Comprueba el rechazo de una petición sin identidad en sesión."""
        response, creados = self.ejecutar(self.solicitud(sesion=False))
        self.assertEqual((response.status_code, creados), (403, 0))

    def test_sesion_de_otro_rol_no_crea_perfil(self):
        """Comprueba que una sesión administrativa no cree un perfil profesional propio."""
        self.usuario.rol = "ADMIN_SKILLY"
        response, creados = self.ejecutar(self.solicitud())
        self.assertEqual((response.status_code, creados), (403, 0))

    def test_post_sin_csrf_o_incorrecto_no_crea_perfil(self):
        """Comprueba que CSRF ausente o inválido impida cualquier creación."""
        for csrf in ("ausente", "incorrecto"):
            with self.subTest(csrf=csrf):
                response, creados = self.ejecutar(self.solicitud(csrf=csrf))
                self.assertEqual((response.status_code, creados), (403, 0))

    def test_reintento_con_perfil_existente_no_lo_duplica(self):
        """Comprueba la respuesta de conflicto sin duplicar el perfil existente."""
        response, creados = self.ejecutar(self.solicitud(), existente=True)
        self.assertEqual((response.status_code, creados), (409, 0))

    def test_datos_invalidos_no_crean_perfil(self):
        """Comprueba el rechazo de cuerpos vacíos, incompletos o con estructura inválida."""
        for datos in ({"nombres": "", "apellidos": "Prueba"}, [], {"nombres": "Persona"}):
            with self.subTest(tipo=type(datos).__name__):
                response, creados = self.ejecutar(self.solicitud(datos=datos))
                self.assertEqual((response.status_code, creados), (400, 0))
