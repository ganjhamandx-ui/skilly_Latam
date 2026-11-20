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
    """Añade CSRF a la consulta y verificación administrativa heredadas del pago."""
    pass


@method_decorator(csrf_protect, name="dispatch")
class LiberarPagoSeguroAdministracionView(
    LiberarPagoAdministracionView
):
    """Exige CSRF antes de aplicar los controles heredados de liberación de pago."""
    pass


@method_decorator(csrf_protect, name="dispatch")
class ReversasPagoSegurasAdministracionView(
    ReversasPagoAdministracionView
):
    """Protege con CSRF el registro de reversas y conserva permisos y consultas base."""
    pass
