-- Skilly
-- Migracion unica de timestamp without time zone a timestamptz.
--
-- Regla de conversion:
-- 1) Los datos sembrados por 06_postgresql_datos_prueba.sql
--    representan hora local America/Santiago.
-- 2) Los registros creados posteriormente por Django, mientras
--    USE_TZ=True y la conexion PostgreSQL estaba en UTC, quedaron
--    almacenados como valores UTC sin zona.
--
-- Excepciones actuales comprobadas:
-- usuario: IDs 9 y 10 fueron creados por Django.
-- recuperacion_acceso: IDs 2 a 12 fueron creados por Django.

BEGIN;

ALTER TABLE skilly."asignacion_solicitud"
    ALTER COLUMN "fecha_asignacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_asignacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."asignacion_solicitud"
    ALTER COLUMN "fecha_fin"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_fin" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."avance_servicio"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."contacto_empresa"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."coordinacion_solicitud"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."documento_profesional"
    ALTER COLUMN "fecha_carga"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_carga" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."empresa_solicitante"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."entrega"
    ALTER COLUMN "fecha_entrega"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_entrega" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."entrevista_validacion"
    ALTER COLUMN "fecha_reserva"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_reserva" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."evento_trazabilidad"
    ALTER COLUMN "fecha_evento"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_evento" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."historial_estado_pago"
    ALTER COLUMN "fecha_cambio"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_cambio" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."historial_parametro"
    ALTER COLUMN "fecha_cambio"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_cambio" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."observacion_entrega"
    ALTER COLUMN "fecha"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."pago"
    ALTER COLUMN "fecha_pago"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_pago" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."pago"
    ALTER COLUMN "fecha_retencion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_retencion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."pago"
    ALTER COLUMN "fecha_liberacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_liberacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."parametro_sistema"
    ALTER COLUMN "fecha_actualizacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_actualizacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."prestacion_servicio"
    ALTER COLUMN "fecha_confirmacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_confirmacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."prestacion_servicio"
    ALTER COLUMN "fecha_cierre"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_cierre" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."profesional"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."profesional_competencia"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reclamo_prestacion"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reclamo_prestacion"
    ALTER COLUMN "fecha_cierre"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_cierre" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."recomendacion_desarrollo"
    ALTER COLUMN "fecha_creacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_creacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."recomendacion_desarrollo"
    ALTER COLUMN "fecha_comunicacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_comunicacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."recuperacion_acceso"
    ALTER COLUMN "fecha_solicitud"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        CASE
                WHEN id_recuperacion = 1
                    THEN "fecha_solicitud" AT TIME ZONE 'America/Santiago'
                ELSE "fecha_solicitud" AT TIME ZONE 'UTC'
            END
    );

ALTER TABLE skilly."recuperacion_acceso"
    ALTER COLUMN "fecha_expiracion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        CASE
                WHEN id_recuperacion = 1
                    THEN "fecha_expiracion" AT TIME ZONE 'America/Santiago'
                ELSE "fecha_expiracion" AT TIME ZONE 'UTC'
            END
    );

ALTER TABLE skilly."reserva_disponibilidad"
    ALTER COLUMN "fecha_reserva"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_reserva" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reserva_disponibilidad"
    ALTER COLUMN "fecha_cambio"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_cambio" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."resolucion_reclamo"
    ALTER COLUMN "fecha_resolucion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_resolucion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."retroalimentacion"
    ALTER COLUMN "fecha_registro"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_registro" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reunion_solicitud"
    ALTER COLUMN "fecha_hora"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_hora" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reversa_pago"
    ALTER COLUMN "fecha_solicitud"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_solicitud" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."reversa_pago"
    ALTER COLUMN "fecha_resolucion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_resolucion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."revision_servicio"
    ALTER COLUMN "fecha_revision"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_revision" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."revision_servicio"
    ALTER COLUMN "fecha_aprobacion_profesional"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_aprobacion_profesional" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."servicio"
    ALTER COLUMN "fecha_publicacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_publicacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."servicio"
    ALTER COLUMN "fecha_actualizacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_actualizacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_profesional"
    ALTER COLUMN "fecha_asociacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_asociacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_servicio"
    ALTER COLUMN "fecha_solicitud"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_solicitud" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_servicio"
    ALTER COLUMN "fecha_actualizacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_actualizacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_validacion"
    ALTER COLUMN "fecha_solicitud"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_solicitud" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_validacion"
    ALTER COLUMN "fecha_asignacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_asignacion" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."solicitud_validacion"
    ALTER COLUMN "fecha_revision"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        "fecha_revision" AT TIME ZONE 'America/Santiago'
    );

ALTER TABLE skilly."usuario"
    ALTER COLUMN "fecha_creacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        CASE
                WHEN id_usuario IN (1, 2)
                    THEN "fecha_creacion" AT TIME ZONE 'America/Santiago'
                ELSE "fecha_creacion" AT TIME ZONE 'UTC'
            END
    );

ALTER TABLE skilly."usuario"
    ALTER COLUMN "fecha_actualizacion"
    TYPE TIMESTAMP WITH TIME ZONE
    USING (
        CASE
                WHEN id_usuario IN (1, 2)
                    THEN "fecha_actualizacion" AT TIME ZONE 'America/Santiago'
                ELSE "fecha_actualizacion" AT TIME ZONE 'UTC'
            END
    );

COMMIT;
