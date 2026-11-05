"""Regresiones de codificacion de archivos, sin conectar a PostgreSQL."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import verificar_codificacion as control


class VerificarCodificacionTests(unittest.TestCase):
    def test_sintaxis_ascii_valida_no_es_corrupcion(self):
        for linea in (
            r"if (!/\.(pdf|jpe?g|png)$/i.test(comprobante.name)) {",
            "<p>{visible?datos.numero_cuenta:datos.cuenta.numero_oculto}</p>",
            "const url = '/api/listado/?estado=ACTIVO'",
        ):
            with self.subTest(linea=linea):
                self.assertFalse(control.linea_sospechosa(linea))

    def test_conserva_deteccion_de_mojibake_y_reemplazo_unicode(self):
        for linea in (
            "Contrase\u00c3\u00b1a",
            "Precio\u00c2\u00a0total",
            "Registrando\u00e2\u20ac\u00a6",
            "Texto con \ufffd reemplazo",
        ):
            with self.subTest(linea=linea):
                self.assertTrue(control.linea_sospechosa(linea))

    def revisar_archivo_temporal(self, contenido):
        with tempfile.TemporaryDirectory(prefix='skilly_codificacion_') as carpeta:
            raiz = Path(carpeta)
            archivo = raiz / 'ejemplo.js'
            archivo.write_bytes(contenido)
            salida = io.StringIO()
            with patch.object(control, 'RAIZ', raiz), patch.object(
                control, 'obtener_archivos', return_value=[archivo],
            ), contextlib.redirect_stdout(salida):
                resultado = control.revisar_archivos()
            return resultado, salida.getvalue()

    def test_lectura_rechaza_bytes_utf8_invalidos(self):
        resultado, salida = self.revisar_archivo_temporal(b'const texto = "\xff";')
        self.assertGreater(resultado, 0)
        self.assertIn('ARCHIVOS INVALIDOS: 1', salida)

    def test_lectura_acepta_acentos_utf8_bom_y_sintaxis_valida(self):
        texto = "const titulo = 'Sesi\u00f3n'; const foto = /jpe?g/;"
        resultado, salida = self.revisar_archivo_temporal(texto.encode('utf-8-sig'))
        self.assertEqual(resultado, 0)
        self.assertIn('ARCHIVOS SOSPECHOSOS: 0', salida)
        self.assertIn('ARCHIVOS INVALIDOS: 0', salida)


if __name__ == '__main__':
    unittest.main()
