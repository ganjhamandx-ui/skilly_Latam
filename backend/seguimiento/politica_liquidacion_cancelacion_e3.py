"""Cálculo puro, sin retiros ni devolución de fondos.

Esta proyección mantiene el cargo ejecutado en cero y no evalúa aceptación
versionada ni excepciones legales. La autorización documental se calcula en
politica_liquidacion_final_e3; el cargo teórico de este módulo no constituye cobro.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def proyectar_liquidacion(*, monto_total, monto_trabajo, porcentaje,
                          origen, decision, aceptacion_previa_valida=False):
    """Proyecta la devolución y un cargo teórico sin autorizar cobros.

    Args:
        monto_total (Decimal | str): Total finito y no negativo.
        monto_trabajo (Decimal | str): Trabajo acreditado entre cero y el total.
        porcentaje (Decimal | str): Porcentaje finito entre cero y cien.
        origen (str): Solo ``ORGANIZACION`` habilita el cálculo del cargo teórico.
        decision (str): ``INJUSTIFICADA`` permite ese cálculo; con
            ``RECHAZAR_SOLICITUD`` no se propone devolución.
        aceptacion_previa_valida (bool): Parámetro conservado en el contrato;
            esta proyección no lo utiliza ni permite ejecutar el cargo.

    Returns:
        dict: Cargo teórico redondeado a pesos con ROUND_HALF_UP, cargo ejecutado
        siempre cero y devolución propuesta igual al saldo sin trabajo. Si se
        rechaza la solicitud, ambos cargos son cero y la devolución es ``None``.

    Raises:
        ValueError: Si los importes o el porcentaje no son números finitos
            dentro de sus rangos, o el trabajo supera el total.
    """

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
    # Esta proyección conserva el cargo ejecutado en cero; la autorización
    # con aceptación versionada se evalúa en politica_liquidacion_final_e3.
    cargo = Decimal('0')
    return {'cargo_teorico': teorico, 'cargo_ejecutado': cargo,
            'devolucion_propuesta': saldo}
