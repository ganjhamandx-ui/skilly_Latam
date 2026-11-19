"""Cálculo puro, sin retiros ni devolución de fondos.

El cargo real está deliberadamente bloqueado hasta incorporar aceptación versionada
anterior al pago y controles de retracto. No usar el cálculo teórico como cobro.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def proyectar_liquidacion(*, monto_total, monto_trabajo, porcentaje,
                          origen, decision, aceptacion_previa_valida=False):
    """Proyecta trabajo, cargo y devolución sin ejecutar movimientos de dinero."""

    try:
        total = Decimal(str(monto_total))
        trabajo = Decimal(str(monto_trabajo))
        pct = Decimal(str(porcentaje))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('Los valores económicos deben ser números válidos.') from exc
    if not all(v.is_finite() for v in (total, trabajo, pct)):
        raise ValueError('No se admiten valores infinitos o NaN.')
    if total < 0 or trabajo < 0 or trabajo > total or not 0 <= pct <= 100:
        raise ValueError('Montos o porcentaje fuera de rango.')
    if decision == 'RECHAZAR_SOLICITUD':
        return {'cargo_teorico': Decimal('0'), 'cargo_ejecutado': Decimal('0'),
                'devolucion_propuesta': None}
    saldo = total - trabajo
    teorico = Decimal('0')
    if origen == 'ORGANIZACION' and decision == 'INJUSTIFICADA':
        teorico = (saldo * pct / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    # Aun no existe consentimiento versionado previo al pago:
    # nunca ejecutar cobros por penalizacion en esta fase.
    cargo = Decimal('0')
    return {'cargo_teorico': teorico, 'cargo_ejecutado': cargo,
            'devolucion_propuesta': saldo}
