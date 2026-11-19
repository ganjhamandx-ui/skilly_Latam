"""Aplica protección CSRF explícita a operaciones administrativas de pago."""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from .views import (
    DetallePagoAdministracionView,
    LiberarPagoAdministracionView,
    ReversasPagoAdministracionView,
)


@method_decorator(csrf_protect, name="dispatch")
class DetallePagoSeguroAdministracionView(
    DetallePagoAdministracionView
):
    pass


@method_decorator(csrf_protect, name="dispatch")
class LiberarPagoSeguroAdministracionView(
    LiberarPagoAdministracionView
):
    pass


@method_decorator(csrf_protect, name="dispatch")
class ReversasPagoSegurasAdministracionView(
    ReversasPagoAdministracionView
):
    pass
