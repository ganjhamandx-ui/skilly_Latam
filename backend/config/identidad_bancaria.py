"""Identidad de conexion autorizada para las operaciones bancarias de SKILLY."""
from collections.abc import Mapping


def identidad_bancaria_autorizada(conexion, identidad):
    """La base real debe ser la configurada; esquema y rol siguen restringidos.

    No deduce autorizacion del nombre de una copia ni habilita superusuarios.
    Recibe la identidad ya consultada por el llamador, sin abrir otra conexion.
    """
    configuracion = getattr(conexion, 'settings_dict', None)
    if not isinstance(configuracion, Mapping):
        return False
    nombre = configuracion.get('NAME')
    if (not isinstance(nombre, str) or not nombre.strip()
            or nombre != nombre.strip() or '\x00' in nombre
            or configuracion.get('USER') != 'skilly_app'):
        return False
    return identidad == (nombre, 'skilly', 'skilly_app')
