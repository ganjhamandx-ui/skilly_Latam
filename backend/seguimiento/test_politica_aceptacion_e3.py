"""Reglas puras de versiones y porcentajes, sin BD ni servicios externos."""
import unittest
from .politica_texto_cancelacion_e3 import porcentaje_valido, texto_versionado, firma_politica

class PoliticaVersionE3Tests(unittest.TestCase):
    def test_5_por_ciento(self):
        self.assertEqual(str(porcentaje_valido('5')), '5.0000')
    def test_actualizacion_cambia_firma(self):
        self.assertNotEqual(firma_politica(texto_versionado('5')), firma_politica(texto_versionado('6')))
    def test_misma_version_es_estable(self):
        self.assertEqual(firma_politica(texto_versionado('5.0000')), firma_politica(texto_versionado('5')))
    def test_texto_garantias(self):
        contenido = texto_versionado('5')
        self.assertIn('no se aplican retroactivamente', contenido)
        self.assertIn('retracto', contenido)
        self.assertIn('sin', 'sin')
    def test_no_acepta_negativo(self):
        with self.assertRaises(ValueError): porcentaje_valido('-1')
    def test_no_acepta_mayor_100(self):
        with self.assertRaises(ValueError): porcentaje_valido('101')
    def test_no_acepta_nan(self):
        with self.assertRaises(ValueError): porcentaje_valido('NaN')
    def test_no_acepta_inf(self):
        with self.assertRaises(ValueError): porcentaje_valido('Infinity')
