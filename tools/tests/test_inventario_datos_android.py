"""Inventario: lista blanca y grafo sintetico, sin PostgreSQL ni datos reales."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('_android_inventory', TOOLS / 'inventario_datos_android.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class InventoryTests(unittest.TestCase):
    def test_fixture_copies_only_explicit_integer_ids_not_secrets_or_unknown_fields(self):
        value = {'professional_id': 22, 'service_id': 11, 'email': 'private-canary',
                 'password': 'private-canary', 'control': 'private-canary', 'reference': 'private-canary',
                 'unknown_id': 99, 'cierre': {'request_id': 23, 'reference': 'private-canary'}}
        result = TOOL.fixture_anchors(value)
        self.assertEqual(result, [('profesional', 22, 'professional_id'), ('servicio', 11, 'service_id'),
                                  ('solicitud_servicio', 23, 'cierre.request_id')])
        self.assertNotIn('private-canary', json.dumps(result))

    def test_auxiliary_account_ids_are_explicit_and_professional_is_distinct(self):
        self.assertEqual(TOOL.fixture_anchors({'admin': {'id': 37, 'password': 'private-canary'},
            'professional_ui': {'id': 38, 'professional_id': 21}}, auxiliary=True),
            [('usuario', 37, 'admin.id'), ('usuario', 38, 'professional_ui.id'),
             ('profesional', 21, 'professional_ui.professional_id')])

    def test_rejects_bool_string_negative_and_real_service_anchors(self):
        for value in (True, '22', 0, -1, 2**63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TOOL.fixture_anchors({'professional_id': value})
        for value in (1, 2):
            with self.assertRaises(ValueError):
                TOOL.fixture_anchors({'service_id': value})

    def test_readonly_graph_follows_dependents_and_reports_external_fk_without_expanding_it(self):
        pks = {'usuario': ('id_usuario',), 'profesional': ('id_profesional',),
               'servicio': ('id_servicio',), 'categoria_servicio': ('id_categoria',),
               'revision_servicio': ('id_revision',), 'sin_filas': ('id_vacio',)}
        def fk(name, child, parent, column, parent_column):
            return {'constraint': name, 'child': child, 'parent': parent,
                    'columns': (column,), 'parent_columns': (parent_column,)}
        fks = [fk('prof_user', 'profesional', 'usuario', 'id_usuario', 'id_usuario'),
               fk('service_prof', 'servicio', 'profesional', 'id_profesional', 'id_profesional'),
               fk('service_cat', 'servicio', 'categoria_servicio', 'id_categoria', 'id_categoria'),
               fk('revision_service', 'revision_servicio', 'servicio', 'id_servicio', 'id_servicio'),
               fk('empty_service', 'sin_filas', 'servicio', 'id_servicio', 'id_servicio')]
        data = {'usuario': [{'id_usuario': 39}],
                'profesional': [{'id_profesional': 22, 'id_usuario': 39}],
                'servicio': [{'id_servicio': 11, 'id_profesional': 22, 'id_categoria': 1}],
                'revision_servicio': [{'id_revision': 7, 'id_servicio': 11}], 'sin_filas': []}
        queried = []
        def select(_connection, table, columns, filters, keys):
            queried.append(table)
            return [tuple(row[column] for column in columns) for row in data[table]
                    if tuple(row[column] for column in filters) in keys]
        with patch.object(TOOL, 'catalog', return_value=(pks, fks)), patch.object(TOOL, 'select_keys', side_effect=select):
            result = TOOL.build_inventory(object(), [{'table': 'profesional', 'id': 22}])
        self.assertEqual({item['table'] for item in result}, {'profesional', 'usuario', 'servicio', 'revision_servicio'})
        self.assertNotIn('categoria_servicio', queried)
        service = next(item for item in result if item['table'] == 'servicio')
        external = next(fk for fk in service['rows'][0]['foreign_keys'] if fk['to_table'] == 'categoria_servicio')
        self.assertEqual(external['values'], [1])
        self.assertFalse(external['target_in_inventory'])

    def test_missing_fixture_key_is_recorded_without_exporting_a_row(self):
        with patch.object(TOOL, 'catalog', return_value=({'entrega': ('id_entrega',)}, [])), \
                patch.object(TOOL, 'select_keys', return_value=[]):
            result = TOOL.build_inventory(object(), [{'table': 'entrega', 'id': 999}])
        self.assertEqual(result[0]['rows'], [])
        self.assertEqual(result[0]['missing_fixture_keys'], [[999]])

    def test_load_requires_result_bound_to_same_run_and_ignores_in_progress_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            name = 'android_aislado_' + 'a' * 20
            (run / 'fixture_privado.json').write_text(json.dumps({'run_id': name, 'admin': {'id': 37}}))
            output = run / ('browser_e2e_' + 'b' * 32)
            output.mkdir()
            (output / 'fixture_privado.json').write_text(json.dumps({'service_id': 11}))
            ctx = {'run_id': name, 'run_dir': str(run)}
            self.assertEqual(len(TOOL.load_anchors(ctx)), 1)
            (output / 'resultado.json').write_text(json.dumps({'run_id': 'other', 'isolated': True}))
            with self.assertRaises(ValueError):
                TOOL.load_anchors(ctx)

    def test_database_marker_uses_shared_catalog_comment_before_inventory(self):
        # PostgreSQL databases are shared objects: an ordinary obj_description
        # lookup does not establish ownership of this isolated database.
        shared_query = "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            ctx = {'run_id': 'android_aislado_' + 'a' * 20, 'database_name': 'skilly_android_' + 'a' * 20,
                   'database_port': 57647, 'cluster': str(run / 'cluster'), 'run_dir': str(run)}
            admin = MagicMock()
            admin.__enter__.return_value = admin
            admin.execute.return_value.fetchone.return_value = (ctx['cluster'],)
            connection = MagicMock()
            connection.__enter__.return_value = connection
            queries = []
            def execute(query):
                queries.append(query)
                if query == 'SELECT current_database(),current_schema(),current_user,inet_server_port()':
                    value = (ctx['database_name'], 'skilly', 'skilly_app', 57647)
                elif query == shared_query:
                    value = ('skilly_android:' + ctx['run_id'],)
                elif query == 'SHOW transaction_read_only':
                    value = ('on',)
                else:
                    raise AssertionError('Unexpected inventory query')
                cursor = MagicMock()
                cursor.fetchone.return_value = value
                return cursor
            connection.execute.side_effect = execute
            with patch.object(TOOL, 'load_anchors', return_value=[{'table': 'servicio', 'id': 11}]), \
                    patch.object(TOOL.runtime, 'admin_connection', return_value=admin), \
                    patch.object(TOOL.runtime, 'environment', return_value={
                        'POSTGRES_USER': 'skilly_app', 'POSTGRES_PASSWORD': 'synthetic-test-only'}), \
                    patch('psycopg.connect', return_value=connection), \
                    patch.object(TOOL, 'build_inventory', return_value=[]) as build, redirect_stdout(io.StringIO()):
                TOOL.inventory(ctx)
            self.assertIn(shared_query, queries)
            self.assertFalse(any('SELECT obj_description(' in query for query in queries))
            self.assertTrue(connection.read_only)
            build.assert_called_once()


if __name__ == '__main__':
    unittest.main()
