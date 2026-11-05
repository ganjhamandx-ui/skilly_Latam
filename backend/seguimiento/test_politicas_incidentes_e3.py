"""Pruebas focalizadas E3 (sin escrituras en PostgreSQL)."""

from unittest import TestCase

from seguimiento.politicas_incidentes import MOTIVOS, orientacion_reclamo


class PoliticasIncidentesE3Tests(TestCase):
    def test_catalogo_sin_duplicados(self):
        self.assertEqual(len(MOTIVOS), 7)
        self.assertEqual(len(set(MOTIVOS)), len(MOTIVOS))

    def test_motivos_respetan_tamano_campo(self):
        self.assertTrue(all(0 < len(m) <= 120 for m in MOTIVOS))

    def test_reprogramacion_exige_gestion_administrativa(self):
        mensaje = orientacion_reclamo(MOTIVOS[3])["accion_recomendada"]
        self.assertIn("gestión de agenda", mensaje)

    def test_no_se_aplica_penalizacion_ni_reversa_automatica(self):
        for motivo in MOTIVOS:
            guia = orientacion_reclamo(motivo)
            self.assertIn("no libera o devuelve dinero", guia["precaucion"])
            self.assertIn("no suspende", guia["precaucion"])

    def test_compatibilidad_con_reclamo_historico(self):
        guia = orientacion_reclamo("Un motivo anterior libre")
        self.assertEqual(guia["tipo"], "Motivo anterior o libre")
