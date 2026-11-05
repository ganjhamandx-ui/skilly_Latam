"""Pruebas focalizadas E3: solo reglas nuevas de reserva/cancelacion.

No crean usuarios, no escriben en PostgreSQL y no repiten los E2E aprobados.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .reserva_entrevista import (
    CancelarEntrevistaProfesionalSerializer,
    ReservaEntrevistaProfesionalView,
)


class MotivoCancelacionTest(SimpleTestCase):
    def test_motivo_corto_rechazado(self):
        self.assertFalse(
            CancelarEntrevistaProfesionalSerializer(data={"motivo": "breve"}).is_valid()
        )

    def test_motivo_valido(self):
        self.assertTrue(
            CancelarEntrevistaProfesionalSerializer(
                data={"motivo": "Debo atender una emergencia familiar."}
            ).is_valid()
        )

    def test_motivo_mayor_a_500_rechazado(self):
        self.assertFalse(
            CancelarEntrevistaProfesionalSerializer(data={"motivo": "a" * 501}).is_valid()
        )


class NuevaReservaTrasCancelacionTest(SimpleTestCase):
    def setUp(self):
        self.vista = ReservaEntrevistaProfesionalView()
        self.profesional = SimpleNamespace(pk=1)
        self.solicitud = SimpleNamespace(estado="APROBADA", pk=2)

    @patch("profesionales.reserva_entrevista.revision_completa", return_value=True)
    @patch("profesionales.reserva_entrevista.EntrevistaValidacion")
    def test_entrevista_cancelada_no_bloquea_nueva_reserva(self, modelo, _revision):
        modelo.objects.filter.return_value.exclude.return_value.exists.return_value = False
        self.assertIsNone(self.vista.validar_solicitud(self.profesional, self.solicitud))
        modelo.objects.filter.return_value.exclude.assert_called_once_with(estado="CANCELADA")

    @patch("profesionales.reserva_entrevista.revision_completa", return_value=True)
    @patch("profesionales.reserva_entrevista.EntrevistaValidacion")
    def test_entrevista_vigente_bloquea_duplicado(self, modelo, _revision):
        modelo.objects.filter.return_value.exclude.return_value.exists.return_value = True
        respuesta = self.vista.validar_solicitud(self.profesional, self.solicitud)
        self.assertEqual(respuesta.status_code, 409)
