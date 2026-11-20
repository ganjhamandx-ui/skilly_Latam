-- Revierte solo si ninguna fila utiliza los estados nuevos. No reescribe cierres históricos.
-- Si existen cierres finales, aborta: conservar esquema y respaldos hasta planificar la reversión.
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
        (estado IN ('REVERSA_SOLICITADA', 'PENDIENTE_CONCILIACION'));
ALTER TABLE skilly.conciliacion_reversa_e3
    DROP CONSTRAINT conciliacion_reversa_e3_estado_check,
    DROP CONSTRAINT ck_e3_conciliacion_remanente,
    ADD CONSTRAINT conciliacion_reversa_e3_estado_check CHECK (estado = 'SIMULACION_DOCUMENTAL'),
    ADD CONSTRAINT ck_e3_conciliacion_remanente CHECK (remanente_pendiente = monto_trabajo + monto_cargo);
COMMIT;
