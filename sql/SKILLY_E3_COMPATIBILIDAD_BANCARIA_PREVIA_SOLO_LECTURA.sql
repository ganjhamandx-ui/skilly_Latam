-- SKILLY E3: compatibilidad previa de cuentas bancarias (SOLO LECTURA)
-- Abrir en pgAdmin conectado a la base principal 'skilly'.
-- Este archivo contiene UNA consulta SELECT. No crea ni modifica objetos.
WITH columnas AS (
 SELECT
  count(*) FILTER (WHERE table_name='pago' AND column_name='id_pago' AND data_type='bigint') AS pago_id_bigint,
  count(*) FILTER (WHERE table_name='usuario' AND column_name='id_usuario' AND data_type='bigint') AS usuario_id_bigint
 FROM information_schema.columns
 WHERE table_schema='skilly'
   AND ((table_name='pago' AND column_name='id_pago')
     OR (table_name='usuario' AND column_name='id_usuario'))
), claves AS (
 SELECT
  EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attname='id_pago'
    WHERE c.conrelid=to_regclass('skilly.pago')
      AND c.contype IN ('p','u') AND a.attnum=ANY(c.conkey)
  ) AS pago_id_clave,
  EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attname='id_usuario'
    WHERE c.conrelid=to_regclass('skilly.usuario')
      AND c.contype IN ('p','u') AND a.attnum=ANY(c.conkey)
  ) AS usuario_id_clave
)
SELECT
 current_database() AS base_actual,
 current_database()='skilly' AS base_esperada,
 to_regclass('skilly.pago') IS NOT NULL AS tabla_pago,
 to_regclass('skilly.usuario') IS NOT NULL AS tabla_usuario,
 columnas.pago_id_bigint=1 AS pago_id_tipo_correcto,
 columnas.usuario_id_bigint=1 AS usuario_id_tipo_correcto,
 claves.pago_id_clave,
 claves.usuario_id_clave,
 to_regclass('skilly.cuenta_bancaria_skilly') IS NOT NULL AS cuenta_ya_existe,
 to_regclass('skilly.cuenta_bancaria_skilly_historial') IS NOT NULL AS historial_ya_existe,
 to_regclass('skilly.instruccion_transferencia_skilly') IS NOT NULL AS instrucciones_ya_existen,
 has_schema_privilege('skilly_app','skilly','USAGE') AS app_acceso_esquema,
 CASE WHEN current_database()<>'skilly' THEN 'DETENER: base incorrecta'
      WHEN NOT (columnas.pago_id_bigint=1 AND columnas.usuario_id_bigint=1 AND claves.pago_id_clave AND claves.usuario_id_clave)
      THEN 'REVISAR: claves/tipos no coinciden'
      WHEN (to_regclass('skilly.cuenta_bancaria_skilly') IS NOT NULL OR
            to_regclass('skilly.cuenta_bancaria_skilly_historial') IS NOT NULL OR
            to_regclass('skilly.instruccion_transferencia_skilly') IS NOT NULL)
      THEN 'REVISAR: objeto bancario preexistente'
      ELSE 'COMPATIBILIDAD BASICA OK; AUN FALTA RESPALDO Y REVISION FINAL'
 END AS diagnostico
FROM columnas CROSS JOIN claves;
