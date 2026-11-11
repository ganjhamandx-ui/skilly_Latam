"""Inventario privado de IDs/FK del ensayo Android; no modifica PostgreSQL.

No representa un delta inicial/final ni autoriza borrar filas individuales.
Solo identifica anclas de fixtures y filas relacionadas mediante claves enteras.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

import entorno_android_skilly as runtime

STAGE = 'arguments'
MAX_ROWS = 10000
ROOT_FIELDS = {
    'professional_id': 'profesional', 'document_id': 'documento_profesional',
    'corrected_document_id': 'documento_profesional', 'validation_id': 'solicitud_validacion',
    'interview_block_id': 'bloque_entrevista_validacion', 'interview_id': 'entrevista_validacion',
    'service_id': 'servicio',
}
CYCLE_FIELDS = {
    'availability_id': 'disponibilidad', 'alternative_id': 'disponibilidad',
    'request_id': 'solicitud_servicio', 'engagement_id': 'prestacion_servicio',
    'payment_id': 'pago', 'reschedule_id': 'solicitud_reagendamiento',
    'first_delivery_id': 'entrega', 'corrected_delivery_id': 'entrega',
    'claim_id': 'reclamo_prestacion', 'case_id': 'expediente_cancelacion_e3',
    'reversal_id': 'reversa_pago', 'feedback_id': 'retroalimentacion',
}


def require(value):
    if not value:
        raise ValueError('Inventario Android no validado')


def integer_id(value):
    require(type(value) is int and 0 < value < 2**63)
    return value


def fixture_anchors(data, *, auxiliary=False):
    """Lista blanca: nunca copia correo, clave, token, referencia ni texto."""
    require(isinstance(data, dict))
    found = []
    if auxiliary:
        for actor in ('admin', 'professional_ui'):
            values = data.get(actor, {})
            require(isinstance(values, dict))
            if values.get('id') is not None:
                found.append(('usuario', integer_id(values['id']), actor + '.id'))
        values = data.get('professional_ui', {})
        if values.get('professional_id') is not None:
            found.append(('profesional', integer_id(values['professional_id']), 'professional_ui.professional_id'))
    else:
        for field, table in ROOT_FIELDS.items():
            if data.get(field) is not None:
                found.append((table, integer_id(data[field]), field))
        for cycle in ('cierre', 'cancelacion'):
            values = data.get(cycle, {})
            require(isinstance(values, dict))
            for field, table in CYCLE_FIELDS.items():
                if values.get(field) is not None:
                    found.append((table, integer_id(values[field]), cycle + '.' + field))
    require(not any(table == 'servicio' and value in (1, 2) for table, value, _ in found))
    return found


def load_anchors(ctx):
    run = Path(ctx['run_dir']).resolve(strict=True)
    auxiliary = run / 'fixture_privado.json'
    data = runtime.read_json(auxiliary)
    require(data.get('run_id') == ctx['run_id'])
    anchors = [{'table': table, 'id': value, 'field': field, 'fixture': auxiliary.name}
               for table, value, field in fixture_anchors(data, auxiliary=True)]
    for directory in sorted(run.glob('browser_e2e_*')):
        require(not directory.is_symlink() and re.fullmatch(r'browser_e2e_[a-f0-9]{32}', directory.name))
        require(directory.resolve().parent == run)
        fixture, result = directory / 'fixture_privado.json', directory / 'resultado.json'
        # Un proceso todavia activo puede no haber escrito su resultado final.
        if not fixture.is_file() or not result.is_file():
            continue
        require(not fixture.is_symlink() and not result.is_symlink())
        report = runtime.read_json(result)
        require(report.get('isolated') is True and report.get('run_id') == ctx['run_id'])
        for table, value, field in fixture_anchors(runtime.read_json(fixture)):
            anchors.append({'table': table, 'id': value, 'field': field,
                            'fixture': fixture.relative_to(run).as_posix()})
    require(bool(anchors))
    return anchors


def catalog(connection):
    primary = connection.execute("""
        SELECT t.relname, array_agg(a.attname ORDER BY k.ord)
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY k(num,ord)
        JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.num
        WHERE c.contype='p' AND n.nspname='skilly'
        GROUP BY t.relname HAVING bool_and(a.atttypid IN (20,21,23))
        ORDER BY t.relname
    """).fetchall()
    foreign = connection.execute("""
        SELECT c.conname, child.relname, parent.relname,
               array_agg(ca.attname ORDER BY k.ord), array_agg(pa.attname ORDER BY k.ord)
        FROM pg_constraint c JOIN pg_class child ON child.oid=c.conrelid
        JOIN pg_class parent ON parent.oid=c.confrelid
        JOIN pg_namespace cn ON cn.oid=child.relnamespace
        JOIN pg_namespace pn ON pn.oid=parent.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey,c.confkey) WITH ORDINALITY k(cnum,pnum,ord)
        JOIN pg_attribute ca ON ca.attrelid=child.oid AND ca.attnum=k.cnum
        JOIN pg_attribute pa ON pa.attrelid=parent.oid AND pa.attnum=k.pnum
        WHERE c.contype='f' AND cn.nspname='skilly' AND pn.nspname='skilly'
        GROUP BY c.conname,child.relname,parent.relname
        HAVING bool_and(ca.atttypid IN (20,21,23) AND pa.atttypid IN (20,21,23))
        ORDER BY child.relname,c.conname
    """).fetchall()
    pks = {table: tuple(columns) for table, columns in primary}
    fks = [{'constraint': name, 'child': child, 'parent': parent,
            'columns': tuple(columns), 'parent_columns': tuple(parent_columns)}
           for name, child, parent, columns, parent_columns in foreign]
    return pks, fks


def select_keys(connection, table, columns, filter_columns, keys):
    from psycopg import sql
    require(bool(keys) and len(keys) <= MAX_ROWS)
    require(all(len(key) == len(filter_columns) for key in keys))
    require(all(type(value) is int for key in keys for value in key))
    fields = sql.SQL(',').join(map(sql.Identifier, columns))
    predicates = []
    parameters = []
    for key in sorted(keys):
        predicates.append(sql.SQL('(') + sql.SQL(' AND ').join(
            sql.SQL('{}=%s').format(sql.Identifier(column)) for column in filter_columns) + sql.SQL(')'))
        parameters.extend(key)
    query = sql.SQL('SELECT DISTINCT {} FROM {}.{} WHERE {} LIMIT {}').format(
        fields, sql.Identifier('skilly'), sql.Identifier(table),
        sql.SQL(' OR ').join(predicates), sql.Literal(MAX_ROWS + 1))
    rows = connection.execute(query, parameters).fetchall()
    require(len(rows) <= MAX_ROWS)
    require(all(type(value) is int or value is None for row in rows for value in row))
    return rows


def build_inventory(connection, anchors):
    pks, fks = catalog(connection)
    owned = {}
    for anchor in anchors:
        table = anchor['table']
        require(table in pks and len(pks[table]) == 1)
        owned.setdefault(table, set()).add((anchor['id'],))
    # Captura tambien los IDs de cuenta/empresa/contacto creados por la UI.
    # No expande categorias, configuraciones globales ni otros padres previos.
    parents_allowed = {('profesional', 'usuario'), ('solicitud_servicio', 'empresa_solicitante'),
                       ('solicitud_servicio', 'contacto_empresa')}
    for fk in fks:
        if ((fk['child'], fk['parent']) in parents_allowed and fk['child'] in owned
                and fk['parent_columns'] == pks.get(fk['parent'])):
            rows = select_keys(connection, fk['child'], fk['columns'], pks[fk['child']], owned[fk['child']])
            owned.setdefault(fk['parent'], set()).update(tuple(row) for row in rows if all(v is not None for v in row))
    for _ in range(20):
        changed = False
        for fk in fks:
            if (not owned.get(fk['parent']) or fk['child'] not in pks
                    or fk['parent_columns'] != pks[fk['parent']]):
                continue
            rows = select_keys(connection, fk['child'], pks[fk['child']], fk['columns'], owned[fk['parent']])
            target = owned.setdefault(fk['child'], set())
            before = len(target)
            target.update(tuple(row) for row in rows)
            changed = changed or len(target) != before
            require(sum(map(len, owned.values())) <= MAX_ROWS)
        if not changed:
            break
    else:
        raise ValueError('Relacion de ensayo demasiado amplia')
    require(not owned.get('servicio', set()).intersection({(1,), (2,)}))
    tables = []
    for table, keys in sorted(owned.items()):
        if not keys:
            continue
        outgoing = [fk for fk in fks if fk['child'] == table]
        columns = list(pks[table])
        for fk in outgoing:
            columns.extend(column for column in fk['columns'] if column not in columns)
        rows = select_keys(connection, table, columns, pks[table], keys)
        present = {tuple(row[:len(pks[table])]) for row in rows}
        records = []
        for row in rows:
            values = dict(zip(columns, row))
            relationships = []
            for fk in outgoing:
                foreign_key = tuple(values[column] for column in fk['columns'])
                if any(value is None for value in foreign_key):
                    continue
                relationships.append({'constraint': fk['constraint'], 'to_table': fk['parent'],
                    'to_columns': list(fk['parent_columns']), 'values': list(foreign_key),
                    'target_in_inventory': fk['parent_columns'] == pks.get(fk['parent'])
                                           and foreign_key in owned.get(fk['parent'], set())})
            records.append({'pk': list(row[:len(pks[table])]), 'foreign_keys': relationships})
        tables.append({'table': table, 'primary_key': list(pks[table]), 'rows': records,
                       'missing_fixture_keys': [list(key) for key in sorted(keys - present)]})
    return tables


def inventory(ctx):
    global STAGE
    import psycopg
    from psycopg import IsolationLevel
    STAGE = 'fixtures'
    anchors = load_anchors(ctx)
    STAGE = 'cluster_identity'
    with runtime.admin_connection(ctx) as admin:
        admin.read_only = True
        require(Path(admin.execute('SHOW data_directory').fetchone()[0]).resolve() == Path(ctx['cluster']).resolve())
    config = runtime.environment(ctx)
    STAGE = 'database_identity'
    with psycopg.connect(dbname=ctx['database_name'], user=config['POSTGRES_USER'],
            password=config['POSTGRES_PASSWORD'], host=runtime.HOST, port=ctx['database_port'],
            options='-c search_path=skilly,public -c default_transaction_read_only=on', connect_timeout=8) as connection:
        connection.read_only = True
        connection.isolation_level = IsolationLevel.REPEATABLE_READ
        require(connection.execute('SELECT current_database(),current_schema(),current_user,inet_server_port()').fetchone()
                == (ctx['database_name'], 'skilly', 'skilly_app', runtime.DATABASE_PORT))
        # Las bases pertenecen al catalogo compartido; sus comentarios se
        # consultan en pg_shdescription, no en pg_description.
        require(connection.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()").fetchone()
                == ('skilly_android:' + ctx['run_id'],))
        require(connection.execute('SHOW transaction_read_only').fetchone() == ('on',))
        STAGE = 'inventory_read_only'
        tables = build_inventory(connection, anchors)
    report = {'completed': True, 'run_id': ctx['run_id'], 'database': ctx['database_name'],
        'read_only': True, 'data_modified': False, 'anchors': anchors, 'tables': tables,
        'is_initial_final_delta': False, 'individual_row_deletion_authorized': False,
        'scope': 'fixture integer IDs and related integer PK/FK rows; relationships can include preexisting records',
        'attachments_inventoried': False, 'business_values_exported': False}
    output = Path(ctx['run_dir']) / ('inventario_datos_android_' + uuid4().hex + '.json')
    payload = json.dumps(report, indent=2).encode('utf-8')
    with output.open('xb') as stream:
        stream.write(payload)
    print(json.dumps({'completed': True, 'report': str(output), 'sha256': hashlib.sha256(payload).hexdigest(),
                      'tables': len(tables), 'rows': sum(len(table['rows']) for table in tables), 'read_only': True}))


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Argumentos de inventario no validos')


if __name__ == '__main__':
    try:
        parser = PrivateParser(description=__doc__)
        parser.add_argument('--contexto', required=True)
        args = parser.parse_args()
        inventory(runtime.context_from(args.contexto))
    except Exception:
        print(json.dumps({'completed': False, 'stage': STAGE, 'error_type': 'AndroidInventoryRejected'}))
        raise SystemExit(1) from None
