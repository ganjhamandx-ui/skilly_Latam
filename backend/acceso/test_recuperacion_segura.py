"""Regresiones de recuperacion con modelos simulados, sin conexiones a BD."""
import hashlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch

from django.test import SimpleTestCase
from django.utils import timezone

from .recuperacion import _revocar_sesiones_usuario, restablecer_contrasena


class RestablecimientoSeguroTests(SimpleTestCase):
    """Comprueba consumo único, expiración y atomicidad del restablecimiento."""

    def setUp(self):
        self.ahora = timezone.now()
        self.token = "token-sintetico-de-prueba"
        self.nueva_contrasena = object()
        self.usuario = SimpleNamespace(
            pk=7, password_hash="hash-anterior-simulado", save=Mock(),
        )
        self.recuperacion = SimpleNamespace(
            fecha_expiracion=self.ahora + timedelta(minutes=5),
            usado=False, save=Mock(),
        )
        self.tokens = self.iniciar_patch("acceso.recuperacion.RecuperacionAcceso.objects")
        self.usuarios = self.iniciar_patch("acceso.recuperacion.Usuario.objects")
        self.sesiones = self.iniciar_patch("acceso.recuperacion.Session.objects")
        self.hash_password = self.iniciar_patch("acceso.recuperacion.make_password")
        self.hash_password.return_value = "hash-nuevo-simulado"
        self.reloj = self.iniciar_patch("acceso.recuperacion.timezone.now")
        self.reloj.return_value = self.ahora
        self.atomic = MagicMock()
        self.transaccion = self.iniciar_patch("acceso.recuperacion.transaction.atomic")
        self.transaccion.return_value = self.atomic
        self.tokens.filter.return_value.values_list.return_value.first.return_value = self.usuario.pk
        self.tokens.select_for_update.return_value.filter.return_value.first.return_value = self.recuperacion
        self.usuarios.select_for_update.return_value.get.return_value = self.usuario
        self.sesiones.filter.return_value.iterator.return_value = iter(())

    def iniciar_patch(self, destino):
        parche = patch(destino)
        self.addCleanup(parche.stop)
        return parche.start()

    def restablecer(self):
        return restablecer_contrasena(self.token, self.nueva_contrasena)

    def test_cambio_invalida_tokens_del_mismo_usuario_y_revoca_sus_sesiones(self):
        propia = SimpleNamespace(
            session_key="sesion-propia", get_decoded=lambda: {"id_usuario": self.usuario.pk},
        )
        ajena = SimpleNamespace(
            session_key="sesion-ajena", get_decoded=lambda: {"id_usuario": 8},
        )
        self.sesiones.filter.return_value.iterator.return_value = iter((propia, ajena))

        self.assertEqual(self.restablecer(), (True, "CONTRASENA_ACTUALIZADA"))

        self.hash_password.assert_called_once_with(self.nueva_contrasena)
        self.assertEqual(self.usuario.password_hash, "hash-nuevo-simulado")
        self.assertEqual(self.usuario.fecha_actualizacion, self.ahora)
        self.usuario.save.assert_called_once_with(
            update_fields=["password_hash", "fecha_actualizacion"],
        )
        self.assertTrue(self.recuperacion.usado)
        self.recuperacion.save.assert_called_once_with(update_fields=["usado"])
        self.assertEqual(self.tokens.filter.call_args_list, [
            call(token_hash=hashlib.sha256(self.token.encode("utf-8")).hexdigest(), usado=False),
            call(id_usuario=self.usuario, usado=False),
        ])
        self.tokens.filter.return_value.update.assert_called_once_with(usado=True)
        self.assertEqual(self.sesiones.filter.call_args_list, [
            call(expire_date__gt=self.ahora),
            call(session_key__in=["sesion-propia"]),
        ])
        self.sesiones.filter.return_value.delete.assert_called_once_with()
        self.atomic.__exit__.assert_called_once_with(None, None, None)

    def test_bloquea_usuario_antes_de_revalidar_y_bloquear_el_token(self):
        orden = []
        self.usuarios.select_for_update.return_value.get.side_effect = (
            lambda **kwargs: orden.append("usuario") or self.usuario
        )
        self.tokens.select_for_update.return_value.filter.return_value.first.side_effect = (
            lambda: orden.append("token") or self.recuperacion
        )

        self.restablecer()

        self.assertEqual(orden, ["usuario", "token"])
        self.usuarios.select_for_update.return_value.get.assert_called_once_with(pk=self.usuario.pk)
        self.tokens.select_for_update.return_value.filter.assert_called_once_with(
            token_hash=hashlib.sha256(self.token.encode("utf-8")).hexdigest(),
            usado=False, id_usuario=self.usuario,
        )

    def test_token_desconocido_no_modifica_usuario_tokens_ni_sesiones(self):
        self.tokens.filter.return_value.values_list.return_value.first.return_value = None

        self.assertEqual(self.restablecer(), (False, "TOKEN_INVALIDO_O_UTILIZADO"))

        self.usuarios.select_for_update.assert_not_called()
        self.hash_password.assert_not_called()
        self.tokens.filter.return_value.update.assert_not_called()
        self.sesiones.filter.assert_not_called()

    def test_token_consumido_mientras_esperaba_el_usuario_no_cambia_contrasena(self):
        self.tokens.select_for_update.return_value.filter.return_value.first.return_value = None

        self.assertEqual(self.restablecer(), (False, "TOKEN_INVALIDO_O_UTILIZADO"))

        self.hash_password.assert_not_called()
        self.usuario.save.assert_not_called()
        self.tokens.filter.return_value.update.assert_not_called()
        self.sesiones.filter.assert_not_called()

    def test_token_expirado_conserva_hash_tokens_y_sesiones(self):
        self.recuperacion.fecha_expiracion = self.ahora - timedelta(seconds=1)

        self.assertEqual(self.restablecer(), (False, "TOKEN_EXPIRADO"))

        self.hash_password.assert_not_called()
        self.usuario.save.assert_not_called()
        self.recuperacion.save.assert_not_called()
        self.tokens.filter.return_value.update.assert_not_called()
        self.sesiones.filter.assert_not_called()

    def test_fallo_de_revocacion_se_propaga_dentro_de_la_transaccion(self):
        error = RuntimeError("fallo simulado de revocacion")
        self.sesiones.filter.side_effect = error

        with self.assertRaises(RuntimeError):
            self.restablecer()

        self.assertTrue(self.atomic.__enter__.called)
        argumentos = self.atomic.__exit__.call_args.args
        self.assertIs(argumentos[0], RuntimeError)
        self.assertIs(argumentos[1], error)


class RevocacionSesionesTests(SimpleTestCase):
    """Comprueba que cambiar la contraseña revoque solo sesiones del usuario afectado."""

    @patch("acceso.recuperacion.Session.objects")
    def test_revoca_ids_enteros_o_texto_y_conserva_otros_usuarios(self, sesiones):
        def sesion(clave, contenido):
            return SimpleNamespace(session_key=clave, get_decoded=lambda: contenido)

        sesiones.filter.return_value.iterator.return_value = iter((
            sesion("propia-entero", {"id_usuario": 7}),
            sesion("propia-texto", {"id_usuario": "7"}),
            sesion("ajena", {"id_usuario": 8}),
            sesion("anonima", {}),
        ))
        ahora = timezone.now()

        _revocar_sesiones_usuario(7, ahora)

        self.assertEqual(sesiones.filter.call_args_list, [
            call(expire_date__gt=ahora),
            call(session_key__in=["propia-entero", "propia-texto"]),
        ])
        sesiones.filter.return_value.delete.assert_called_once_with()

    @patch("acceso.recuperacion.Session.objects")
    def test_sin_sesiones_propias_no_borra_sesiones_ajenas(self, sesiones):
        sesiones.filter.return_value.iterator.return_value = iter((
            SimpleNamespace(session_key="ajena", get_decoded=lambda: {"id_usuario": 8}),
        ))

        _revocar_sesiones_usuario(7, timezone.now())

        sesiones.filter.return_value.delete.assert_not_called()
        self.assertEqual(sesiones.filter.call_count, 1)
