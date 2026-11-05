"""Validador de datos bancarios para la futura API SKILLY (sin operaciones BD)."""
import re
from dataclasses import dataclass

TIPOS_CUENTA = frozenset({'CORRIENTE', 'VISTA', 'CUENTA_RUT', 'AHORRO'})
CAMPOS_REQUERIDOS = ('titular', 'rut_titular', 'banco', 'tipo_cuenta', 'numero_cuenta', 'correo')


class DatosBancariosInvalidos(ValueError):
    pass


def normalizar_rut(rut):
    texto = re.sub(r'[.\s-]', '', str(rut or '')).upper()
    if not re.fullmatch(r'\d{7,8}[0-9K]', texto):
        raise DatosBancariosInvalidos('RUT: formato invalido.')
    cuerpo, digito = texto[:-1], texto[-1]
    suma = sum(int(cifra) * (2 + i % 6) for i, cifra in enumerate(reversed(cuerpo)))
    resultado = 11 - suma % 11
    esperado = '0' if resultado == 11 else 'K' if resultado == 10 else str(resultado)
    if digito != esperado:
        raise DatosBancariosInvalidos('RUT: digito verificador incorrecto.')
    return f'{int(cuerpo)}-{digito}'


def validar_cuenta(datos):
    """Devuelve datos limpios; falla ante ausencias o formatos incorrectos.

    Estas reglas solo comprueban formato, NO titularidad ni existencia bancaria.
    """
    if not isinstance(datos, dict):
        raise DatosBancariosInvalidos('Los datos deben ser un objeto.')
    resultado = {}
    for campo in CAMPOS_REQUERIDOS:
        valor = datos.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise DatosBancariosInvalidos(f'Campo obligatorio: {campo}.')
        resultado[campo] = valor.strip()
    if len(resultado['titular']) > 180 or len(resultado['banco']) > 120:
        raise DatosBancariosInvalidos('Titular o banco excede longitud maxima.')
    resultado['rut_titular'] = normalizar_rut(resultado['rut_titular'])
    resultado['tipo_cuenta'] = resultado['tipo_cuenta'].upper()
    if resultado['tipo_cuenta'] not in TIPOS_CUENTA:
        raise DatosBancariosInvalidos('Tipo de cuenta no admitido.')
    if not re.fullmatch(r'[0-9]{5,32}', resultado['numero_cuenta']):
        raise DatosBancariosInvalidos('Numero de cuenta debe contener 5 a 32 digitos.')
    correo = resultado['correo']
    if len(correo) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', correo):
        raise DatosBancariosInvalidos('Correo invalido.')
    resultado['correo'] = correo.lower()
    # Regla de producto: CuentaRUT solamente con banco seleccionado explícitamente.
    # Reglas por banco y acreditación de titularidad pendientes de catálogos verificados.
    return resultado
