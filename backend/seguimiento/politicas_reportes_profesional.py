"""Política académica: avisos del profesional sobre prestaciones contratadas.

El aviso aporta antecedentes a SKILLY; no modifica reservas, estados,
contratos, penalizaciones, reclamaciones ni movimientos de dinero.
"""

ESTADO_AVISO = 'INCIDENCIA_REPORTADA'  # varchar(30), tabla avance_servicio existente

# Los expedientes de cancelacion conservan otro estado historico. Sus
# antecedentes tambien son internos y no se publican mediante el enlace empresa.
ESTADOS_AVANCE_PRIVADOS = (ESTADO_AVISO, 'INCIDENCIA_PROFESIONAL')

MOTIVOS_PROFESIONAL = {
    'INASISTENCIA_ORGANIZACION': 'La organización no asistió a la reunión',
    'CANCELACION_PROFESIONAL': 'Solicito cancelar la reunión o prestación',
    'REPROGRAMACION_PROFESIONAL': 'Solicito reprogramar la reunión',
    'IMPOSIBILIDAD_EJECUCION': 'Impedimento para continuar el servicio',
    'PROBLEMA_COORDINACION': 'Problema de coordinación con la organización',
    'OTRO': 'Otra incidencia de la prestación',
}


def preparar_aviso(motivo, descripcion):
    """Valida un aviso y produce un texto legible y auditable, sin efectos de negocio.

    Args:
        motivo (str): Clave exacta del catálogo MOTIVOS_PROFESIONAL.
        descripcion (str): Antecedentes de 20 a 2000 caracteres tras quitar
            espacios externos.

    Returns:
        str: Texto con motivo, descripción y aviso de revisión administrativa.

    Raises:
        ValueError: Si el motivo no pertenece al catálogo o la descripción
            tiene un tipo o longitud inválidos.
    """
    if not isinstance(motivo, str) or motivo not in MOTIVOS_PROFESIONAL:
        raise ValueError('Selecciona un motivo de incidencia válido.')
    if not isinstance(descripcion, str):
        raise ValueError('Explica qué ocurrió con la reunión o el servicio.')
    texto = descripcion.strip()
    if len(texto) < 20 or len(texto) > 2000:
        raise ValueError('La descripción debe contener entre 20 y 2000 caracteres.')
    return (
        'INCIDENCIA INFORMADA POR EL PROFESIONAL\n'
        f'Motivo: {MOTIVOS_PROFESIONAL[motivo]}\n'
        f'Descripción: {texto}\n'
        'Estado: pendiente de revisión administrativa. '
        'Este aviso no cancela ni reagenda automáticamente.'
    )
