"""Ensayo BD con datos ficticios y ROLLBACK obligatorio; ejecutar con manage.py shell."""
from copy import deepcopy
from django.db import connections, transaction

NOMBRE = 'skilly_test_concurrencia'
ALIAS = 'bancos_prueba_temporal'
config = deepcopy(connections.databases['default'])
config['NAME'] = NOMBRE
config['OPTIONS'] = dict(config.get('OPTIONS') or {})
config['OPTIONS']['options'] = '-c search_path=public'
connections.databases[ALIAS] = config

try:
    c = connections[ALIAS]
    with c.cursor() as cur:
        cur.execute('SELECT current_database(), current_user, current_schema()')
        base, usuario, esquema = cur.fetchone()
        if (base, usuario, esquema) != (NOMBRE, 'skilly_app', 'public'):
            raise RuntimeError(f'CONEXION BLOQUEADA: {(base, usuario, esquema)!r}')
        cur.execute('''SELECT count(*) FROM public.cuenta_bancaria_skilly''')
        n1 = cur.fetchone()[0]
        cur.execute('''SELECT count(*) FROM public.cuenta_bancaria_skilly_historial''')
        n2 = cur.fetchone()[0]
        if (n1, n2) != (0, 0):
            raise RuntimeError(f'La BD de ensayo contiene datos ({n1} cuentas, {n2} cambios). No tocar.')
    print('AISLAMIENTO CONFIRMADO:', base, usuario, esquema)
    print('REGISTROS INICIALES: cuentas=0, historial=0')
    try:
        with transaction.atomic(using=ALIAS):
            with c.cursor() as cur:
                def registrar(accion, cuenta, antes, despues):
                    cur.execute('''INSERT INTO public.cuenta_bancaria_skilly_historial
                      (id_cuenta, accion, datos_anteriores, datos_nuevos, id_usuario_skilly)
                      VALUES (%s,%s,%s::jsonb,%s::jsonb,%s)''',
                      [cuenta, accion, antes, despues, 9001])
                import json
                ids=[]
                for numero in ('0000012345', '0000054321'):
                    cur.execute('''INSERT INTO public.cuenta_bancaria_skilly
                      (titular,rut_titular,banco,tipo_cuenta,numero_cuenta,correo,
                       activa,principal,id_usuario_creacion,id_usuario_modificacion)
                      VALUES (%s,%s,%s,%s,%s,%s,FALSE,FALSE,9001,9001)
                      RETURNING id_cuenta''',
                      ['SKILLY DEMOSTRACION SPA','12345678-5','BANCO FICTICIO',
                       'CORRIENTE',numero,'pagos@example.invalid'])
                    ident=cur.fetchone()[0]; ids.append(ident)
                    registrar('CREAR',ident,None,json.dumps({'numero_cuenta':numero,'activa':False,'principal':False}))
                for ident in ids:
                    cur.execute('UPDATE public.cuenta_bancaria_skilly SET activa=TRUE WHERE id_cuenta=%s',[ident])
                    registrar('ACTIVAR',ident,json.dumps({'activa':False}),json.dumps({'activa':True}))
                cur.execute('UPDATE public.cuenta_bancaria_skilly SET principal=TRUE WHERE id_cuenta=%s',[ids[0]])
                registrar('PRINCIPAL',ids[0],json.dumps({'principal':False}),json.dumps({'principal':True}))
                cur.execute('UPDATE public.cuenta_bancaria_skilly SET principal=FALSE WHERE id_cuenta=%s',[ids[0]])
                registrar('PRINCIPAL',ids[0],json.dumps({'principal':True}),json.dumps({'principal':False}))
                cur.execute('UPDATE public.cuenta_bancaria_skilly SET principal=TRUE WHERE id_cuenta=%s',[ids[1]])
                registrar('PRINCIPAL',ids[1],json.dumps({'principal':False}),json.dumps({'principal':True}))
                cur.execute('SELECT count(*),count(*) FILTER (WHERE principal) FROM public.cuenta_bancaria_skilly')
                cuentas, principales = cur.fetchone()
                cur.execute('SELECT count(*) FROM public.cuenta_bancaria_skilly_historial')
                cambios=cur.fetchone()[0]
                print('DURANTE ENSAYO:', f'{cuentas} cuentas; {principales} principal; {cambios} eventos')
                assert (cuentas,principales,cambios)==(2,1,7), 'Integridad del ensayo incorrecta'
                # Probar restriccion de principal duplicada dentro de savepoint.
                try:
                    with transaction.atomic(using=ALIAS):
                        cur.execute('UPDATE public.cuenta_bancaria_skilly SET principal=TRUE WHERE id_cuenta=%s',[ids[0]])
                except Exception as ex:
                    print('SEGUNDA PRINCIPAL: rechazada por PostgreSQL ('+type(ex).__name__+')')
                else:
                    raise AssertionError('ERROR: permitió dos cuentas principales')
            transaction.set_rollback(True, using=ALIAS)
        with c.cursor() as cur:
            cur.execute('SELECT count(*) FROM public.cuenta_bancaria_skilly')
            final1=cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM public.cuenta_bancaria_skilly_historial')
            final2=cur.fetchone()[0]
        assert (final1,final2)==(0,0), 'ERROR: los datos ficticios permanecen'
        print('RESULTADO: APROBADO - PERSISTENCIA, PRINCIPAL UNICA, TRAZABILIDAD')
        print('ROLLBACK: CONFIRMADO - CUENTAS 0, HISTORIAL 0')
        print('BASE PRINCIPAL: NO UTILIZADA PARA ESCRITURAS')
    except Exception:
        print('PRUEBA NO APROBADA. Revisar error antes de avanzar.')
        raise
finally:
    connections[ALIAS].close()
