"""Pruebas focalizadas de parámetros y autorización, sin tocar PostgreSQL."""
from decimal import Decimal
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from acceso.permissions import EsAdministracionSkilly
from backoffice.configuracion_cargo_cancelacion_e3 import (
    ActualizarCargoCancelacionSerializer,
    ConfiguracionCargoCancelacionView,
    CLAVE_CARGO_CANCELACION,
)


class ConfiguracionCargoCancelacionE3Tests(SimpleTestCase):
    """Comprueba aislamiento, permisos y trazabilidad del cargo de cancelación."""

    def test_clave_aislada_de_comision(self):
        """Comprueba que el cargo de cancelación utiliza una clave independiente de la comisión."""
        self.assertEqual(CLAVE_CARGO_CANCELACION, "cancelacion_injustificada_porcentaje")
        self.assertNotEqual(CLAVE_CARGO_CANCELACION, "comision_porcentaje")

    def test_porcentaje_valido_con_decimales(self):
        """Conserva un porcentaje válido de cuatro decimales como Decimal."""
        serializer = ActualizarCargoCancelacionSerializer(data={"valor_nuevo": "7.5000"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["valor_nuevo"], Decimal("7.5000"))

    def test_cero_es_valido(self):
        """Admite desactivar el cargo mediante un porcentaje igual a cero."""
        serializer = ActualizarCargoCancelacionSerializer(data={"valor_nuevo": "0"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_no_permite_negativos_ni_superar_100(self):
        """Rechaza porcentajes fuera del intervalo inclusivo de cero a cien."""
        for numero in ["-1", "101", "100.0001"]:
            with self.subTest(numero=numero):
                serializer = ActualizarCargoCancelacionSerializer(data={"valor_nuevo": numero})
                self.assertFalse(serializer.is_valid())

    def test_rechaza_mas_de_cuatro_decimales(self):
        """Rechaza precisión superior a los cuatro decimales admitidos."""
        serializer = ActualizarCargoCancelacionSerializer(data={"valor_nuevo": "5.12345"})
        self.assertFalse(serializer.is_valid())

    def test_requiere_permiso_administrativo(self):
        """Comprueba la declaración del permiso administrativo en la vista."""
        self.assertIn(EsAdministracionSkilly, ConfiguracionCargoCancelacionView.permission_classes)

    def test_endpoint_responde_a_get_y_patch(self):
        """Comprueba que la vista declara manejadores de consulta y actualización."""
        self.assertTrue(callable(getattr(ConfiguracionCargoCancelacionView, "get", None)))
        self.assertTrue(callable(getattr(ConfiguracionCargoCancelacionView, "patch", None)))
