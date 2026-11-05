"""Comprobaciones focalizadas de la redacción contractual nueva, sin BD."""
import unittest
from .politica_texto_cancelacion_e3 import texto_versionado, firma_politica


class PoliticaBreveTests(unittest.TestCase):
    def test_aviso_sin_codigos_ni_comisiones_internas(self):
        texto = texto_versionado('5')
        self.assertNotIn('SKILLY-E3-CANCELACION', texto)
        self.assertNotIn('comisión de servicio', texto)
        self.assertNotIn('comisión normal', texto)
        self.assertLessEqual(len(texto.split()), 90)

    def test_condiciones_y_excepciones_claras(self):
        texto = texto_versionado('5')
        for fragmento in ['5%', 'justificación válida', 'no hay descuentos automáticos',
                          'devolución íntegra', 'retracto', 'no se aplican retroactivamente']:
            self.assertIn(fragmento, texto)

    def test_mantiene_firma_determinista_por_porcentaje(self):
        self.assertEqual(firma_politica(texto_versionado('5.0000')), firma_politica(texto_versionado('5')))
        self.assertNotEqual(firma_politica(texto_versionado('5')), firma_politica(texto_versionado('6')))
