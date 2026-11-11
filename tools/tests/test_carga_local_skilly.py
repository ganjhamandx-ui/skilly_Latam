"""Guardias de carga offline: sin procesos, red, PostgreSQL ni datos privados."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock


SPEC = importlib.util.spec_from_file_location("_carga_local_tested", Path(__file__).resolve().parents[1] / "carga_local_skilly.py")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class LoadSafetyTests(unittest.TestCase):
    def test_namespace_actual_se_lee_por_ast_sin_ejecutar_settings(self):
        namespace = "skilly-local-" + "a" * 40
        with tempfile.TemporaryDirectory(prefix="skilly-cache-namespace-") as temporary:
            file = Path(temporary) / "skilly_local.py"
            file.write_text("raise RuntimeError('No ejecutar esta configuración')\n"
                            "CACHES[ACCESO_CACHE_ALIAS]['KEY_PREFIX']=" + repr(namespace) + "\n", encoding="utf-8")
            self.assertTrue(TOOL.settings_namespace_matches(file, namespace))

    def test_namespace_alterado_no_pasa_validacion(self):
        namespace = "skilly-local-" + "a" * 40
        with tempfile.TemporaryDirectory(prefix="skilly-cache-namespace-") as temporary:
            file = Path(temporary) / "skilly_local.py"
            file.write_text("CACHES[ACCESO_CACHE_ALIAS]['KEY_PREFIX']=" + repr(namespace) + "\n", encoding="utf-8")
            self.assertFalse(TOOL.settings_namespace_matches(file, "skilly-local-" + "b" * 40))

    def test_namespace_dinamico_o_sobrescrito_no_se_admite(self):
        namespace = "skilly-local-" + "a" * 40
        with tempfile.TemporaryDirectory(prefix="skilly-cache-namespace-") as temporary:
            file = Path(temporary) / "skilly_local.py"
            file.write_text("CACHES[ACCESO_CACHE_ALIAS]['KEY_PREFIX']=os.getenv('OTRO')\n", encoding="utf-8")
            self.assertFalse(TOOL.settings_namespace_matches(file, namespace))
            file.write_text(("CACHES[ACCESO_CACHE_ALIAS]['KEY_PREFIX']=" + repr(namespace) + "\n") * 2, encoding="utf-8")
            self.assertFalse(TOOL.settings_namespace_matches(file, namespace))

    def test_percentiles_reales_por_interpolacion_y_muestra_vacia(self):
        self.assertIsNone(TOOL.percentile([], .95))
        self.assertEqual(TOOL.percentile([10, 20, 30, 40, 50], .50), 30)
        self.assertEqual(TOOL.percentile([10, 20, 30, 40, 50], .95), 48)
        self.assertAlmostEqual(TOOL.percentile([10, 20, 30, 40, 50], .99), 49.6)

    def test_maximo_64_escrituras_por_etapa(self):
        metrics = TOOL.Metrics()
        for index in range(64):
            self.assertTrue(metrics.reserve_write("stage", index % 8, float(index)))
        self.assertFalse(metrics.reserve_write("stage", 0, 1000))
        self.assertEqual(metrics.write_counts["stage"], 64)

    def test_cliente_no_puede_escribir_mas_de_una_vez_por_segundo(self):
        metrics = TOOL.Metrics()
        self.assertTrue(metrics.reserve_write("stage", 0, 100))
        self.assertFalse(metrics.reserve_write("stage", 0, 100.99))
        self.assertTrue(metrics.reserve_write("stage", 1, 100.1))
        self.assertTrue(metrics.reserve_write("stage", 0, 101))

    def test_evento_parada_impide_reservar_nuevas_escrituras(self):
        metrics = TOOL.Metrics()
        metrics.halt("fixture_static_reason")
        self.assertFalse(metrics.reserve_write("stage", 0, 100))
        metrics.halt("second_reason")
        self.assertEqual(metrics.stop_reason, "fixture_static_reason")

    def test_mas_de_uno_por_ciento_5xx_detiene_la_carga(self):
        metrics = TOOL.Metrics()
        for _ in range(99):
            metrics.record("stage", "catalog", 0, 200, 10, {200})
        metrics.record("stage", "catalog", 0, 500, 10, {200, 500})
        self.assertFalse(metrics.stop.is_set())  # Exactamente 1%, aún no supera el límite.
        metrics.record("stage", "catalog", 0, 503, 10, {200, 503})
        self.assertEqual(metrics.stop_reason, "http_5xx_over_one_percent")

    def test_cinco_5xx_consecutivos_detienen_aun_bajo_uno_por_ciento(self):
        metrics = TOOL.Metrics()
        for _ in range(1000):
            metrics.record("stage", "catalog", 0, 200, 1, {200})
        for _ in range(5):
            metrics.record("stage", "catalog", 0, 500, 1, {200, 500})
        self.assertEqual(metrics.stop_reason, "five_consecutive_5xx")

    def test_p95_superior_a_tres_segundos_detiene_la_carga(self):
        metrics = TOOL.Metrics()
        metrics.record("stage", "session", 0, 200, 1000, {200})
        metrics.record("stage", "session", 1, 200, 3200, {200})
        self.assertEqual(metrics.stop_reason, "p95_over_three_seconds")

    def test_403_no_se_ignora_ni_desactiva_csrf(self):
        metrics = TOOL.Metrics()
        metrics.record("stage", "update_own_availability", 0, 403, 1, {200})
        self.assertEqual(metrics.stop_reason, "unexpected_http_status")

    def test_patch_de_objeto_ajeno_se_rechaza_antes_de_red(self):
        client = TOOL.Client(("http://127.0.0.2:53111", "http://127.0.0.2:53112"), "http://127.0.0.2:53113")
        client.opener = Mock()
        with self.assertRaises(TOOL.LoadRejected):
            client.request(0, "update_availability", method="PATCH", payload={"hora_fin": "10:16:00"}, block_id=99)
        client.opener.open.assert_not_called()

    def test_contexto_de_un_solo_worker_no_inicia_carga(self):
        context = {"database_port": 57647, "external_payments_and_mail": False,
                   "frontend_origin": "http://127.0.0.2:53113", "run_dir": str(TOOL.ROOT.parent / "fixture-run"),
                   "backend_workers": [{"origin": "http://127.0.0.2:53111", "pid": 999}]}
        launcher = SimpleNamespace(context_from=lambda value: context)
        with self.assertRaises(TOOL.LoadRejected) as error:
            TOOL.checked_context(launcher, "fixture-context")
        self.assertEqual(error.exception.code, "two_workers_required")

    def test_cpu_sostenida_tres_muestras_detiene_sin_procesos_reales(self):
        metrics = TOOL.Metrics()
        psutil = SimpleNamespace(cpu_percent=Mock(side_effect=[0, 71, 72, 73]),
                                 virtual_memory=lambda: SimpleNamespace(available=3 * 1024 ** 3))
        done = SimpleNamespace(wait=Mock(side_effect=[False, False, False, True]))
        TOOL.resource_monitor(psutil, [], metrics, done)
        self.assertEqual(metrics.stop_reason, "global_cpu_over_70_three_samples")
        self.assertEqual(len(metrics.resources), 3)

    def test_memoria_disponible_baja_detiene_sin_procesos_reales(self):
        metrics = TOOL.Metrics()
        psutil = SimpleNamespace(cpu_percent=lambda **kwargs: 0,
                                 virtual_memory=lambda: SimpleNamespace(available=1024 ** 3))
        done = SimpleNamespace(wait=Mock(side_effect=[False, True]))
        TOOL.resource_monitor(psutil, [], metrics, done)
        self.assertEqual(metrics.stop_reason, "available_ram_below_two_gib")


if __name__ == "__main__":
    unittest.main()
