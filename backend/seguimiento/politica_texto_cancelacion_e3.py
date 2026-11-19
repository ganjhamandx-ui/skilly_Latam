"""Texto informativo y versión determinista de la política; sin Django ni BD."""
import hashlib
from decimal import Decimal, InvalidOperation


def porcentaje_valido(valor):
    """Normaliza el porcentaje configurable y exige el rango permitido."""

    try:
        pct = Decimal(str(valor))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError('Porcentaje inválido') from exc
    if not pct.is_finite() or pct < 0 or pct > 100:
        raise ValueError('Porcentaje fuera de rango')
    return pct.quantize(Decimal('0.0001'))

def texto_versionado(pct):
    """Genera el texto contractual estable asociado al porcentaje vigente."""

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
    """Calcula la huella SHA-256 que identifica el texto aceptado."""

    return hashlib.sha256(texto.encode('utf-8')).hexdigest()
