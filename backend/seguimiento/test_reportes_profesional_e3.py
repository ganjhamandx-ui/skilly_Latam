"""Pruebas focalizadas y sin acceso a BD: reglas de avisos profesionales."""
from unittest import TestCase

from seguimiento.politicas_reportes_profesional import (
    ESTADO_AVISO, MOTIVOS_PROFESIONAL, preparar_aviso,
)


class ReportesProfesionalE3Tests(TestCase):
    """Cubre motivos permitidos y carácter informativo de los avisos."""

    def test_catalogo_y_estado_compatibles_con_base_existente(self):
        """Verifica el escenario: catálogo y estado compatibles con base existente."""
        self.assertEqual(len(MOTIVOS_PROFESIONAL), 6)
        self.assertLessEqual(len(ESTADO_AVISO), 30)

    def test_aviso_valido_conserva_motivo_y_descripcion(self):
        """Verifica el escenario: aviso válido conserva motivo y descripción."""
        texto = preparar_aviso('INASISTENCIA_ORGANIZACION',
                               '  La reunión comenzó y nadie se presentó.  ')
        self.assertIn('La organización no asistió', texto)
        self.assertIn('Descripción: La reunión comenzó', texto)

    def test_motivo_invalido_se_rechaza(self):
        """Verifica el escenario: motivo inválido se rechaza."""
        with self.assertRaises(ValueError):
            preparar_aviso('CANCELAR_Y_REEMBOLSAR', 'Solicito cambiar la reunión de fecha.')

    def test_descripcion_insuficiente_se_rechaza(self):
        """Verifica el escenario: descripción insuficiente se rechaza."""
        with self.assertRaises(ValueError):
            preparar_aviso('OTRO', 'Poca información')

    def test_texto_excesivo_se_rechaza(self):
        """Verifica el escenario: texto excesivo se rechaza."""
        with self.assertRaises(ValueError):
            preparar_aviso('OTRO', 'x' * 2001)

    def test_aviso_no_equivale_a_cancelacion_ni_reprogramacion(self):
        """Verifica el escenario: aviso no equivale a cancelación ni reprogramación."""
        texto = preparar_aviso('CANCELACION_PROFESIONAL',
                               'Solicito cancelar por fuerza mayor acreditable.')
        self.assertIn('no cancela ni reagenda automáticamente', texto)
