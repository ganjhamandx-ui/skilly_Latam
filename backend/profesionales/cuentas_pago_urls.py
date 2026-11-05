from django.urls import path
from .cuentas_pago_api import MiCuentaPagoView, MisAbonosView, DestinoYAbonoAdministracionView

urlpatterns = [
    path('mi-cuenta-bancaria/', MiCuentaPagoView.as_view(), name='mi_cuenta_pago'),
    path('mis-abonos/', MisAbonosView.as_view(), name='mis_abonos'),
    path('administracion/pagos/<int:id_pago>/destino-abono/',
         DestinoYAbonoAdministracionView.as_view(), name='destino_abono_pago'),
]
