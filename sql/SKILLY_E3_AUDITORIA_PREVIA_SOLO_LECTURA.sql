-- SKILLY E3 - AUDITORÍA PREVIA A CUENTAS BANCARIAS
-- SOLO LECTURA. Abrir en pgAdmin Query Tool conectado a BD skilly con usuario autorizado.
-- NO crea tablas, NO modifica datos, NO ejecuta migraciones.
BEGIN TRANSACTION READ ONLY;
DO $$
BEGIN
  IF current_database() <> 'skilly' THEN
    RAISE EXCEPTION 'AUDITORIA CANCELADA: la base conectada es %, se esperaba skilly', current_database();
  END IF;
END $$;

-- A) Identidad de conexión y existencia de tablas base / nuevas.
SELECT current_database() AS base_actual, current_user AS usuario,
       current_schema() AS esquema_predeterminado,
       to_regclass('skilly.pago') IS NOT NULL AS existe_pago,
       to_regclass('skilly.usuario') IS NOT NULL AS existe_usuario,
       to_regclass('skilly.cuenta_bancaria_skilly') IS NOT NULL AS ya_existe_cuenta,
       to_regclass('skilly.cuenta_bancaria_skilly_historial') IS NOT NULL AS ya_existe_historial,
       to_regclass('skilly.instruccion_transferencia_skilly') IS NOT NULL AS ya_existen_instrucciones;

-- B) Columnas requeridas y sus tipos: no se leen valores personales ni de cuentas.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'skilly'
  AND ((table_name = 'pago' AND column_name IN ('id_pago','metodo_pago','estado_pago','estado_verificacion'))
       OR (table_name = 'usuario' AND column_name = 'id_usuario'))
ORDER BY table_name, ordinal_position;

-- C) Claves primarias / únicas sobre columnas referenciadas.
SELECT conrelid::regclass::text AS tabla, conname AS restriccion,
       pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE conrelid IN (to_regclass('skilly.pago'), to_regclass('skilly.usuario'))
  AND contype IN ('p','u')
ORDER BY tabla, restriccion;

-- D) Cantidad de pagos; NO muestra transacciones, montos ni usuarios.
SELECT COUNT(*) AS total_pagos FROM skilly.pago;

-- E) Existencia de objetos potencialmente conflictivos.
SELECT n.nspname AS esquema, c.relname AS objeto,
       c.relkind AS tipo_objeto
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'skilly'
 AND c.relname IN (
 'cuenta_bancaria_skilly','cuenta_bancaria_skilly_historial',
 'instruccion_transferencia_skilly','uq_cuenta_bancaria_principal',
 'cuenta_bancaria_skilly_id_cuenta_seq',
 'cuenta_bancaria_skilly_historial_id_cambio_seq',
 'instruccion_transferencia_skilly_id_instruccion_seq')
ORDER BY objeto;

-- F) Verificar si ya existe la función o trigger que la migración alteraría.
SELECT n.nspname AS esquema, p.proname AS funcion
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname='skilly' AND p.proname='impedir_cambio_instruccion_transferencia';
SELECT event_object_schema, event_object_table, trigger_name
FROM information_schema.triggers
WHERE event_object_schema='skilly'
  AND trigger_name='tg_instruccion_transferencia_inmutable';
COMMIT;
