-- Skilly Latam - PostgreSQL - Eliminación de tablas
-- Rúbrica B1: script separado DROP TABLE.
-- Ejecutar después de 04_postgresql_drop_fk.sql.
BEGIN;
SET search_path TO skilly;

DROP TABLE IF EXISTS historial_parametro;
DROP TABLE IF EXISTS parametro_sistema;
DROP TABLE IF EXISTS evento_trazabilidad;
DROP TABLE IF EXISTS recomendacion_desarrollo;
DROP TABLE IF EXISTS retroalimentacion;
DROP TABLE IF EXISTS resolucion_reclamo;
DROP TABLE IF EXISTS reclamo_prestacion;
DROP TABLE IF EXISTS observacion_entrega;
DROP TABLE IF EXISTS entrega;
DROP TABLE IF EXISTS avance_servicio;
DROP TABLE IF EXISTS reversa_pago;
DROP TABLE IF EXISTS historial_estado_pago;
DROP TABLE IF EXISTS pago;
DROP TABLE IF EXISTS prestacion_servicio;
DROP TABLE IF EXISTS reunion_solicitud;
DROP TABLE IF EXISTS coordinacion_solicitud;
DROP TABLE IF EXISTS asignacion_solicitud;
DROP TABLE IF EXISTS solicitud_profesional;
DROP TABLE IF EXISTS solicitud_competencia;
DROP TABLE IF EXISTS solicitud_servicio;
DROP TABLE IF EXISTS contacto_empresa;
DROP TABLE IF EXISTS empresa_solicitante;
DROP TABLE IF EXISTS reserva_disponibilidad;
DROP TABLE IF EXISTS disponibilidad;
DROP TABLE IF EXISTS revision_servicio;
DROP TABLE IF EXISTS servicio_competencia;
DROP TABLE IF EXISTS servicio;
DROP TABLE IF EXISTS categoria_servicio;
DROP TABLE IF EXISTS entrevista_validacion;
DROP TABLE IF EXISTS bloque_entrevista_validacion;
DROP TABLE IF EXISTS validacion_documento;
DROP TABLE IF EXISTS solicitud_validacion;
DROP TABLE IF EXISTS documento_profesional;
DROP TABLE IF EXISTS profesional_competencia;
DROP TABLE IF EXISTS competencia;
DROP TABLE IF EXISTS profesional;
DROP TABLE IF EXISTS recuperacion_acceso;
DROP TABLE IF EXISTS usuario;

COMMIT;
