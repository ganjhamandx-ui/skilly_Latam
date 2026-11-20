"""Orientaciones de gestión E3 para incidencias empresariales de prestaciones.

Estas orientaciones NO ejecutan sanciones, cambios de agenda ni operaciones
monetarias. Los cambios operativos siguen sus endpoints originales.
"""

# Motivos visibles en el formulario. Evita codificar causas distintas en una
# categoría genérica y conserva compatibilidad con reclamos históricos libres.
MOTIVOS = (
    "Inasistencia del profesional a la reunión",
    "Cancelación solicitada por la organización",
    "Cancelación solicitada por el profesional",
    "Solicitud de reprogramación de la reunión",
    "Abandono o interrupción del servicio",
    "Incumplimiento de entregables o condiciones",
    "Otro incidente de la prestación",
)

_ORIENTACIONES = {
    MOTIVOS[0]: (
        "Comprobar fecha y hora acordadas; solicitar antecedentes a ambas "
        "partes y evaluar un nuevo bloque con coordinación."
    ),
    MOTIVOS[1]: (
        "Revisar condiciones aceptadas, avance y plazo del aviso; la "
        "administración tramita cancelación y eventual reversa por separado."
    ),
    MOTIVOS[2]: (
        "Comprobar el aviso y motivo del profesional; contactar a la "
        "organización y evaluar reagendamiento o cancelación administrativa."
    ),
    MOTIVOS[3]: (
        "Contactar a las partes y confirmar nuevo bloque disponible; "
        "reagendar únicamente desde la gestión de agenda autorizada."
    ),
    MOTIVOS[4]: (
        "Revisar avances, entregas y comunicaciones; solicitar descargos "
        "y evaluar incumplimiento antes de resolver el reclamo."
    ),
    MOTIVOS[5]: (
        "Contrastar los entregables y condiciones originales; evaluar "
        "correcciones, reclamo y eventual efecto económico."
    ),
    MOTIVOS[6]: (
        "Recopilar antecedentes y clasificar la situación antes de "
        "adoptar una medida administrativa."
    ),
}


def orientacion_reclamo(motivo):
    """Proporciona recomendaciones sin ejecutar operaciones de negocio.

    Args:
        motivo (str): Motivo registrado del reclamo; puede ser un texto anterior
            o libre que no figure en el catálogo vigente.

    Returns:
        dict: Tipo, acción recomendada y precaución común. Los motivos ajenos
        al catálogo reciben una orientación general de revisión.
    """
    return {
        "tipo": motivo if motivo in _ORIENTACIONES else "Motivo anterior o libre",
        "accion_recomendada": _ORIENTACIONES.get(
            motivo,
            "Verificar antecedentes y resolver de acuerdo con el tipo de incidente."
        ),
        "precaucion": (
            "El reclamo no cancela reuniones ni prestaciones, no suspende "
            "usuarios y no libera o devuelve dinero automáticamente. "
            "Utilizar los flujos administrativos existentes y registrar decisiones."
        ),
    }
