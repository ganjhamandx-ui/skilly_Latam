"""Servicio de instrucciones bancarias por pago — ENSAYO AISLADO.

NO se conecta a urls.py ni a pagos existentes.
Solo opera con alias previamente configurado que apunta a skilly_test_concurrencia.
NO expone los datos de otras cuentas a organizaciones; el acceso HTTP y la
comprobación de titularidad del pago deben agregarse antes de producción.
"""
from django.db import connections, transaction, IntegrityError

BASE_AUTORIZADA = 'skilly_test_concurrencia'
CAMPOS_SNAPSHOT = (
    'titular_fijado', 'rut_titular_fijado', 'banco_fijado',
    'tipo_cuenta_fijado', 'numero_cuenta_fijado', 'correo_fijado',
)

class ErrorInstruccionBancaria(Exception):
    pass


def _verificar_alias(alias):
    if not isinstance(alias, str) or not alias or alias == 'default':
        raise ErrorInstruccionBancaria('Se exige un alias aislado explícito.')
    if alias not in connections.databases:
        raise ErrorInstruccionBancaria('Alias de pruebas no configurado.')
    with connections[alias].cursor() as cursor:
        cursor.execute('SELECT current_database(), current_schema(), current_user')
        actual = cursor.fetchone()
    if actual != (BASE_AUTORIZADA, 'public', 'skilly_app'):
        raise ErrorInstruccionBancaria('Conexión no autorizada para ensayo: operación bloqueada.')


def _serializar(fila):
    return {
        'id_instruccion': fila[0], 'id_pago': fila[1],
        'titular': fila[2], 'rut_titular': fila[3], 'banco': fila[4],
        'tipo_cuenta': fila[5], 'numero_cuenta': fila[6], 'correo': fila[7],
        'fecha_emision': fila[8].isoformat() if fila[8] else None,
    }


SELECT_INSTRUCCION = '''
SELECT id_instruccion, id_pago, titular_fijado, rut_titular_fijado,
       banco_fijado, tipo_cuenta_fijado, numero_cuenta_fijado,
       correo_fijado, fecha_emision
FROM public.instruccion_transferencia_skilly WHERE id_pago = %s
'''


def consultar_instruccion_aislada(*, alias, id_pago):
    """Solo consulta. NO verifica titularidad de cliente; uso INTERNO de ensayo."""
    _verificar_alias(alias)
    if type(id_pago) is not int or id_pago <= 0:
        raise ErrorInstruccionBancaria('ID de pago inválido.')
    with connections[alias].cursor() as cursor:
        cursor.execute(SELECT_INSTRUCCION, [id_pago])
        fila = cursor.fetchone()
    return _serializar(fila) if fila else None


def emitir_instruccion_aislada(*, alias, id_pago):
    """Emite instrucción inmutable e idempotente usando principal ACTIVA.

    La primera emisión congela la cuenta; siguientes consultas o emisiones
    devuelven la misma instrucción. No crea ni modifica un registro de Pago.
    Id_pago es FICTICIO en este esquema aislado y no tiene FK a pago real.
    """
    _verificar_alias(alias)
    if type(id_pago) is not int or id_pago <= 0:
        raise ErrorInstruccionBancaria('ID de pago inválido.')
    try:
        with transaction.atomic(using=alias):
            with connections[alias].cursor() as cursor:
                # Serializa la emisión y cambios de principal de ensayo.
                cursor.execute('LOCK TABLE public.cuenta_bancaria_skilly IN SHARE ROW EXCLUSIVE MODE')
                cursor.execute(SELECT_INSTRUCCION, [id_pago])
                existente = cursor.fetchone()
                if existente:
                    return _serializar(existente)
                cursor.execute('''
                    SELECT id_cuenta FROM public.cuenta_bancaria_skilly
                    WHERE principal IS TRUE AND activa IS TRUE
                    FOR UPDATE
                ''')
                principal = cursor.fetchone()
                if not principal:
                    raise ErrorInstruccionBancaria('No existe una cuenta principal activa.')
                cursor.execute('''
                    INSERT INTO public.instruccion_transferencia_skilly
                    (id_pago, id_cuenta, titular_fijado, rut_titular_fijado,
                     banco_fijado, tipo_cuenta_fijado, numero_cuenta_fijado, correo_fijado)
                    SELECT %s, id_cuenta, titular, rut_titular, banco,
                           tipo_cuenta, numero_cuenta, correo
                    FROM public.cuenta_bancaria_skilly WHERE id_cuenta = %s
                    RETURNING id_instruccion, id_pago, titular_fijado,
                              rut_titular_fijado, banco_fijado, tipo_cuenta_fijado,
                              numero_cuenta_fijado, correo_fijado, fecha_emision
                ''', [id_pago, principal[0]])
                return _serializar(cursor.fetchone())
    except IntegrityError as exc:
        raise ErrorInstruccionBancaria('Conflicto de integridad al emitir instrucciones.') from exc
