"""Errores de registro y correo: transacciones y respuestas sin datos privados.

ORM y SMTP simulados; las pruebas HTTP/PostgreSQL se ejecutan por separado.
"""
from contextlib import contextmanager
from smtplib import SMTPAuthenticationError
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase
from rest_framework import serializers

from .serializers import RegistroProfesionalSerializer
from .views import SolicitarRecuperacionView


class RegistroConcurrenteTests(SimpleTestCase):
    def setUp(self):
        self.datos = {"correo": "registro@example.invalid", "contrasena": "ficticia"}
        self.eventos = []

    @contextmanager
    def savepoint(self):
        self.eventos.append("inicio")
        try:
            yield
        except IntegrityError:
            self.eventos.append("rollback")
            raise
        else:
            self.eventos.append("commit")

    @patch("acceso.serializers.make_password", return_value="hash-ficticio")
    @patch("acceso.serializers.Usuario.objects")
    @patch("acceso.serializers.transaction.atomic")
    def test_conflicto_concurrente_devuelve_el_error_de_correo_tras_rollback(
        self, atomic, usuarios, _hash,
    ):
        atomic.side_effect = self.savepoint
        usuarios.create.side_effect = IntegrityError("conflicto simulado")

        def existe():
            self.assertEqual(self.eventos, ["inicio", "rollback"])
            return True

        usuarios.filter.return_value.exists.side_effect = existe
        with self.assertRaises(serializers.ValidationError) as error:
            RegistroProfesionalSerializer().create(self.datos)
        self.assertEqual(set(error.exception.detail), {"correo"})
        usuarios.filter.assert_called_once_with(correo__iexact=self.datos["correo"])
        self.assertEqual(str(error.exception.detail["correo"][0]),
                         "Ya existe una cuenta registrada con este correo.")

    @patch("acceso.serializers.make_password", return_value="hash-ficticio")
    @patch("acceso.serializers.Usuario.objects")
    @patch("acceso.serializers.transaction.atomic")
    def test_no_oculta_errores_de_integridad_ajenos_al_correo(
        self, atomic, usuarios, _hash,
    ):
        atomic.side_effect = self.savepoint
        usuarios.create.side_effect = IntegrityError("otra restriccion simulada")
        usuarios.filter.return_value.exists.return_value = False
        with self.assertRaises(IntegrityError):
            RegistroProfesionalSerializer().create(self.datos)
        self.assertEqual(self.eventos, ["inicio", "rollback"])

    @patch("acceso.serializers.make_password", return_value="hash-ficticio")
    @patch("acceso.serializers.Usuario.objects")
    @patch("acceso.serializers.transaction.atomic")
    def test_registro_normal_no_consulta_conflictos_y_conserva_hash_y_rol(
        self, atomic, usuarios, _hash,
    ):
        atomic.side_effect = self.savepoint
        esperado = usuarios.create.return_value
        self.assertIs(RegistroProfesionalSerializer().create(self.datos), esperado)
        usuarios.filter.assert_not_called()
        self.assertEqual(self.eventos, ["inicio", "commit"])
        self.assertEqual(usuarios.create.call_args.kwargs["rol"], "PROFESIONAL")
        self.assertEqual(usuarios.create.call_args.kwargs["password_hash"], "hash-ficticio")
        self.assertNotIn("contrasena", usuarios.create.call_args.kwargs)


class CorreoRecuperacionErroresTests(SimpleTestCase):
    def solicitar(self, usuario, enviados=1, error=None):
        request = SimpleNamespace(data={"correo": "recuperacion@example.invalid"})
        with (
            patch("acceso.views.Usuario.objects") as usuarios,
            patch("acceso.views.crear_recuperacion_acceso", return_value=("ficticio", Mock())),
            patch("acceso.views.enviar_correo_recuperacion", return_value=enviados,
                  side_effect=error),
            patch("acceso.views.transaction.atomic") as atomic,
        ):
            usuarios.filter.return_value.first.return_value = usuario
            respuesta = SolicitarRecuperacionView().post(request)
        return respuesta, atomic.return_value.__exit__.call_args

    def test_error_smtp_no_registra_contenido_ni_traceback_y_mantiene_respuesta_generica(self):
        inexistente, _ = self.solicitar(None)
        with self.assertLogs("acceso.views", level="WARNING") as logs:
            fallida, salida = self.solicitar(
                SimpleNamespace(pk=1),
                error=SMTPAuthenticationError(535, b"contenido-privado-sintetico"),
            )
        self.assertEqual(fallida.status_code, 200)
        self.assertEqual(fallida.data, inexistente.data)
        self.assertEqual(len(logs.records), 1)
        self.assertIsNone(logs.records[0].exc_info)
        self.assertEqual(logs.records[0].getMessage(), "Fallo el envio del correo de recuperacion.")
        self.assertNotIn("contenido-privado-sintetico", "\n".join(logs.output))
        self.assertIs(salida.args[0], SMTPAuthenticationError)

    def test_envio_cero_y_error_de_red_salen_con_rollback_y_mismo_mensaje(self):
        normal, _ = self.solicitar(SimpleNamespace(pk=1))
        for opciones in ({"enviados": 0}, {"error": OSError("dato-privado-sintetico")}):
            with self.subTest(opciones=tuple(opciones)), self.assertLogs("acceso.views", level="WARNING") as logs:
                respuesta, salida = self.solicitar(SimpleNamespace(pk=1), **opciones)
            self.assertEqual(respuesta.data, normal.data)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIsNotNone(salida.args[0])
            self.assertIsNone(logs.records[0].exc_info)
