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
    """Comprueba límites del motivo de cancelación mediante el serializador."""
    def test_motivo_corto_rechazado(self):
        """Rechaza un motivo que no alcanza la longitud mínima exigida."""
        self.assertFalse(
            CancelarEntrevistaProfesionalSerializer(data={"motivo": "breve"}).is_valid()
        )

    def test_motivo_valido(self):
        """Admite una explicación dentro de los límites del serializador."""
        self.assertTrue(
            CancelarEntrevistaProfesionalSerializer(
                data={"motivo": "Debo atender una emergencia familiar."}
            ).is_valid()
        )

    def test_motivo_mayor_a_500_rechazado(self):
        """Rechaza un motivo que supera quinientos caracteres."""
        self.assertFalse(
            CancelarEntrevistaProfesionalSerializer(data={"motivo": "a" * 501}).is_valid()
        )


class NuevaReservaTrasCancelacionTest(SimpleTestCase):
    """Comprueba la exclusión de entrevistas canceladas al evaluar otra reserva."""
    def setUp(self):
        """Prepara vista, profesional y solicitud aprobada sin persistir registros."""
        self.vista = ReservaEntrevistaProfesionalView()
        self.profesional = SimpleNamespace(pk=1)
        self.solicitud = SimpleNamespace(estado="APROBADA", pk=2)

    @patch("profesionales.reserva_entrevista.revision_completa", return_value=True)
    @patch("profesionales.reserva_entrevista.EntrevistaValidacion")
    def test_entrevista_cancelada_no_bloquea_nueva_reserva(self, modelo, _revision):
        """Comprueba que la búsqueda de duplicados excluya el estado CANCELADA.

        Args:
            modelo: Modelo de entrevistas sustituido por patch.
            _revision: Simulación de una revisión documental completa.
        """
        modelo.objects.filter.return_value.exclude.return_value.exists.return_value = False
        self.assertIsNone(self.vista.validar_solicitud(self.profesional, self.solicitud))
        modelo.objects.filter.return_value.exclude.assert_called_once_with(estado="CANCELADA")

    @patch("profesionales.reserva_entrevista.revision_completa", return_value=True)
    @patch("profesionales.reserva_entrevista.EntrevistaValidacion")
    def test_entrevista_vigente_bloquea_duplicado(self, modelo, _revision):
        """Comprueba el conflicto cuando existe una entrevista no cancelada.

        Args:
            modelo: Modelo simulado que informa una entrevista vigente.
            _revision: Simulación de una revisión documental completa.
        """
        modelo.objects.filter.return_value.exclude.return_value.exists.return_value = True
        respuesta = self.vista.validar_solicitud(self.profesional, self.solicitud)
        self.assertEqual(respuesta.status_code, 409)
