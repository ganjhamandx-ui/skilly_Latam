"""Política E3 para cerrar una solicitud de reversa en el entorno académico.
No ejecuta transferencias bancarias ni operaciones ante Transbank.
"""
from decimal import Decimal, InvalidOperation

ESTADO_PAGO_SIMULADO = "REVERSA_SIMULADA"
ESTADO_REVERSA_SIMULADA = "SIMULADA"
ESTADO_REVERSA_RECHAZADA = "RECHAZADA"
ACCIONES = {"RECHAZAR_SOLICITUD", "REGISTRAR_DEVOLUCION_SIMULADA"}


class ReversaInvalida(ValueError):
    pass


def plan_cierre(*, accion, estado_pago, estado_verificacion,
                estado_reversa, metodo_pago, monto_total,
                monto_reversa, confirmado=False):
    """Valida el cierre y retorna los estados; es una política pura y comprobable."""
    if accion not in ACCIONES:
        raise ReversaInvalida("Acción de cierre no permitida.")
    if estado_reversa != "SOLICITADA":
        raise ReversaInvalida("Solo se resuelven solicitudes de reversa pendientes.")
    if estado_pago != "RETENIDO" or estado_verificacion != "VERIFICADO":
        raise ReversaInvalida("El pago debe permanecer retenido y verificado.")
    if metodo_pago != "TRANSFERENCIA":
        raise ReversaInvalida("Este cierre académico solo cubre transferencias. Webpay requiere refund del proveedor.")
    if accion == "RECHAZAR_SOLICITUD":
        return (ESTADO_REVERSA_RECHAZADA, estado_pago)
    if confirmado is not True:
        raise ReversaInvalida("Debe reconocer expresamente que es una simulación sin movimiento de fondos.")
    try:
        total = Decimal(str(monto_total))
        monto = total if monto_reversa is None else Decimal(str(monto_reversa))
    except (InvalidOperation, ValueError, TypeError):
        raise ReversaInvalida("Monto de reversa inválido.")
    if not total.is_finite() or not monto.is_finite() or total <= 0 or monto <= 0 or monto > total:
        raise ReversaInvalida("Los montos no permiten el cierre solicitado.")
    if monto != total:
        raise ReversaInvalida("La simulación parcial no está habilitada: requiere conciliación del saldo restante.")
    return (ESTADO_REVERSA_SIMULADA, ESTADO_PAGO_SIMULADO)
