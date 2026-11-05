"""Rutas pendientes de activación, no incluidas en backoffice/urls.py."""
from django.urls import path
from .cuentas_bancarias_api import CuentasBancariasView, CuentaBancariaDetalleView, HistorialCuentasBancariasView
urlpatterns = [
    path('configuracion/cuentas-bancarias/', CuentasBancariasView.as_view(), name='cuentas_bancarias_skilly'),
    path('configuracion/cuentas-bancarias/<int:id_cuenta>/', CuentaBancariaDetalleView.as_view(), name='cuenta_bancaria_detalle'),
    path('configuracion/cuentas-bancarias/historial/', HistorialCuentasBancariasView.as_view(), name='cuentas_bancarias_historial'),
]
