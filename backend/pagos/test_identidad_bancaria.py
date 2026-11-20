"""Identidad bancaria y rechazos de API con cursores/ORM simulados, sin BD."""
from contextlib import nullcontext
from datetime import timedelta, time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from backoffice import cuentas_bancarias_api as cuentas_api
from backoffice import transferencia_disponibilidad as disponibilidad_backoffice
from config.identidad_bancaria import identidad_bancaria_autorizada
from pagos import transferencia_disponibilidad as disponibilidad_pagos
from pagos import views as pagos_views


def conexion_ficticia(nombre='skilly', *, usuario='skilly_app', filas=()):
    """Construye una conexión y un cursor simulados con respuestas secuenciales.

    Args:
        nombre: Nombre configurado de la base que se evaluará.
        usuario: Rol configurado de conexión.
        filas: Resultados sucesivos que devolverá fetchone.

    Returns:
        tuple: Conexión ficticia y cursor que permite inspeccionar las consultas.
    """
    conexion = SimpleNamespace(settings_dict={'NAME': nombre, 'USER': usuario}, cursor=MagicMock())
    cursor = conexion.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = list(filas)
    return conexion, cursor


class IdentidadBancariaTests(SimpleTestCase):
    """Comprueba coincidencia estricta de base, esquema y rol sin abrir conexiones."""
    def test_base_configurada_original_y_clon_son_validas_con_mismo_rol_y_esquema(self):
        """Admite nombres de base distintos cuando coinciden con la configuración y la identidad exigida."""
        for nombre in ('skilly', 'skilly_android_fixture', 'otra_base_configurada'):
            with self.subTest(nombre=nombre):
                conexion, _cursor = conexion_ficticia(nombre)
                self.assertTrue(identidad_bancaria_autorizada(conexion, (nombre, 'skilly', 'skilly_app')))
                conexion.cursor.assert_not_called()

    def test_nombre_real_distinto_no_se_autoriza_por_ser_original_o_parecer_clon(self):
        """Exige coincidencia exacta del nombre real con el configurado."""
        conexion, _cursor = conexion_ficticia('skilly_android_fixture')
        for real in ('skilly', 'skilly_android_otro', 'postgres'):
            with self.subTest(real=real):
                self.assertFalse(identidad_bancaria_autorizada(conexion, (real, 'skilly', 'skilly_app')))

    def test_esquema_y_rol_no_se_relajan_por_coincidir_el_nombre(self):
        """Mantiene las restricciones de esquema y rol aunque coincida la base."""
        conexion, _cursor = conexion_ficticia()
        for identidad in (('skilly', 'public', 'skilly_app'),
                          ('skilly', 'skilly_cu040_pruebas', 'skilly_app'),
                          ('skilly', 'skilly', 'postgres'),
                          ('skilly', 'skilly', 'otro_rol'), None, ('skilly', 'skilly')):
            with self.subTest(identidad=identidad):
                self.assertFalse(identidad_bancaria_autorizada(conexion, identidad))

    def test_usuario_configurado_privilegiado_o_ausente_no_se_autoriza(self):
        """Rechaza usuarios configurados distintos del rol de aplicación exigido."""
        for usuario in ('postgres', 'root', 'otro_rol', '', None):
            conexion, _cursor = conexion_ficticia(usuario=usuario)
            with self.subTest(usuario=usuario):
                self.assertFalse(identidad_bancaria_autorizada(conexion, ('skilly', 'skilly', 'skilly_app')))

    def test_configuracion_de_base_ausente_o_invalida_falla_cerrada(self):
        """Rechaza configuraciones incompletas, tipos inesperados y nombres ambiguos."""
        for nombre in ('', ' ', None, False, 42, ' skilly', 'skilly ', 'skilly\x00'):
            conexion, _cursor = conexion_ficticia(nombre)
            with self.subTest(tipo=type(nombre).__name__):
                self.assertFalse(identidad_bancaria_autorizada(conexion, (nombre, 'skilly', 'skilly_app')))
        for configuracion in ({}, None, 'skilly'):
            self.assertFalse(identidad_bancaria_autorizada(SimpleNamespace(settings_dict=configuracion), ('skilly', 'skilly', 'skilly_app')))
        self.assertFalse(identidad_bancaria_autorizada(SimpleNamespace(), ('skilly', 'skilly', 'skilly_app')))


class DisponibilidadIdentidadBancariaTests(SimpleTestCase):
    """Comprueba los adaptadores de disponibilidad bancaria con cursores simulados."""
    modulos = (disponibilidad_pagos, disponibilidad_backoffice)
    cuenta = (7, 'Titular ficticio', '11111111-1', 'Banco ficticio', 'VISTA', '12345678', 'pruebas@example.invalid')

    def consultar(self, modulo, conexion, *, referencia=True, prestacion=True, pago=False):
        """Consulta disponibilidad sustituyendo referencia, prestación, pago y conexión.

        Args:
            modulo: Adaptador de disponibilidad que se despachará.
            conexion: Conexión ficticia con resultados de identidad y cuenta.
            referencia: Indica si la referencia privada se considera válida.
            prestacion: Indica si existe una prestación pendiente con condiciones.
            pago: Indica si ya existe un pago para la prestación.

        Returns:
            Response: Respuesta producida por el adaptador bajo el escenario simulado.
        """
        with patch.object(modulo, 'connection', conexion), \
                patch.object(modulo, 'leer_referencia_seguimiento', return_value={'id_solicitud': 11, 'id_contacto': 12} if referencia else None), \
                patch.object(modulo.PrestacionServicio, 'objects') as prestaciones, \
                patch.object(modulo.Pago, 'objects') as pagos:
            prestaciones.filter.return_value.first.return_value = (
                SimpleNamespace(estado='PENDIENTE_CONTRATACION', condiciones_comunicadas='Condiciones ficticias') if prestacion else None)
            pagos.filter.return_value.exists.return_value = pago
            response = modulo.DisponibilidadTransferenciaEmpresaView().get(SimpleNamespace(), 'referencia-ficticia')
        return response

    def test_cuenta_disponible_en_original_y_base_configurada_distinta(self):
        """Comprueba disponibilidad con identidad válida tanto en la base original como en otra configurada."""
        for modulo in self.modulos:
            for nombre in ('skilly', 'skilly_android_fixture'):
                conexion, cursor = conexion_ficticia(nombre, filas=[(nombre, 'skilly', 'skilly_app'), (True,), self.cuenta])
                with self.subTest(modulo=modulo.__name__, nombre=nombre):
                    response = self.consultar(modulo, conexion)
                    self.assertEqual(response.status_code, 200)
                    self.assertIs(response.data['disponible'], True)
                    self.assertEqual(response.data['cuenta']['id_cuenta'], 7)
                    self.assertEqual(cursor.execute.call_count, 3)

    def test_identidad_incorrecta_devuelve_503_sin_consultar_datos_de_cuentas(self):
        """Comprueba el rechazo tras consultar identidad y antes de leer cuentas bancarias."""
        casos = (
            ('skilly_android_fixture', 'skilly_app', ('skilly', 'skilly', 'skilly_app')),
            ('skilly', 'skilly_app', ('skilly', 'public', 'skilly_app')),
            ('skilly', 'skilly_app', ('skilly', 'skilly', 'postgres')),
            ('skilly', 'postgres', ('skilly', 'skilly', 'skilly_app')),
            ('', 'skilly_app', ('skilly', 'skilly', 'skilly_app')),
        )
        for modulo in self.modulos:
            for nombre, usuario, identidad in casos:
                conexion, cursor = conexion_ficticia(nombre, usuario=usuario, filas=[identidad])
                with self.subTest(modulo=modulo.__name__, usuario=usuario, identidad=identidad):
                    response = self.consultar(modulo, conexion)
                    self.assertEqual(response.status_code, 503)
                    self.assertIs(response.data['disponible'], False)
                    self.assertNotIn('cuenta', response.data)
                    self.assertEqual(cursor.execute.call_count, 1)

    def test_referencia_prestacion_y_pago_siguen_limitando_la_consulta(self):
        """Comprueba que requisitos empresariales se evalúen antes de consultar datos bancarios."""
        for modulo in self.modulos:
            for argumentos, estado in (({'referencia': False}, 400), ({'prestacion': False}, 404), ({'pago': True}, 200)):
                conexion, _cursor = conexion_ficticia()
                with self.subTest(modulo=modulo.__name__, caso=argumentos):
                    response = self.consultar(modulo, conexion, **argumentos)
                    self.assertEqual(response.status_code, estado)
                    self.assertNotIn('cuenta', response.data)
                    conexion.cursor.assert_not_called()

    def test_base_valida_sin_principal_no_entrega_datos_bancarios(self):
        """Comprueba indisponibilidad cuando la consulta de existencia previa devuelve falso."""
        for modulo in self.modulos:
            conexion, cursor = conexion_ficticia('skilly_android_fixture', filas=[('skilly_android_fixture', 'skilly', 'skilly_app'), (False,)])
            response = self.consultar(modulo, conexion)
            self.assertEqual(response.status_code, 200)
            self.assertIs(response.data['disponible'], False)
            self.assertNotIn('cuenta', response.data)
            self.assertEqual(cursor.execute.call_count, 2)


class CuentasAdministracionIdentidadTests(SimpleTestCase):
    """Comprueba identidad y disponibilidad de tablas antes de consultar cuentas administrativas."""
    def test_base_configurada_distinta_permita_consultar_sin_cambiar_alias_o_tablas(self):
        """Conserva el alias default al admitir otra base expresamente configurada."""
        conexion, cursor = conexion_ficticia('skilly_android_fixture', filas=[('skilly_android_fixture', 'skilly', 'skilly_app'), (True,)])
        with patch.object(cuentas_api, 'connections', {'default': conexion}), patch.object(cuentas_api.Cuenta, 'objects') as cuentas:
            cuentas.using.return_value.order_by.return_value = []
            response = cuentas_api.CuentasBancariasView().get(SimpleNamespace())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {'cuentas': []})
            cuentas.using.assert_called_once_with('default')
            self.assertEqual(cursor.execute.call_count, 2)

    def test_rechazo_503_no_consulta_cuentas_ni_historial_ni_tablas(self):
        """Comprueba que una identidad rechazada impida lecturas posteriores del módulo bancario."""
        conexion, cursor = conexion_ficticia('skilly_android_fixture', filas=[('skilly', 'skilly', 'skilly_app')])
        with patch.object(cuentas_api, 'connections', {'default': conexion}), \
                patch.object(cuentas_api.Cuenta, 'objects') as cuentas, patch.object(cuentas_api.Cambio, 'objects') as cambios:
            response = cuentas_api.CuentasBancariasView().get(SimpleNamespace())
            self.assertEqual(response.status_code, 503)
            cuentas.using.assert_not_called()
            cambios.using.assert_not_called()
            self.assertEqual(cursor.execute.call_count, 1)

    def test_tablas_inexistentes_siguen_bloqueando_modulo(self):
        """Comprueba que la identidad válida no omita la exigencia de tablas disponibles."""
        conexion, cursor = conexion_ficticia('skilly_android_fixture', filas=[('skilly_android_fixture', 'skilly', 'skilly_app'), (False,)])
        with patch.object(cuentas_api, 'connections', {'default': conexion}), patch.object(cuentas_api.Cuenta, 'objects') as cuentas:
            response = cuentas_api.CuentasBancariasView().get(SimpleNamespace())
            self.assertEqual(response.status_code, 503)
            cuentas.using.assert_not_called()
            self.assertEqual(cursor.execute.call_count, 2)


class InicioTransferenciaIdentidadTests(SimpleTestCase):
    """Comprueba rechazos de identidad y cuenta antes de guardar comprobantes o crear pagos."""
    def iniciar(self, identidad, *, usuario='skilly_app'):
        """Prepara una transferencia y simula las consultas hasta el rechazo bancario.

        Args:
            identidad: Fila de base, esquema y rol devuelta por el cursor simulado.
            usuario: Rol declarado en la configuración de la conexión ficticia.

        Returns:
            tuple: Respuesta de inicio de transferencia y cursor con llamadas registradas.
        """
        conexion, cursor = conexion_ficticia('skilly_android_fixture', usuario=usuario, filas=[identidad, None])
        servicio = SimpleNamespace(id_profesional_id=31, referencia_precio='10000 CLP')
        solicitud = SimpleNamespace(id_servicio=servicio)
        prestacion = SimpleNamespace(estado='PENDIENTE_CONTRATACION', condiciones_comunicadas='Condiciones ficticias',
            id_solicitud=solicitud, id_profesional_id=31)
        bloque = SimpleNamespace(id_profesional_id=31, estado='DISPONIBLE', fecha=timezone.now().date() + timedelta(days=2), hora_inicio=time(12))
        with patch.object(pagos_views, 'connection', conexion), \
                patch.object(pagos_views, 'leer_referencia_seguimiento', return_value={'id_solicitud': 11, 'id_contacto': 12}), \
                patch.object(pagos_views, 'IniciarPagoTransferenciaSerializer') as serializer, \
                patch.object(pagos_views.PrestacionServicio, 'objects') as prestaciones, \
                patch.object(pagos_views.Pago, 'objects') as pagos, \
                patch.object(pagos_views.ReservaDisponibilidad, 'objects') as reservas, \
                patch.object(pagos_views.Disponibilidad, 'objects') as bloques, \
                patch.object(pagos_views.ParametroSistema, 'objects') as parametros, \
                patch.object(pagos_views.transaction, 'atomic', return_value=nullcontext()), \
                patch.object(pagos_views, 'bloquear_pago_sin_aceptacion'), \
                patch.object(pagos_views.default_storage, 'save') as guardar:
            serializer.return_value.is_valid.return_value = True
            serializer.return_value.validated_data = {'comprobante_transferencia': object(), 'extension_comprobante': 'pdf'}
            prestaciones.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = prestacion
            pagos.select_for_update.return_value.filter.return_value.first.return_value = None
            reservas.select_for_update.return_value.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(id_disponibilidad_id=51)
            reservas.filter.return_value.exists.return_value = False
            bloques.select_for_update.return_value.filter.return_value.first.return_value = bloque
            parametros.filter.return_value.first.return_value = SimpleNamespace(valor_actual='10')
            response = pagos_views.IniciarPagoTransferenciaEmpresaView().post(SimpleNamespace(data={'id_cuenta_receptora': 7}), 'referencia-ficticia')
            guardar.assert_not_called()
            pagos.create.assert_not_called()
        return response, cursor

    def test_identidad_incorrecta_impide_bloqueo_bancario_guardado_y_creacion_pago(self):
        """Comprueba el rechazo de identidad antes del bloqueo de cuenta y las escrituras."""
        for identidad, usuario in ((('skilly', 'skilly', 'skilly_app'), 'skilly_app'),
                                   (('skilly_android_fixture', 'public', 'skilly_app'), 'skilly_app'),
                                   (('skilly_android_fixture', 'skilly', 'postgres'), 'skilly_app'),
                                   (('skilly_android_fixture', 'skilly', 'skilly_app'), 'postgres')):
            with self.subTest(identidad=identidad, usuario=usuario):
                response, cursor = self.iniciar(identidad, usuario=usuario)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(cursor.execute.call_count, 1)

    def test_base_configurada_avanza_y_conserva_rechazo_si_cuenta_mostrada_cambio(self):
        """Comprueba que una identidad válida aún exija la cuenta receptora mostrada a la organización."""
        response, cursor = self.iniciar(('skilly_android_fixture', 'skilly', 'skilly_app'))
        self.assertEqual(response.status_code, 409)
        self.assertIn('datos bancarios cambiaron', response.data['mensaje'])
        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn('LOCK TABLE skilly.cuenta_bancaria_skilly', cursor.execute.call_args_list[1].args[0])
