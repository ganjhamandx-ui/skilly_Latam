"""Texto informativo y versión determinista de la política; sin Django ni BD."""
import hashlib
from decimal import Decimal, InvalidOperation


def porcentaje_valido(valor):
    """Convierte el porcentaje a Decimal finito entre 0 y 100 con cuatro decimales.

    Args:
        valor: Valor convertible a Decimal mediante su representación textual.

    Returns:
        Decimal: Porcentaje cuantizado con el contexto decimal vigente.

    Raises:
        ValueError: Si no puede convertirse, no es finito o está fuera de rango.
        InvalidOperation: Si el contexto decimal impide cuantizar el resultado.

    Example:
        >>> porcentaje_valido('12.5')
        Decimal('12.5000')
    """

    try:
        pct = Decimal(str(valor))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError('Porcentaje inválido') from exc
    if not pct.is_finite() or pct < 0 or pct > 100:
        raise ValueError('Porcentaje fuera de rango')
    return pct.quantize(Decimal('0.0001'))

def texto_versionado(pct):
    """Genera el texto contractual estable asociado al porcentaje vigente.

    Args:
        pct: Porcentaje que se normaliza mediante porcentaje_valido.

    Returns:
        str: Política informativa con porcentaje sin ceros decimales innecesarios.

    Raises:
        ValueError: Si el porcentaje no es válido.
        InvalidOperation: Si no puede cuantizarse con el contexto decimal actual.
    """

    valor = porcentaje_valido(pct)
    legible = format(valor.normalize(), 'f')
    return (
        f'Si cancelas sin justificación válida, podría aplicarse un cargo de hasta {legible}% '
        'sobre la parte del servicio que aún no se haya realizado, siempre que corresponda legalmente. '
        'SKILLY revisará tu solicitud antes de decidir; no hay descuentos automáticos. '
        'No se aplicará un cargo por una causa justificada, incumplimiento de la otra parte '
        'o derecho a devolución íntegra, incluido el retracto cuando corresponda. '
        'Te informaremos los motivos y montos de la decisión. '
        'Los cambios futuros no se aplican retroactivamente.'
    )

def firma_politica(texto):
    """Calcula la huella SHA-256 que identifica exactamente el texto aceptado.

    Args:
        texto (str): Política completa codificada como UTF-8, sin normalizarla.

    Returns:
        str: Huella hexadecimal de 64 caracteres; identifica cambios de contenido,
        pero no constituye una firma autenticada con una clave secreta.
    """

    return hashlib.sha256(texto.encode('utf-8')).hexdigest()
