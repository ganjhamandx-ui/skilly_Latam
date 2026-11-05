-- Skilly Latam - PostgreSQL - Llaves primarias
-- Rúbrica B1: script separado de PK.
BEGIN;
SET search_path TO skilly;

ALTER TABLE usuario ADD CONSTRAINT pk_usuario PRIMARY KEY (id_usuario);
ALTER TABLE recuperacion_acceso ADD CONSTRAINT pk_recuperacion_acceso PRIMARY KEY (id_recuperacion);
ALTER TABLE profesional ADD CONSTRAINT pk_profesional PRIMARY KEY (id_profesional);
ALTER TABLE competencia ADD CONSTRAINT pk_competencia PRIMARY KEY (id_competencia);
ALTER TABLE profesional_competencia ADD CONSTRAINT pk_profesional_competencia PRIMARY KEY (id_profesional, id_competencia);
ALTER TABLE documento_profesional ADD CONSTRAINT pk_documento_profesional PRIMARY KEY (id_documento);
ALTER TABLE solicitud_validacion ADD CONSTRAINT pk_solicitud_validacion PRIMARY KEY (id_validacion);
ALTER TABLE validacion_documento ADD CONSTRAINT pk_validacion_documento PRIMARY KEY (id_validacion, id_documento);
ALTER TABLE bloque_entrevista_validacion ADD CONSTRAINT pk_bloque_entrevista_validacion PRIMARY KEY (id_bloque_entrevista);
ALTER TABLE entrevista_validacion ADD CONSTRAINT pk_entrevista_validacion PRIMARY KEY (id_entrevista);
ALTER TABLE categoria_servicio ADD CONSTRAINT pk_categoria_servicio PRIMARY KEY (id_categoria);
ALTER TABLE servicio ADD CONSTRAINT pk_servicio PRIMARY KEY (id_servicio);
ALTER TABLE servicio_competencia ADD CONSTRAINT pk_servicio_competencia PRIMARY KEY (id_servicio, id_competencia);
ALTER TABLE revision_servicio ADD CONSTRAINT pk_revision_servicio PRIMARY KEY (id_revision_servicio);
ALTER TABLE disponibilidad ADD CONSTRAINT pk_disponibilidad PRIMARY KEY (id_disponibilidad);
ALTER TABLE reserva_disponibilidad ADD CONSTRAINT pk_reserva_disponibilidad PRIMARY KEY (id_reserva);
ALTER TABLE empresa_solicitante ADD CONSTRAINT pk_empresa_solicitante PRIMARY KEY (id_empresa);
ALTER TABLE contacto_empresa ADD CONSTRAINT pk_contacto_empresa PRIMARY KEY (id_contacto);
ALTER TABLE solicitud_servicio ADD CONSTRAINT pk_solicitud_servicio PRIMARY KEY (id_solicitud);
ALTER TABLE solicitud_competencia ADD CONSTRAINT pk_solicitud_competencia PRIMARY KEY (id_solicitud, id_competencia);
ALTER TABLE solicitud_profesional ADD CONSTRAINT pk_solicitud_profesional PRIMARY KEY (id_solicitud, id_profesional);
ALTER TABLE asignacion_solicitud ADD CONSTRAINT pk_asignacion_solicitud PRIMARY KEY (id_asignacion);
ALTER TABLE coordinacion_solicitud ADD CONSTRAINT pk_coordinacion_solicitud PRIMARY KEY (id_coordinacion);
ALTER TABLE reunion_solicitud ADD CONSTRAINT pk_reunion_solicitud PRIMARY KEY (id_reunion);
ALTER TABLE prestacion_servicio ADD CONSTRAINT pk_prestacion_servicio PRIMARY KEY (id_prestacion);
ALTER TABLE pago ADD CONSTRAINT pk_pago PRIMARY KEY (id_pago);
ALTER TABLE historial_estado_pago ADD CONSTRAINT pk_historial_estado_pago PRIMARY KEY (id_historial_pago);
ALTER TABLE reversa_pago ADD CONSTRAINT pk_reversa_pago PRIMARY KEY (id_reversa);
ALTER TABLE avance_servicio ADD CONSTRAINT pk_avance_servicio PRIMARY KEY (id_avance);
ALTER TABLE entrega ADD CONSTRAINT pk_entrega PRIMARY KEY (id_entrega);
ALTER TABLE observacion_entrega ADD CONSTRAINT pk_observacion_entrega PRIMARY KEY (id_observacion);
ALTER TABLE reclamo_prestacion ADD CONSTRAINT pk_reclamo_prestacion PRIMARY KEY (id_reclamo);
ALTER TABLE resolucion_reclamo ADD CONSTRAINT pk_resolucion_reclamo PRIMARY KEY (id_resolucion);
ALTER TABLE retroalimentacion ADD CONSTRAINT pk_retroalimentacion PRIMARY KEY (id_feedback);
ALTER TABLE recomendacion_desarrollo ADD CONSTRAINT pk_recomendacion_desarrollo PRIMARY KEY (id_recomendacion);
ALTER TABLE evento_trazabilidad ADD CONSTRAINT pk_evento_trazabilidad PRIMARY KEY (id_evento);
ALTER TABLE parametro_sistema ADD CONSTRAINT pk_parametro_sistema PRIMARY KEY (id_parametro);
ALTER TABLE historial_parametro ADD CONSTRAINT pk_historial_parametro PRIMARY KEY (id_historial_parametro);

COMMIT;
