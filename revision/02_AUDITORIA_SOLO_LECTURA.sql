-- Solo lectura, usar únicamente después de aplicar la migración autorizada.
SELECT current_database() AS base, current_user AS usuario,
 to_regclass('skilly.cuenta_bancaria_skilly') AS cuentas,
 to_regclass('skilly.cuenta_bancaria_skilly_historial') AS historial,
 to_regclass('skilly.instruccion_transferencia_skilly') AS instrucciones;
SELECT count(*) AS pagos_existentes FROM skilly.pago;
