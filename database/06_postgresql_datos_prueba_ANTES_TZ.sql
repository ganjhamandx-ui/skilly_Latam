-- Skilly Latam - PostgreSQL - Datos sintéticos de prueba
-- Script complementario de carga para demostrar funcionamiento.
-- Estos registros son ficticios y se usan solo para evaluación/desarrollo.
-- No corresponden a personas, empresas, pagos ni operaciones reales.
BEGIN;
SET search_path TO skilly;

INSERT INTO usuario (id_usuario, correo, password_hash, rol, estado, fecha_creacion, fecha_actualizacion) VALUES
(1, 'profesional.demo@skilly.example', 'HASH_SINTETICO_NO_PRODUCTIVO', 'PROFESIONAL', 'ACTIVO', TIMESTAMP '2026-10-01 09:00:00', TIMESTAMP '2026-10-01 09:00:00'),
(2, 'admin.demo@skilly.example', 'HASH_SINTETICO_NO_PRODUCTIVO', 'ADMIN_SKILLY', 'ACTIVO', TIMESTAMP '2026-10-01 09:05:00', TIMESTAMP '2026-10-01 09:05:00');

INSERT INTO competencia (id_competencia, nombre, descripcion, estado) VALUES
(1, 'Gestión de proyectos', 'Competencia sintética de prueba.', 'ACTIVA');

INSERT INTO categoria_servicio (id_categoria, nombre, descripcion, estado) VALUES
(1, 'Gestión y liderazgo', 'Categoría sintética.', 'ACTIVA');

INSERT INTO empresa_solicitante (id_empresa, nombre_organizacion, rut, rubro, sitio_web, estado, fecha_registro) VALUES
(1, 'Empresa Demo SpA', '76.000.000-0', 'Servicios', 'https://example.com', 'ACTIVA', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO profesional (id_profesional, id_usuario, nombres, apellidos, telefono, titulo_profesional, resumen, ubicacion, estado_validacion, fecha_registro) VALUES
(1, 1, 'Ana', 'Demo', '+56911111111', 'Consultora de prueba', 'Perfil sintético creado para pruebas académicas de Skilly.', 'Santiago', 'APROBADO', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO bloque_entrevista_validacion (id_bloque_entrevista, id_usuario_gestor, fecha, hora_inicio, hora_fin, capacidad, estado) VALUES
(1, 2, DATE '2026-10-10', TIME '10:00:00', TIME '12:00:00', 1, 'DISPONIBLE');

INSERT INTO parametro_sistema (id_parametro, clave, valor_actual, tipo_dato, descripcion, id_usuario_actualiza, fecha_actualizacion) VALUES
(1, 'comision_porcentaje', '8.50', 'DECIMAL', 'Comisión configurable de prueba; valor sintético no fijo.', 2, TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO evento_trazabilidad (id_evento, id_usuario, entidad_tipo, entidad_id, accion, detalle_resumido, fecha_evento) VALUES
(1, 1, 'pago', 1, 'CAMBIO_ESTADO', 'Evento sintético de auditoría.', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO recuperacion_acceso (id_recuperacion, id_usuario, token_hash, fecha_solicitud, fecha_expiracion, usado) VALUES
(1, 1, 'HASH_SINTETICO_NO_PRODUCTIVO', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 11:00:00', TRUE);

INSERT INTO contacto_empresa (id_contacto, id_empresa, nombre, cargo, correo, telefono, fecha_registro) VALUES
(1, 1, 'Camila Demo', 'Jefatura de Personas', 'contacto@empresa.example', '+56922222222', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO documento_profesional (id_documento, id_profesional, tipo_documento, nombre_archivo, referencia_archivo, visibilidad, estado, fecha_carga) VALUES
(1, 1, 'CERTIFICADO', 'certificado_demo.pdf', 'demo/documentos/certificado_demo.pdf', 'PRIVADA', 'VIGENTE', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO profesional_competencia (id_profesional, id_competencia, fecha_registro) VALUES
(1, 1, TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO servicio (id_servicio, id_profesional, id_categoria, nombre, descripcion, modalidad, alcance, referencia_precio, estado_publicacion, fecha_publicacion, fecha_actualizacion) VALUES
(1, 1, 1, 'Asesoría de gestión', 'Servicio de prueba para validación académica.', 'REMOTA', 'Sesión de asesoría y cierre.', '100000 CLP', 'PUBLICADO', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO disponibilidad (id_disponibilidad, id_profesional, fecha, hora_inicio, hora_fin, estado) VALUES
(1, 1, DATE '2026-10-10', TIME '10:00:00', TIME '12:00:00', 'RESERVADA');

INSERT INTO solicitud_validacion (id_validacion, id_profesional, id_revisor_skilly, estado, fecha_solicitud, fecha_asignacion, fecha_revision, observacion_resultado) VALUES
(1, 1, 2, 'APROBADA', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00', 'Validación sintética para pruebas.');

INSERT INTO historial_parametro (id_historial_parametro, id_parametro, valor_anterior, valor_nuevo, id_usuario_skilly, fecha_cambio) VALUES
(1, 1, '7.50', '8.50', 2, TIMESTAMP '2026-10-13 12:00:00');

INSERT INTO revision_servicio (id_revision_servicio, id_servicio, id_usuario_skilly, numero_version, contenido_revisado, observacion, estado_revision, fecha_revision, fecha_aprobacion_profesional) VALUES
(1, 1, 2, 1, 'Versión comercial revisada.', 'Ajuste sintético.', 'APROBADA', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO solicitud_servicio (id_solicitud, id_empresa, id_contacto, id_servicio, objetivo, descripcion_necesidad, modalidad, fecha_preferida, referencia_presupuesto, urgencia, estado, fecha_solicitud, fecha_actualizacion) VALUES
(1, 1, 1, 1, 'Fortalecer capacidades del equipo', 'Solicitud sintética de prueba.', 'REMOTA', DATE '2026-10-10', '100000 CLP', 'MEDIA', 'COORDINADA', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO servicio_competencia (id_servicio, id_competencia) VALUES
(1, 1);

INSERT INTO entrevista_validacion (id_entrevista, id_validacion, id_bloque_entrevista, estado, fecha_reserva, observacion) VALUES
(1, 1, 1, 'REALIZADA', TIMESTAMP '2026-10-10 10:00:00', 'Entrevista de prueba realizada.');

INSERT INTO validacion_documento (id_validacion, id_documento, estado_revision, observacion) VALUES
(1, 1, 'APROBADO', 'Documento revisado.');

INSERT INTO coordinacion_solicitud (id_coordinacion, id_solicitud, id_usuario_skilly, tipo, detalle, estado_resultante, fecha_registro) VALUES
(1, 1, 2, 'COORDINACION', 'Coordinación sintética.', 'COORDINADA', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO asignacion_solicitud (id_asignacion, id_solicitud, id_usuario_skilly, tipo_asignacion, fecha_asignacion, fecha_fin, estado) VALUES
(1, 1, 2, 'MANUAL', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-14 16:00:00', 'ACTIVA');

INSERT INTO solicitud_competencia (id_solicitud, id_competencia) VALUES
(1, 1);

INSERT INTO prestacion_servicio (id_prestacion, id_solicitud, id_profesional, condiciones_comunicadas, estado, fecha_confirmacion, fecha_inicio, fecha_fin, fecha_cierre) VALUES
(1, 1, 1, 'Condiciones comunicadas para escenario sintético.', 'FINALIZADA', TIMESTAMP '2026-10-10 10:00:00', DATE '2026-10-10', DATE '2026-10-14', TIMESTAMP '2026-10-14 16:00:00');

INSERT INTO reunion_solicitud (id_reunion, id_solicitud, id_profesional, id_usuario_skilly, fecha_hora, modalidad, estado, enlace_reunion) VALUES
(1, 1, 1, 2, TIMESTAMP '2026-10-10 10:00:00', 'REMOTA', 'AGENDADA', 'https://meet.example/skilly-demo');

INSERT INTO solicitud_profesional (id_solicitud, id_profesional, tipo_asociacion, estado, fecha_asociacion) VALUES
(1, 1, 'PROPUESTO', 'ACEPTADO', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO reserva_disponibilidad (id_reserva, id_disponibilidad, id_solicitud, estado, fecha_reserva, fecha_cambio, motivo_cambio) VALUES
(1, 1, 1, 'ACTIVA', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-13 12:00:00', 'Sin cambio.');

INSERT INTO entrega (id_entrega, id_prestacion, version, descripcion, referencia_entrega, fecha_entrega, estado) VALUES
(1, 1, 1, 'Entrega de prueba.', 'demo/entregas/entrega_1.pdf', TIMESTAMP '2026-10-10 10:00:00', 'ENTREGADA');

INSERT INTO avance_servicio (id_avance, id_prestacion, estado, detalle, fecha_registro) VALUES
(1, 1, 'EN_PROGRESO', 'Avance sintético de prueba.', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO retroalimentacion (id_feedback, id_prestacion, id_contacto, contenido, visibilidad, estado, fecha_registro) VALUES
(1, 1, 1, 'Feedback privado sintético.', 'PRIVADA', 'REGISTRADA', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO reclamo_prestacion (id_reclamo, id_prestacion, id_contacto, motivo, descripcion, estado, fecha_registro, fecha_cierre) VALUES
(1, 1, 1, 'DISCONFORMIDAD', 'Reclamo sintético para probar el flujo.', 'RESUELTO', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-14 16:00:00');

INSERT INTO pago (id_pago, id_prestacion, monto_total, moneda, porcentaje_comision_aplicado, monto_comision, monto_neto_profesional, estado_pago, metodo_pago, proveedor_pago, estado_verificacion, comprobante_transferencia, fecha_pago, fecha_retencion, fecha_liberacion, referencia_transaccion) VALUES
(1, 1, 100000, 'CLP', 8.5, 8500, 91500, 'RETENIDO', 'TRANSFERENCIA', NULL, 'VERIFICADO', 'demo/comprobantes/pago_1.pdf', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00', NULL, 'TRX-DEMO-001');

INSERT INTO observacion_entrega (id_observacion, id_entrega, id_contacto, fecha, detalle, estado) VALUES
(1, 1, 1, TIMESTAMP '2026-10-10 10:00:00', 'Se solicita aclaración de un punto.', 'REGISTRADA');

INSERT INTO recomendacion_desarrollo (id_recomendacion, id_profesional, id_feedback, id_usuario_skilly, titulo, descripcion, estado, fecha_creacion, fecha_comunicacion) VALUES
(1, 1, 1, 2, 'Reforzar facilitación', 'Recomendación sintética.', 'COMUNICADA', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-10 10:00:00');

INSERT INTO resolucion_reclamo (id_resolucion, id_reclamo, id_usuario_skilly, decision, efecto_economico, monto_afectado, observacion, fecha_resolucion) VALUES
(1, 1, 2, 'DEVOLUCION', 'REVERSA', 100000, 'Resolución sintética de prueba.', TIMESTAMP '2026-10-14 16:00:00');

INSERT INTO historial_estado_pago (id_historial_pago, id_pago, id_usuario_skilly, estado_anterior, estado_nuevo, fecha_cambio, observacion) VALUES
(1, 1, 2, 'CONFIRMADO', 'RETENIDO', TIMESTAMP '2026-10-13 12:00:00', 'Cambio de estado sintético.');

INSERT INTO reversa_pago (id_reversa, id_pago, id_usuario_skilly, id_resolucion_reclamo, monto_reversa, estado_reversa, motivo, referencia_externa, fecha_solicitud, fecha_resolucion) VALUES
(1, 1, 2, 1, 100000, 'SOLICITADA', 'Resolución económica de reclamo de prueba.', 'REV-DEMO-001', TIMESTAMP '2026-10-10 10:00:00', TIMESTAMP '2026-10-14 16:00:00');

-- Sincronización de secuencias después de usar IDs explícitos de prueba
SELECT setval(pg_get_serial_sequence('skilly.usuario', 'id_usuario'), (SELECT MAX(id_usuario) FROM skilly.usuario), true);
SELECT setval(pg_get_serial_sequence('skilly.recuperacion_acceso', 'id_recuperacion'), (SELECT MAX(id_recuperacion) FROM skilly.recuperacion_acceso), true);
SELECT setval(pg_get_serial_sequence('skilly.profesional', 'id_profesional'), (SELECT MAX(id_profesional) FROM skilly.profesional), true);
SELECT setval(pg_get_serial_sequence('skilly.competencia', 'id_competencia'), (SELECT MAX(id_competencia) FROM skilly.competencia), true);
SELECT setval(pg_get_serial_sequence('skilly.documento_profesional', 'id_documento'), (SELECT MAX(id_documento) FROM skilly.documento_profesional), true);
SELECT setval(pg_get_serial_sequence('skilly.solicitud_validacion', 'id_validacion'), (SELECT MAX(id_validacion) FROM skilly.solicitud_validacion), true);
SELECT setval(pg_get_serial_sequence('skilly.bloque_entrevista_validacion', 'id_bloque_entrevista'), (SELECT MAX(id_bloque_entrevista) FROM skilly.bloque_entrevista_validacion), true);
SELECT setval(pg_get_serial_sequence('skilly.entrevista_validacion', 'id_entrevista'), (SELECT MAX(id_entrevista) FROM skilly.entrevista_validacion), true);
SELECT setval(pg_get_serial_sequence('skilly.categoria_servicio', 'id_categoria'), (SELECT MAX(id_categoria) FROM skilly.categoria_servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.servicio', 'id_servicio'), (SELECT MAX(id_servicio) FROM skilly.servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.revision_servicio', 'id_revision_servicio'), (SELECT MAX(id_revision_servicio) FROM skilly.revision_servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.disponibilidad', 'id_disponibilidad'), (SELECT MAX(id_disponibilidad) FROM skilly.disponibilidad), true);
SELECT setval(pg_get_serial_sequence('skilly.reserva_disponibilidad', 'id_reserva'), (SELECT MAX(id_reserva) FROM skilly.reserva_disponibilidad), true);
SELECT setval(pg_get_serial_sequence('skilly.empresa_solicitante', 'id_empresa'), (SELECT MAX(id_empresa) FROM skilly.empresa_solicitante), true);
SELECT setval(pg_get_serial_sequence('skilly.contacto_empresa', 'id_contacto'), (SELECT MAX(id_contacto) FROM skilly.contacto_empresa), true);
SELECT setval(pg_get_serial_sequence('skilly.solicitud_servicio', 'id_solicitud'), (SELECT MAX(id_solicitud) FROM skilly.solicitud_servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.asignacion_solicitud', 'id_asignacion'), (SELECT MAX(id_asignacion) FROM skilly.asignacion_solicitud), true);
SELECT setval(pg_get_serial_sequence('skilly.coordinacion_solicitud', 'id_coordinacion'), (SELECT MAX(id_coordinacion) FROM skilly.coordinacion_solicitud), true);
SELECT setval(pg_get_serial_sequence('skilly.reunion_solicitud', 'id_reunion'), (SELECT MAX(id_reunion) FROM skilly.reunion_solicitud), true);
SELECT setval(pg_get_serial_sequence('skilly.prestacion_servicio', 'id_prestacion'), (SELECT MAX(id_prestacion) FROM skilly.prestacion_servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.pago', 'id_pago'), (SELECT MAX(id_pago) FROM skilly.pago), true);
SELECT setval(pg_get_serial_sequence('skilly.historial_estado_pago', 'id_historial_pago'), (SELECT MAX(id_historial_pago) FROM skilly.historial_estado_pago), true);
SELECT setval(pg_get_serial_sequence('skilly.reversa_pago', 'id_reversa'), (SELECT MAX(id_reversa) FROM skilly.reversa_pago), true);
SELECT setval(pg_get_serial_sequence('skilly.avance_servicio', 'id_avance'), (SELECT MAX(id_avance) FROM skilly.avance_servicio), true);
SELECT setval(pg_get_serial_sequence('skilly.entrega', 'id_entrega'), (SELECT MAX(id_entrega) FROM skilly.entrega), true);
SELECT setval(pg_get_serial_sequence('skilly.observacion_entrega', 'id_observacion'), (SELECT MAX(id_observacion) FROM skilly.observacion_entrega), true);
SELECT setval(pg_get_serial_sequence('skilly.reclamo_prestacion', 'id_reclamo'), (SELECT MAX(id_reclamo) FROM skilly.reclamo_prestacion), true);
SELECT setval(pg_get_serial_sequence('skilly.resolucion_reclamo', 'id_resolucion'), (SELECT MAX(id_resolucion) FROM skilly.resolucion_reclamo), true);
SELECT setval(pg_get_serial_sequence('skilly.retroalimentacion', 'id_feedback'), (SELECT MAX(id_feedback) FROM skilly.retroalimentacion), true);
SELECT setval(pg_get_serial_sequence('skilly.recomendacion_desarrollo', 'id_recomendacion'), (SELECT MAX(id_recomendacion) FROM skilly.recomendacion_desarrollo), true);
SELECT setval(pg_get_serial_sequence('skilly.evento_trazabilidad', 'id_evento'), (SELECT MAX(id_evento) FROM skilly.evento_trazabilidad), true);
SELECT setval(pg_get_serial_sequence('skilly.parametro_sistema', 'id_parametro'), (SELECT MAX(id_parametro) FROM skilly.parametro_sistema), true);
SELECT setval(pg_get_serial_sequence('skilly.historial_parametro', 'id_historial_parametro'), (SELECT MAX(id_historial_parametro) FROM skilly.historial_parametro), true);

COMMIT;