"""Desglose inmutable de conciliación académica de una reversa parcial.

No confirma transferencia bancaria, abono profesional, cargo cobrado ni refund Webpay.
"""
from decimal import Decimal, InvalidOperation

class ConciliacionInvalida(ValueError):
    """Señala una combinación económica que no puede conciliarse."""

    pass


def importe(valor):
    """Normaliza un importe no negativo a dos posiciones decimales.

    Args:
        valor (Decimal | str | int | float): Importe convertible mediante texto,
            finito y representado con un máximo de dos posiciones decimales.

    Returns:
        Decimal: Importe cuantizado a centavos, sin redondear entradas inválidas.

    Raises:
        ConciliacionInvalida: Si la conversión falla, el importe es negativo,
            no es finito o su representación tiene más de dos decimales.

    Example:
        >>> importe("1250.5")
        Decimal('1250.50')
    """

    try:
        x = Decimal(str(valor))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ConciliacionInvalida('Monto inválido.') from exc
    if not x.is_finite() or x < 0 or x.as_tuple().exponent < -2:
        raise ConciliacionInvalida('Monto negativo, no finito o con más de dos decimales.')
    return x.quantize(Decimal('0.01'))


def desglose_parcial(*, total, trabajo, cargo, devolucion, monto_reversa,
                     metodo_pago, estado_pago, estado_verificacion, estado_reversa):
    """Valida el desglose de una devolución parcial pendiente de ejecución.

    Args:
        total (Decimal): Total positivo de la contratación.
        trabajo (Decimal): Importe no negativo del trabajo acreditado.
        cargo (Decimal): Cargo no negativo autorizado por cancelación.
        devolucion (Decimal): Devolución mayor que cero y menor que el total.
        monto_reversa (Decimal): Importe solicitado, idéntico a la devolución.
        metodo_pago (str): ``TRANSFERENCIA`` o ``WEBPAY_PLUS``.
        estado_pago (str): Debe ser ``RETENIDO``.
        estado_verificacion (str): Debe ser ``VERIFICADO``.
        estado_reversa (str): Debe ser ``SOLICITADA``.

    Returns:
        dict: Importes Decimal, método y estado ``SIMULACION_DOCUMENTAL``.
        El remanente es trabajo más cargo y sigue pendiente de distribución.
        No persiste datos ni invoca servicios de pago.

    Raises:
        ConciliacionInvalida: Si algún importe no es válido, el desglose no
            suma exactamente el total, la reversa difiere de la devolución
            o los estados y el método no permiten la conciliación.
    """

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
