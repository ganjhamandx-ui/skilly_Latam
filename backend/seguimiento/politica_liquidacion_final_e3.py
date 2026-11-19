"""Cálculo académico de liquidación, sin movimientos bancarios.
No equivale a resolución judicial ni sustituye verificación de derechos de retracto.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTAVO = Decimal('0.01')
PESO = Decimal('1')

def numero(valor):
    """Convierte un importe a decimal finito y no negativo."""

    try:
        n = Decimal(str(valor))
    except (TypeError, ValueError, InvalidOperation) as error:
        raise ValueError('Monto o porcentaje inválido.') from error
    if not n.is_finite():
        raise ValueError('No se aceptan NaN o infinito.')
    return n

def calcular_liquidacion(*, total, trabajo, porcentaje, decision, origen,
                         cargo_solicitado, aceptacion_previa, excepcion_legal=False):
    """Calcula topes y distribución final sin persistir ni transferir fondos."""

    total, trabajo, porcentaje, cargo_solicitado = [numero(x) for x in
        (total, trabajo, porcentaje, cargo_solicitado)]
    if any(x < 0 for x in (total, trabajo, porcentaje, cargo_solicitado)) or porcentaje > 100:
        raise ValueError('Los montos y el porcentaje deben ser positivos.')
    if total <= 0 or trabajo > total:
        raise ValueError('No existe saldo positivo o el trabajo supera el total.')
    if any(x.as_tuple().exponent < -2 for x in (total,trabajo,cargo_solicitado)):
        raise ValueError('Los montos no pueden tener más de dos decimales.')
    if decision not in ('JUSTIFICADA','INJUSTIFICADA','INCUMPLIMIENTO_CONTRAPARTE'):
        raise ValueError('La solicitud debe tener una evaluación favorable a cancelar.')
    saldo = (total-trabajo).quantize(CENTAVO)
    tope = Decimal('0')
    if origen == 'ORGANIZACION' and decision == 'INJUSTIFICADA' and aceptacion_previa and not excepcion_legal:
        tope = (saldo*porcentaje/100).quantize(PESO, rounding=ROUND_HALF_UP)
    if cargo_solicitado > tope:
        raise ValueError('Cargo superior al máximo autorizado; revise aceptación, justificación y derechos aplicables.')
    devolucion = (saldo-cargo_solicitado).quantize(CENTAVO)
    if devolucion < 0:
        raise ValueError('La devolución no puede ser negativa.')
    return {'monto_total':total, 'trabajo_acreditado':trabajo,
            'saldo':saldo,'porcentaje_contratado':porcentaje if aceptacion_previa else Decimal('0'),
            'cargo_maximo':tope,'cargo_autorizado':cargo_solicitado,
            'devolucion_autorizada':devolucion}
