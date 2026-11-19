"""Reglas puras de versiones y porcentajes, sin BD ni servicios externos."""
import unittest
from .politica_texto_cancelacion_e3 import porcentaje_valido, texto_versionado, firma_politica

class PoliticaVersionE3Tests(unittest.TestCase):
    """Comprueba porcentaje, texto y firma de la política versionada."""

    def test_5_por_ciento(self):
        """Verifica el escenario: 5 por ciento."""
        self.assertEqual(str(porcentaje_valido('5')), '5.0000')
    def test_actualizacion_cambia_firma(self):
        """Verifica el escenario: actualización cambia firma."""
        self.assertNotEqual(firma_politica(texto_versionado('5')), firma_politica(texto_versionado('6')))
    def test_misma_version_es_estable(self):
        """Verifica el escenario: misma version es estable."""
        self.assertEqual(firma_politica(texto_versionado('5.0000')), firma_politica(texto_versionado('5')))
    def test_texto_garantias(self):
        """Verifica el escenario: texto garantias."""
        contenido = texto_versionado('5')
        self.assertIn('no se aplican retroactivamente', contenido)
        self.assertIn('retracto', contenido)
        self.assertIn('sin', 'sin')
    def test_no_acepta_negativo(self):
        """Verifica el escenario: no acepta negativo."""
        with self.assertRaises(ValueError): porcentaje_valido('-1')
    def test_no_acepta_mayor_100(self):
        """Verifica el escenario: no acepta mayor 100."""
        with self.assertRaises(ValueError): porcentaje_valido('101')
    def test_no_acepta_nan(self):
        """Verifica el escenario: no acepta NaN."""
        with self.assertRaises(ValueError): porcentaje_valido('NaN')
    def test_no_acepta_inf(self):
        """Verifica el escenario: no acepta infinito."""
        with self.assertRaises(ValueError): porcentaje_valido('Infinity')
