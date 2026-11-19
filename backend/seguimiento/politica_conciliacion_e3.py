"""Desglose inmutable de conciliación académica de una reversa parcial.

No confirma transferencia bancaria, abono profesional, cargo cobrado ni refund Webpay.
"""
from decimal import Decimal, InvalidOperation

class ConciliacionInvalida(ValueError):
    """Señala una combinación económica que no puede conciliarse."""

    pass


def importe(valor):
    """Convierte un valor monetario a decimal no negativo y finito."""

    try:
        x = Decimal(str(valor))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ConciliacionInvalida('Monto inválido.') from exc
    if not x.is_finite() or x < 0 or x.as_tuple().exponent < -2:
        raise ConciliacionInvalida('Monto negativo, no finito o con más de dos decimales.')
    return x.quantize(Decimal('0.01'))


def desglose_parcial(*, total, trabajo, cargo, devolucion, monto_reversa,
                     metodo_pago, estado_pago, estado_verificacion, estado_reversa):
    """Valida que pago, devolución, cargo y reversa formen un desglose consistente."""

    total, trabajo, cargo, devolucion, monto_reversa = map(importe,
        (total, trabajo, cargo, devolucion, monto_reversa))
    if total <= 0 or devolucion <= 0 or devolucion >= total:
        raise ConciliacionInvalida('Esta conciliación es solo para devoluciones parciales autorizadas.')
    if trabajo + cargo + devolucion != total:
        raise ConciliacionInvalida('El desglose no suma exactamente el monto de la contratación.')
    if monto_reversa != devolucion:
        raise ConciliacionInvalida('La reversa solicitada y la liquidación no coinciden.')
    if estado_pago != 'RETENIDO' or estado_verificacion != 'VERIFICADO':
        raise ConciliacionInvalida('El pago debe continuar retenido y verificado.')
    if estado_reversa != 'SOLICITADA':
        raise ConciliacionInvalida('La reversa debe seguir pendiente de ejecución.')
    if metodo_pago not in ('TRANSFERENCIA','WEBPAY_PLUS'):
        raise ConciliacionInvalida('Método de pago no admitido en la conciliación académica.')
    return {
        'total':total,'devolucion_pendiente':devolucion,
        'trabajo_pendiente_distribucion':trabajo,
        'cargo_pendiente_distribucion':cargo,
        'remanente_pendiente_distribucion': trabajo + cargo,
        'metodo_pago':metodo_pago,
        'estado':'SIMULACION_DOCUMENTAL',
    }
