"""La referencia empresarial no publica los antecedentes internos del profesional."""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from coordinacion.models import PrestacionServicio
from seguimiento.models import AvanceServicio
from seguimiento.views import (
    SeguimientoPrestacionAdministracionView, SeguimientoPrestacionEmpresaView,
    SeguimientoPrestacionProfesionalView,
)
from solicitudes.referencias import crear_referencia_seguimiento


class AvancesEnMemoria:
    """Simula una colección de avances para verificar filtros de privacidad."""

    def __init__(self, filas):
        """Conserva los avances simulados para verificar su filtrado."""
        self.filas = filas

    def exclude(self, **condiciones):
        """Excluye de la colección los registros que cumplen las condiciones."""
        def excluida(fila):
            """Decide si una fila coincide con las condiciones de exclusión."""
            for campo, valor in condiciones.items():
                if campo.endswith("__in"):
                    if getattr(fila, campo[:-4]) not in valor:
                        return False
                elif getattr(fila, campo) != valor:
                    return False
            return True
        return AvancesEnMemoria([fila for fila in self.filas if not excluida(fila)])

    def order_by(self, *campos):
        """Describe el colaborador de prueba order_by."""
        return self

    def __iter__(self):
        """Permite recorrer los registros simulados durante la prueba."""
        return iter(self.filas)


class PrivacidadSeguimientoTests(SimpleTestCase):
    """Comprueba que cada actor reciba únicamente avances permitidos."""

    def setUp(self):
        """Prepara dependencias y datos aislados antes de cada escenario."""
        self.factory = APIRequestFactory()
        self.prestacion = PrestacionServicio(
            id_prestacion=901, id_solicitud_id=902, id_profesional_id=903,
            estado="CONTRATADA", condiciones_comunicadas="Condiciones de prueba",
        )
        self.avances = [AvanceServicio(
            id_avance=numero, id_prestacion=self.prestacion, estado=estado,
            detalle=detalle, fecha_registro=timezone.now(),
        ) for numero, estado, detalle in (
            (1, "EN_PROGRESO", "Reunion preparada"),
            (2, "INCIDENCIA_REPORTADA", "Aviso interno pendiente de revision"),
            (3, "INCIDENCIA_PROFESIONAL", "SOLICITUD_CANCELACION | Motivo privado de prueba"),
        )]

    def consultar(self, vista, *, rol=None):
        """Ejecuta la consulta de seguimiento con el rol simulado."""
        request = self.factory.get("/seguimiento-de-prueba/")
        request.session = SessionStore()
        usuario = SimpleNamespace(pk=904, estado="ACTIVO", rol=rol)
        kwargs = {"id_prestacion": self.prestacion.pk}
        if rol:
            request.session["id_usuario"] = usuario.pk
        else:
            kwargs = {"referencia": crear_referencia_seguimiento(
                SimpleNamespace(id_solicitud=902, id_contacto_id=905))}
        with (
            patch("acceso.authentication.Usuario.objects") as usuarios,
            patch("seguimiento.views.Profesional.objects") as profesionales,
            patch("seguimiento.views.PrestacionServicio.objects") as prestaciones,
            patch("seguimiento.views.AvanceServicio.objects") as avances,
            patch("seguimiento.views.Entrega.objects") as entregas,
            patch("seguimiento.views.ObservacionEntrega.objects") as observaciones,
            patch.object(SeguimientoPrestacionAdministracionView, "evaluar_cierre", return_value={}),
        ):
            usuarios.filter.return_value.first.return_value = usuario
            profesionales.filter.return_value.first.return_value = SimpleNamespace(pk=903)
            consulta = prestaciones.select_related.return_value.filter.return_value
            consulta.first.return_value = self.prestacion
            consulta.order_by.return_value.first.return_value = self.prestacion
            avances.filter.return_value = AvancesEnMemoria(self.avances)
            entregas.filter.return_value.order_by.return_value = []
            observaciones.filter.return_value.order_by.return_value = []
            return vista.as_view()(request, **kwargs)

    def test_empresa_recibe_avances_publicos_sin_antecedentes_internos(self):
        """Verifica el escenario: empresa recibe avances públicos sin antecedentes internos."""
        response = self.consultar(SeguimientoPrestacionEmpresaView)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([fila["id_avance"] for fila in response.data["avances"]], [1])
        self.assertEqual(response.data["avances"][0]["detalle"], "Reunion preparada")

    def test_profesional_y_administracion_conservan_antecedentes(self):
        """Verifica el escenario: profesional y administración conservan antecedentes."""
        for vista, rol in (
            (SeguimientoPrestacionProfesionalView, "PROFESIONAL"),
            (SeguimientoPrestacionAdministracionView, "ADMIN_SKILLY"),
        ):
            with self.subTest(rol=rol):
                response = self.consultar(vista, rol=rol)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([fila["id_avance"] for fila in response.data["avances"]], [1, 2, 3])
                if rol == "ADMIN_SKILLY":
                    self.assertEqual(response.data["entregas"], [])
                    self.assertEqual(response.data["observaciones"], [])
