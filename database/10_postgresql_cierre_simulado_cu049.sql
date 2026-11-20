-- Aplicar después de respaldar las cinco tablas económicas y verificar la identidad.
-- No cambia datos: reemplaza tres CHECK en una transacción y valida todas las filas.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $$ BEGIN
    IF current_database() <> 'skilly' OR current_schema() <> 'skilly' THEN
        RAISE EXCEPTION 'Base o esquema ajenos a SKILLY';
    END IF;
END $$;
LOCK TABLE skilly.liquidacion_cancelacion_e3, skilly.conciliacion_reversa_e3 IN ACCESS EXCLUSIVE MODE;
ALTER TABLE skilly.liquidacion_cancelacion_e3
    DROP CONSTRAINT liquidacion_cancelacion_e3_estado_check,
    ADD CONSTRAINT liquidacion_cancelacion_e3_estado_check CHECK
        (estado IN ('REVERSA_SOLICITADA', 'PENDIENTE_CONCILIACION', 'DISTRIBUCION_SIMULADA'));
ALTER TABLE skilly.conciliacion_reversa_e3
    DROP CONSTRAINT conciliacion_reversa_e3_estado_check,
    DROP CONSTRAINT ck_e3_conciliacion_remanente,
    ADD CONSTRAINT conciliacion_reversa_e3_estado_check CHECK
        (estado IN ('SIMULACION_DOCUMENTAL', 'DISTRIBUCION_SIMULADA')),
    ADD CONSTRAINT ck_e3_conciliacion_remanente CHECK
        ((estado = 'SIMULACION_DOCUMENTAL' AND remanente_pendiente = monto_trabajo + monto_cargo)
         OR (estado = 'DISTRIBUCION_SIMULADA' AND remanente_pendiente = 0));
COMMIT;
