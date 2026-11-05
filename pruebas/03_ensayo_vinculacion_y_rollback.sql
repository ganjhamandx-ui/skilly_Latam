-- PRUEBA AISLADA Y REVERSIBLE: crea datos ficticios solo durante la transaccion.
-- Ejecutar DESPUES de 02_... en skilly_test_concurrencia usando pgAdmin/postgres.
BEGIN;
DO $$ DECLARE c BIGINT; h BIGINT; i BIGINT; s RECORD;
BEGIN
 IF current_database() <> 'skilly_test_concurrencia' THEN
  RAISE EXCEPTION 'BLOQUEADO: base incorrecta';
 END IF;
 IF (SELECT count(*) FROM public.cuenta_bancaria_skilly) <> 0
    OR (SELECT count(*) FROM public.cuenta_bancaria_skilly_historial) <> 0
    OR (SELECT count(*) FROM public.instruccion_transferencia_skilly) <> 0 THEN
  RAISE EXCEPTION 'Base de ensayo NO vacia: para no interferir no se ejecuta';
 END IF;
 INSERT INTO public.cuenta_bancaria_skilly
 (titular,rut_titular,banco,tipo_cuenta,numero_cuenta,correo,activa,principal)
 VALUES ('SKILLY DEMO','11111111-1','BANCO FICTICIO A','VISTA','1111100000','demo-a@example.invalid',true,true)
 RETURNING id_cuenta INTO c;
 INSERT INTO public.instruccion_transferencia_skilly
 (id_pago,id_cuenta,titular_fijado,rut_titular_fijado,banco_fijado,tipo_cuenta_fijado,numero_cuenta_fijado,correo_fijado)
 SELECT 990001, id_cuenta,titular,rut_titular,banco,tipo_cuenta,numero_cuenta,correo
 FROM public.cuenta_bancaria_skilly WHERE id_cuenta=c
 RETURNING id_instruccion INTO i;
 INSERT INTO public.cuenta_bancaria_skilly
 (titular,rut_titular,banco,tipo_cuenta,numero_cuenta,correo,activa,principal)
 VALUES ('SKILLY DEMO','11111111-1','BANCO FICTICIO B','CORRIENTE','2222200000','demo-b@example.invalid',true,false)
 RETURNING id_cuenta INTO h;
 UPDATE public.cuenta_bancaria_skilly SET principal=false WHERE id_cuenta=c;
 UPDATE public.cuenta_bancaria_skilly SET principal=true WHERE id_cuenta=h;
 SELECT * INTO s FROM public.instruccion_transferencia_skilly WHERE id_instruccion=i;
 IF s.banco_fijado <> 'BANCO FICTICIO A' OR s.numero_cuenta_fijado <> '1111100000' OR s.id_cuenta <> c THEN
  RAISE EXCEPTION 'FALLO: se alteraron las instrucciones historicas';
 END IF;
 IF (SELECT count(*) FROM public.cuenta_bancaria_skilly WHERE principal) <> 1 THEN
  RAISE EXCEPTION 'FALLO: debe existir una sola cuenta principal';
 END IF;
 RAISE NOTICE 'APROBADO: pago ficticio 990001 mantiene la cuenta A; cuenta B pasa a principal';
END $$;
ROLLBACK;
-- La prueba no guarda datos. Verificar 0 registros si el entorno estaba vacio.
SELECT current_database() AS base_actual,
 (SELECT count(*) FROM public.cuenta_bancaria_skilly) AS cuentas,
 (SELECT count(*) FROM public.instruccion_transferencia_skilly) AS instrucciones;
