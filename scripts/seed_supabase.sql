-- ====================================================================
-- VYGO · PLAN DE INYECCIÓN DE DATOS V2.0 (12 de septiembre de 2026)
-- Reconciliado con Supabase ihmadvmoenkxanoxrwcy (11 tablas con UUIDs)
-- ====================================================================
-- Asegurar extension PostGIS e incluir esquemas postgis y extensions en search_path
CREATE EXTENSION IF NOT EXISTS postgis;
SET search_path TO public, postgis, extensions;

BEGIN;
SET LOCAL search_path TO public, postgis, extensions;

-- 0. Usuario demo en auth.users (Satisface FK de platform_connections en Supabase Auth)
INSERT INTO auth.users (
  id, instance_id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  created_at, updated_at
) VALUES (
  'b9acb1bb-ee96-59c0-9e84-31f29368c97b',
  '00000000-0000-0000-0000-000000000000',
  'authenticated',
  'authenticated',
  'carlos.demo@vygo.mx',
  '',
  now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{"nombre":"Carlos Repartidor Demo"}'::jsonb,
  now(),
  now()
) ON CONFLICT (id) DO NOTHING;

-- 1. Catalogo de Apps (3)
INSERT INTO apps (id, nombre, activa) VALUES
  (1, 'uber', true),
  (2, 'rappi', true),
  (3, 'didi', true)
ON CONFLICT (id) DO UPDATE SET activa = EXCLUDED.activa;

-- 2. Usuarios (1 repartidor + 30 clientes con UUIDs válidos y tipo)
INSERT INTO usuarios (id, nombre, email, telefono, tipo) VALUES
  ('b9acb1bb-ee96-59c0-9e84-31f29368c97b', 'Carlos Repartidor Demo', 'carlos.demo@vygo.mx', '8110000001', 'repartidor'),
  ('408d6ac1-9179-56a2-9184-eb1d9ab28e1d', 'Cliente Ficticio 1', 'cliente1@ejemplo.com', '8110000001', 'cliente'),
  ('2c0ccdd0-a357-5ce5-97f5-a2a29e956fb3', 'Cliente Ficticio 2', 'cliente2@ejemplo.com', '8110000002', 'cliente'),
  ('e32bd79e-4e9c-5e71-b162-37868794420d', 'Cliente Ficticio 3', 'cliente3@ejemplo.com', '8110000003', 'cliente'),
  ('5f842c2f-b6b4-56d9-bf5f-8a15fec6d1c7', 'Cliente Ficticio 4', 'cliente4@ejemplo.com', '8110000004', 'cliente'),
  ('22eb0adb-4d8e-5229-9208-a921b7252c1c', 'Cliente Ficticio 5', 'cliente5@ejemplo.com', '8110000005', 'cliente'),
  ('2f05489f-eabf-5044-bc95-ab50bfd1805e', 'Cliente Ficticio 6', 'cliente6@ejemplo.com', '8110000006', 'cliente'),
  ('86554df5-02cc-55ae-9460-47c38d02dcad', 'Cliente Ficticio 7', 'cliente7@ejemplo.com', '8110000007', 'cliente'),
  ('befe1909-5faa-5814-893e-0e1d6b68dfb2', 'Cliente Ficticio 8', 'cliente8@ejemplo.com', '8110000008', 'cliente'),
  ('532be45a-f8ef-5d90-9c35-d661857a1e8b', 'Cliente Ficticio 9', 'cliente9@ejemplo.com', '8110000009', 'cliente'),
  ('1c7a5a8c-8181-55e2-902d-de7579abddd6', 'Cliente Ficticio 10', 'cliente10@ejemplo.com', '8110000010', 'cliente'),
  ('b840e7ba-0b95-5124-8972-18106cbe3417', 'Cliente Ficticio 11', 'cliente11@ejemplo.com', '8110000011', 'cliente'),
  ('ae52d4d4-c340-5c58-9c17-e638f7a13b0a', 'Cliente Ficticio 12', 'cliente12@ejemplo.com', '8110000012', 'cliente'),
  ('dad63d0c-e3bb-5a2e-9842-463e46c7320e', 'Cliente Ficticio 13', 'cliente13@ejemplo.com', '8110000013', 'cliente'),
  ('22c8c413-d70b-5d64-98d5-e1c2feedaa4a', 'Cliente Ficticio 14', 'cliente14@ejemplo.com', '8110000014', 'cliente'),
  ('021e73d2-d111-5b69-874b-56bbb56c3119', 'Cliente Ficticio 15', 'cliente15@ejemplo.com', '8110000015', 'cliente'),
  ('f345e6a7-b333-53d2-867e-1a66f3644c80', 'Cliente Ficticio 16', 'cliente16@ejemplo.com', '8110000016', 'cliente'),
  ('c459d89a-3292-5bc4-adc4-85c930d2fe56', 'Cliente Ficticio 17', 'cliente17@ejemplo.com', '8110000017', 'cliente'),
  ('f398b049-f10e-50ea-ba4f-14ea29266783', 'Cliente Ficticio 18', 'cliente18@ejemplo.com', '8110000018', 'cliente'),
  ('d0b71226-6c66-516f-b2f7-674487c971dc', 'Cliente Ficticio 19', 'cliente19@ejemplo.com', '8110000019', 'cliente'),
  ('afab2c2c-8f1d-5f9d-a531-dff8383ba158', 'Cliente Ficticio 20', 'cliente20@ejemplo.com', '8110000020', 'cliente'),
  ('c33443ab-6a47-5b88-94f9-c03f0aae4b6d', 'Cliente Ficticio 21', 'cliente21@ejemplo.com', '8110000021', 'cliente'),
  ('ab78ad4d-79d1-57ba-8e9c-b4aa0d04f4ef', 'Cliente Ficticio 22', 'cliente22@ejemplo.com', '8110000022', 'cliente'),
  ('d79024be-104b-5028-aac2-6ef0f2424889', 'Cliente Ficticio 23', 'cliente23@ejemplo.com', '8110000023', 'cliente'),
  ('ed9ce1ae-2ccc-526a-93dc-6e4730bc97db', 'Cliente Ficticio 24', 'cliente24@ejemplo.com', '8110000024', 'cliente'),
  ('be7bf195-d495-55cf-be94-df3d0ebb8875', 'Cliente Ficticio 25', 'cliente25@ejemplo.com', '8110000025', 'cliente'),
  ('d6334f88-8f33-5b59-a7ae-fea47db25aea', 'Cliente Ficticio 26', 'cliente26@ejemplo.com', '8110000026', 'cliente'),
  ('2a0ef942-df89-5a5b-9780-37c50efa9814', 'Cliente Ficticio 27', 'cliente27@ejemplo.com', '8110000027', 'cliente'),
  ('9b3d1e11-11de-5e5c-b9b0-7df30b29f352', 'Cliente Ficticio 28', 'cliente28@ejemplo.com', '8110000028', 'cliente'),
  ('e4551e53-f932-577c-ba23-ba6483cb0fdd', 'Cliente Ficticio 29', 'cliente29@ejemplo.com', '8110000029', 'cliente'),
  ('35442812-0bcd-5a96-8f2b-8dbc059000d9', 'Cliente Ficticio 30', 'cliente30@ejemplo.com', '8110000030', 'cliente')
ON CONFLICT (id) DO NOTHING;

-- 3. Repartidor de Demo
INSERT INTO repartidores (id, usuario_id, app_id, vehiculo, disponible, rating) VALUES
  ('e9128a20-84fd-55e4-bd02-7b0d09f88010', 'b9acb1bb-ee96-59c0-9e84-31f29368c97b', 1, 'moto', true, 4.95)
ON CONFLICT (id) DO UPDATE SET disponible = true, vehiculo = 'moto';

-- 4. Conexiones de plataforma activas (3)
INSERT INTO platform_connections (id, user_id, platform, is_active) VALUES
  ('9075a470-b35c-5dd6-8050-9a78c8fe24cb', 'b9acb1bb-ee96-59c0-9e84-31f29368c97b', 'uber', true),
  ('1522af3a-3e14-5f7b-b9a0-dd8e261e1617', 'b9acb1bb-ee96-59c0-9e84-31f29368c97b', 'rappi', true),
  ('2023e422-f814-52a5-9d26-d30a7442493c', 'b9acb1bb-ee96-59c0-9e84-31f29368c97b', 'didi', true)
ON CONFLICT (user_id, platform) DO UPDATE SET is_active = EXCLUDED.is_active;

-- 5. Parametros de configuracion del sistema (10 claves §3.5)
INSERT INTO configuracion (clave, valor) VALUES
  ('radio_ronda_1_metros', '1500'),
  ('radio_ronda_2_metros', '3000'),
  ('radio_ronda_3_metros', '5000'),
  ('duracion_ronda_seg', '45'),
  ('expiracion_oferta_seg', '30'),
  ('max_rondas', '3'),
  ('max_pedidos_por_viaje', '4'),
  ('costo_km_mxn', '1.2'),
  ('rho_inicial_mxn_h', '140.0'),
  ('duracion_turno_min', '360')
ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

-- 6. Posicion inicial del conductor (Monterrey ZM)
INSERT INTO ubicaciones_conductores (user_id, lat, lng, updated_at) VALUES
  ('b9acb1bb-ee96-59c0-9e84-31f29368c97b', 25.6714, -100.3094, now())
ON CONFLICT (user_id) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, updated_at = now();

-- 7. Viaje activo iniciado hace 90 min con origen y destino en Monterrey
INSERT INTO viajes_repartidor (id, repartidor_id, estado, iniciado_en, origen_actual, destino_final) VALUES
  ('d1c74636-8398-521d-907f-e5e9c40c498f', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'activo', now() - interval '90 minutes', 'SRID=4326;POINT(-100.3094 25.6714)', 'SRID=4326;POINT(-100.2980 25.6650)')
ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado, origen_actual = EXCLUDED.origen_actual;

-- 8. Pedidos con contexto JSONB completo (12 entregados, 3 asignados, 25 buscando)
INSERT INTO pedidos (id, app_id, id_externo, cliente_id, origen, origen_direccion, destino, destino_direccion, estado, clima, contexto, precio, moneda, creado_en) VALUES
  ('ce2a38ca-bfe7-58b5-82ea-8eebac6c5270', 1, 'UBER-cen-01', '408d6ac1-9179-56a2-9184-eb1d9ab28e1d', 'SRID=4326;POINT(-100.3014 25.6714)', 'Sushi Roll Centro, Centro', 'SRID=4326;POINT(-100.2882 25.6786)', 'Calle Entrega 1, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Roll Centro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '30 minutes'),
  ('e80f5077-c3c3-58e4-9526-64509deb735d', 2, 'RAPPI-cen-02', '2c0ccdd0-a357-5ce5-97f5-a2a29e956fb3', 'SRID=4326;POINT(-100.3073 25.6791)', 'Tacos El Primo, Centro', 'SRID=4326;POINT(-100.3202 25.6868)', 'Calle Entrega 2, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos El Primo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '30 minutes'),
  ('a8da2c97-5410-5145-af89-f06f17236240', 3, 'DIDI-cen-03', 'e32bd79e-4e9c-5e71-b162-37868794420d', 'SRID=4326;POINT(-100.3163 25.6755)', 'La Bella Italia Centro, Centro', 'SRID=4326;POINT(-100.3165 25.6605)', 'Calle Entrega 3, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "La Bella Italia Centro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '30 minutes'),
  ('3aee675d-283b-5808-8a76-d1dd28a01ead', 1, 'UBER-cen-04', '5f842c2f-b6b4-56d9-bf5f-8a15fec6d1c7', 'SRID=4326;POINT(-100.3152 25.6659)', 'Burgers MTY Macroplaza, Centro', 'SRID=4326;POINT(-100.3022 25.6733)', 'Calle Entrega 4, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burgers MTY Macroplaza", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '30 minutes'),
  ('79f6b6d4-ba45-5e70-b935-4d7b8244dbb6', 2, 'RAPPI-cen-05', '22eb0adb-4d8e-5229-9208-a921b7252c1c', 'SRID=4326;POINT(-100.3057 25.6643)', 'Chilaquiles Barrio Antiguo, Centro', 'SRID=4326;POINT(-100.3187 25.6718)', 'Calle Entrega 5, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Chilaquiles Barrio Antiguo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '30 minutes'),
  ('9ee880d6-7b56-5954-adf9-c397b064c4c1', 3, 'DIDI-cen-06', '2f05489f-eabf-5044-bc95-ab50bfd1805e', 'SRID=4326;POINT(-100.3016 25.6731)', 'Sushi Roll Centro, Centro', 'SRID=4326;POINT(-100.3015 25.6581)', 'Calle Entrega 6, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Roll Centro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '30 minutes'),
  ('96551310-48cc-54bf-ba6e-e7bf9c680036', 1, 'UBER-cen-07', '86554df5-02cc-55ae-9460-47c38d02dcad', 'SRID=4326;POINT(-100.309 25.6794)', 'Tacos El Primo, Centro', 'SRID=4326;POINT(-100.2961 25.687)', 'Calle Entrega 7, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos El Primo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '30 minutes'),
  ('70609dc0-57b2-55b3-b828-341fb7a9ef8b', 2, 'RAPPI-cen-08', 'befe1909-5faa-5814-893e-0e1d6b68dfb2', 'SRID=4326;POINT(-100.317 25.674)', 'La Bella Italia Centro, Centro', 'SRID=4326;POINT(-100.3301 25.6813)', 'Calle Entrega 8, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "La Bella Italia Centro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '30 minutes'),
  ('2aacb4cf-81ec-515f-91d8-12179af7ebeb', 3, 'DIDI-cen-09', '532be45a-f8ef-5d90-9c35-d661857a1e8b', 'SRID=4326;POINT(-100.3139 25.6648)', 'Burgers MTY Macroplaza, Centro', 'SRID=4326;POINT(-100.3136 25.6498)', 'Calle Entrega 9, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burgers MTY Macroplaza", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '30 minutes'),
  ('1e01906e-7b4e-592e-88c5-ad0a5341aa72', 1, 'UBER-cen-10', '1c7a5a8c-8181-55e2-902d-de7579abddd6', 'SRID=4326;POINT(-100.3042 25.6653)', 'Chilaquiles Barrio Antiguo, Centro', 'SRID=4326;POINT(-100.2914 25.6731)', 'Calle Entrega 10, Centro', 'entregado', 'despejado', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Chilaquiles Barrio Antiguo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '30 minutes'),
  ('247fba58-b7f4-5fb4-bfd3-980186b679fa', 1, 'UBER-san-01', 'b840e7ba-0b95-5124-8972-18106cbe3417', 'SRID=4326;POINT(-100.348 25.658)', 'La Postrería Valle, San Pedro / Valle', 'SRID=4326;POINT(-100.3348 25.6652)', 'Calle Entrega 1, San Pedro / Valle', 'entregado', 'despejado', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "La Postrería Valle", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 60.0, 'MXN', now() - interval '30 minutes'),
  ('10dc7f35-94b2-5fac-89e1-7c04c28120e5', 2, 'RAPPI-san-02', 'ae52d4d4-c340-5c58-9c17-e638f7a13b0a', 'SRID=4326;POINT(-100.3539 25.6657)', 'Steak House San Pedro, San Pedro / Valle', 'SRID=4326;POINT(-100.3668 25.6734)', 'Calle Entrega 2, San Pedro / Valle', 'entregado', 'despejado', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Steak House San Pedro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 64.5, 'MXN', now() - interval '30 minutes'),
  ('03e1181a-0c8a-5a40-924b-549ad8773160', 3, 'DIDI-san-03', 'dad63d0c-e3bb-5a2e-9842-463e46c7320e', 'SRID=4326;POINT(-100.3629 25.6621)', 'Green Bowl Vasconcelos, San Pedro / Valle', 'SRID=4326;POINT(-100.3631 25.6471)', 'Calle Entrega 3, San Pedro / Valle', 'asignado', 'despejado', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Green Bowl Vasconcelos", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 69.0, 'MXN', now() - interval '2 minutes'),
  ('4126548f-fb13-5180-a17f-dfc80c95cad4', 1, 'UBER-san-04', '22c8c413-d70b-5d64-98d5-e1c2feedaa4a', 'SRID=4326;POINT(-100.3618 25.6525)', 'Poke Bar Del Valle, San Pedro / Valle', 'SRID=4326;POINT(-100.3488 25.6599)', 'Calle Entrega 4, San Pedro / Valle', 'asignado', 'despejado', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Poke Bar Del Valle", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 73.5, 'MXN', now() - interval '2 minutes'),
  ('24878880-f0f7-5243-b6ca-05f2b40ba769', 2, 'RAPPI-san-05', '021e73d2-d111-5b69-874b-56bbb56c3119', 'SRID=4326;POINT(-100.3523 25.6509)', 'Pizzeria Napolitana SP, San Pedro / Valle', 'SRID=4326;POINT(-100.3653 25.6584)', 'Calle Entrega 5, San Pedro / Valle', 'asignado', 'despejado', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizzeria Napolitana SP", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 78.0, 'MXN', now() - interval '2 minutes'),
  ('3a2c4c3d-dc9f-591a-9daf-64e7897c50cb', 3, 'DIDI-san-06', 'f345e6a7-b333-53d2-867e-1a66f3644c80', 'SRID=4326;POINT(-100.3482 25.6597)', 'La Postrería Valle, San Pedro / Valle', 'SRID=4326;POINT(-100.3481 25.6447)', 'Calle Entrega 6, San Pedro / Valle', 'buscando', 'despejado', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "La Postrería Valle", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 82.5, 'MXN', now() - interval '2 minutes'),
  ('a33308ed-96f9-5e11-993c-580946fa87dd', 1, 'UBER-san-07', 'c459d89a-3292-5bc4-adc4-85c930d2fe56', 'SRID=4326;POINT(-100.3556 25.666)', 'Steak House San Pedro, San Pedro / Valle', 'SRID=4326;POINT(-100.3427 25.6736)', 'Calle Entrega 7, San Pedro / Valle', 'buscando', 'despejado', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Steak House San Pedro", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 87.0, 'MXN', now() - interval '2 minutes'),
  ('147b9457-1d78-5ea9-9d82-06b8b8db85d0', 2, 'RAPPI-san-08', 'f398b049-f10e-50ea-ba4f-14ea29266783', 'SRID=4326;POINT(-100.3636 25.6606)', 'Green Bowl Vasconcelos, San Pedro / Valle', 'SRID=4326;POINT(-100.3767 25.6679)', 'Calle Entrega 8, San Pedro / Valle', 'buscando', 'despejado', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Green Bowl Vasconcelos", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 91.5, 'MXN', now() - interval '2 minutes'),
  ('0314ac06-8dfe-548c-b74b-95c9b2204fef', 3, 'DIDI-san-09', 'd0b71226-6c66-516f-b2f7-674487c971dc', 'SRID=4326;POINT(-100.3605 25.6514)', 'Poke Bar Del Valle, San Pedro / Valle', 'SRID=4326;POINT(-100.3602 25.6364)', 'Calle Entrega 9, San Pedro / Valle', 'buscando', 'despejado', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Poke Bar Del Valle", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 96.0, 'MXN', now() - interval '2 minutes'),
  ('c14cc69f-061e-5c6e-897e-511ed6e8ecfd', 1, 'UBER-san-10', 'afab2c2c-8f1d-5f9d-a531-dff8383ba158', 'SRID=4326;POINT(-100.3508 25.6519)', 'Pizzeria Napolitana SP, San Pedro / Valle', 'SRID=4326;POINT(-100.338 25.6597)', 'Calle Entrega 10, San Pedro / Valle', 'buscando', 'despejado', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizzeria Napolitana SP", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 100.5, 'MXN', now() - interval '2 minutes'),
  ('a829c773-f659-5c6b-b6cc-6e47cd7139eb', 1, 'UBER-cum-01', 'c33443ab-6a47-5b88-94f9-c03f0aae4b6d', 'SRID=4326;POINT(-100.368 25.718)', 'Burger Lab Cumbres, Cumbres', 'SRID=4326;POINT(-100.3548 25.7252)', 'Calle Entrega 1, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burger Lab Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '2 minutes'),
  ('d5347188-aae9-57cb-bbb0-792a468132a3', 2, 'RAPPI-cum-02', 'ab78ad4d-79d1-57ba-8e9c-b4aa0d04f4ef', 'SRID=4326;POINT(-100.3739 25.7257)', 'Tacos Leones Cumbres, Cumbres', 'SRID=4326;POINT(-100.3868 25.7334)', 'Calle Entrega 2, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos Leones Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '2 minutes'),
  ('85a5b744-93d2-50e4-8946-09a6201273ca', 3, 'DIDI-cum-03', 'd79024be-104b-5028-aac2-6ef0f2424889', 'SRID=4326;POINT(-100.3829 25.7221)', 'Sushi Master Paseo, Cumbres', 'SRID=4326;POINT(-100.3831 25.7071)', 'Calle Entrega 3, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Master Paseo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '2 minutes'),
  ('d3f27c6c-90b5-5b3f-9afd-b56e485fa99d', 1, 'UBER-cum-04', 'ed9ce1ae-2ccc-526a-93dc-6e4730bc97db', 'SRID=4326;POINT(-100.3818 25.7125)', 'Tortas Bravas Cumbres, Cumbres', 'SRID=4326;POINT(-100.3688 25.7199)', 'Calle Entrega 4, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tortas Bravas Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '2 minutes'),
  ('c82cf7cf-03d8-5772-86c8-43a872e55630', 2, 'RAPPI-cum-05', 'be7bf195-d495-55cf-be94-df3d0ebb8875', 'SRID=4326;POINT(-100.3723 25.7109)', 'Alitas & Ribs Cumbres, Cumbres', 'SRID=4326;POINT(-100.3853 25.7184)', 'Calle Entrega 5, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Alitas & Ribs Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '2 minutes'),
  ('561cd1d3-8934-541b-a476-a3b866322a38', 3, 'DIDI-cum-06', 'd6334f88-8f33-5b59-a7ae-fea47db25aea', 'SRID=4326;POINT(-100.3682 25.7197)', 'Burger Lab Cumbres, Cumbres', 'SRID=4326;POINT(-100.3681 25.7047)', 'Calle Entrega 6, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burger Lab Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '2 minutes'),
  ('627ec430-10fa-51e7-9cc8-4c584f801b16', 1, 'UBER-cum-07', '2a0ef942-df89-5a5b-9780-37c50efa9814', 'SRID=4326;POINT(-100.3756 25.726)', 'Tacos Leones Cumbres, Cumbres', 'SRID=4326;POINT(-100.3627 25.7336)', 'Calle Entrega 7, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos Leones Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '2 minutes'),
  ('d4bdc4cd-a042-5047-bc8b-3d616442a81d', 2, 'RAPPI-cum-08', '9b3d1e11-11de-5e5c-b9b0-7df30b29f352', 'SRID=4326;POINT(-100.3836 25.7206)', 'Sushi Master Paseo, Cumbres', 'SRID=4326;POINT(-100.3967 25.7279)', 'Calle Entrega 8, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Master Paseo", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '2 minutes'),
  ('336eb33d-043e-5ff7-af9b-ccf3ced47337', 3, 'DIDI-cum-09', 'e4551e53-f932-577c-ba23-ba6483cb0fdd', 'SRID=4326;POINT(-100.3805 25.7114)', 'Tortas Bravas Cumbres, Cumbres', 'SRID=4326;POINT(-100.3802 25.6964)', 'Calle Entrega 9, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tortas Bravas Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '2 minutes'),
  ('91ea0466-8621-5ae8-a89e-b7b85a3251a3', 1, 'UBER-cum-10', '35442812-0bcd-5a96-8f2b-8dbc059000d9', 'SRID=4326;POINT(-100.3708 25.7119)', 'Alitas & Ribs Cumbres, Cumbres', 'SRID=4326;POINT(-100.358 25.7197)', 'Calle Entrega 10, Cumbres', 'buscando', 'despejado', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Alitas & Ribs Cumbres", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '2 minutes'),
  ('e1e4b463-d4ab-5e45-b04a-be4977f5361a', 1, 'UBER-tec-01', '408d6ac1-9179-56a2-9184-eb1d9ab28e1d', 'SRID=4326;POINT(-100.281 25.651)', 'Chilaquiles del Tec, Tec / Contry', 'SRID=4326;POINT(-100.2678 25.6582)', 'Calle Entrega 1, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Chilaquiles del Tec", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '2 minutes'),
  ('e3a3957a-b181-5223-852b-8b7aeef21ee2', 2, 'RAPPI-tec-02', '2c0ccdd0-a357-5ce5-97f5-a2a29e956fb3', 'SRID=4326;POINT(-100.2869 25.6587)', 'Burritos Garza Sada, Tec / Contry', 'SRID=4326;POINT(-100.2998 25.6664)', 'Calle Entrega 2, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Burritos Garza Sada", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '2 minutes'),
  ('0c791fe6-846a-5440-b78f-e99d20faa438', 3, 'DIDI-tec-03', 'e32bd79e-4e9c-5e71-b162-37868794420d', 'SRID=4326;POINT(-100.2959 25.6551)', 'Bao Bao Contry, Tec / Contry', 'SRID=4326;POINT(-100.2961 25.6401)', 'Calle Entrega 3, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bao Bao Contry", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '2 minutes'),
  ('edfa5b2a-47f5-511a-96bc-f84ce9d902a3', 1, 'UBER-tec-04', '5f842c2f-b6b4-56d9-bf5f-8a15fec6d1c7', 'SRID=4326;POINT(-100.2948 25.6455)', 'Pizza Express Alfonso Reyes, Tec / Contry', 'SRID=4326;POINT(-100.2818 25.6529)', 'Calle Entrega 4, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizza Express Alfonso Reyes", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '2 minutes'),
  ('7d04591d-01a3-5c9d-ad71-050e18516e75', 2, 'RAPPI-tec-05', '22eb0adb-4d8e-5229-9208-a921b7252c1c', 'SRID=4326;POINT(-100.2853 25.6439)', 'Bowl Fresco Tec, Tec / Contry', 'SRID=4326;POINT(-100.2983 25.6514)', 'Calle Entrega 5, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bowl Fresco Tec", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '2 minutes'),
  ('a8fb8894-d776-5f32-9964-50056a2619cb', 3, 'DIDI-tec-06', '2f05489f-eabf-5044-bc95-ab50bfd1805e', 'SRID=4326;POINT(-100.2812 25.6527)', 'Chilaquiles del Tec, Tec / Contry', 'SRID=4326;POINT(-100.2811 25.6377)', 'Calle Entrega 6, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Chilaquiles del Tec", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '2 minutes'),
  ('c84f260b-f115-5a60-8d8e-93bb5e948061', 1, 'UBER-tec-07', '86554df5-02cc-55ae-9460-47c38d02dcad', 'SRID=4326;POINT(-100.2886 25.659)', 'Burritos Garza Sada, Tec / Contry', 'SRID=4326;POINT(-100.2757 25.6666)', 'Calle Entrega 7, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Burritos Garza Sada", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '2 minutes'),
  ('df060571-bf86-5b95-a60e-f9eeb0845c42', 2, 'RAPPI-tec-08', 'befe1909-5faa-5814-893e-0e1d6b68dfb2', 'SRID=4326;POINT(-100.2966 25.6536)', 'Bao Bao Contry, Tec / Contry', 'SRID=4326;POINT(-100.3097 25.6609)', 'Calle Entrega 8, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bao Bao Contry", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '2 minutes'),
  ('6cff037f-bc26-5ba0-ba8c-8fd87d0887a6', 3, 'DIDI-tec-09', '532be45a-f8ef-5d90-9c35-d661857a1e8b', 'SRID=4326;POINT(-100.2935 25.6444)', 'Pizza Express Alfonso Reyes, Tec / Contry', 'SRID=4326;POINT(-100.2932 25.6294)', 'Calle Entrega 9, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizza Express Alfonso Reyes", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '2 minutes'),
  ('db40c1e9-fa3a-5c91-b7f9-465285470aa4', 1, 'UBER-tec-10', '1c7a5a8c-8181-55e2-902d-de7579abddd6', 'SRID=4326;POINT(-100.2838 25.6449)', 'Bowl Fresco Tec, Tec / Contry', 'SRID=4326;POINT(-100.271 25.6527)', 'Calle Entrega 10, Tec / Contry', 'buscando', 'despejado', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bowl Fresco Tec", "limite_entrega_en": "2026-09-13T06:17:17.586210+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '2 minutes')
ON CONFLICT (id) DO NOTHING;

-- 9. viaje_pedidos (12 entregados + 3 a bordo con orden consecutivo 1..15)
INSERT INTO viaje_pedidos (id, viaje_id, pedido_id, orden, agregado_en) VALUES
  ('e9918eaf-2196-5c3f-8f7d-734dc94afe07', 'd1c74636-8398-521d-907f-e5e9c40c498f', 'ce2a38ca-bfe7-58b5-82ea-8eebac6c5270', 1, now() - interval '15 minutes'),
  ('0b56b3e2-b831-5825-bf22-bea96a300f39', 'd1c74636-8398-521d-907f-e5e9c40c498f', 'e80f5077-c3c3-58e4-9526-64509deb735d', 2, now() - interval '15 minutes'),
  ('e3d7a1cf-5cd7-5950-8c4b-4b90da19f987', 'd1c74636-8398-521d-907f-e5e9c40c498f', 'a8da2c97-5410-5145-af89-f06f17236240', 3, now() - interval '15 minutes'),
  ('5bf5032a-ecdc-5a65-a6ad-adc3d2c6edb4', 'd1c74636-8398-521d-907f-e5e9c40c498f', '3aee675d-283b-5808-8a76-d1dd28a01ead', 4, now() - interval '15 minutes'),
  ('624b392a-bc65-5eb1-ab13-5077597524e5', 'd1c74636-8398-521d-907f-e5e9c40c498f', '79f6b6d4-ba45-5e70-b935-4d7b8244dbb6', 5, now() - interval '15 minutes'),
  ('9c0b4432-a8d8-5da3-8bd4-2e9ca4fc5d03', 'd1c74636-8398-521d-907f-e5e9c40c498f', '9ee880d6-7b56-5954-adf9-c397b064c4c1', 6, now() - interval '15 minutes'),
  ('048d81dd-0354-5694-b8b8-02cdeba54fac', 'd1c74636-8398-521d-907f-e5e9c40c498f', '96551310-48cc-54bf-ba6e-e7bf9c680036', 7, now() - interval '15 minutes'),
  ('cb9c01c2-186f-5a94-b90c-11f050b90cea', 'd1c74636-8398-521d-907f-e5e9c40c498f', '70609dc0-57b2-55b3-b828-341fb7a9ef8b', 8, now() - interval '15 minutes'),
  ('4f905172-8149-5d27-b385-b2de4e01d0a6', 'd1c74636-8398-521d-907f-e5e9c40c498f', '2aacb4cf-81ec-515f-91d8-12179af7ebeb', 9, now() - interval '15 minutes'),
  ('137a6c01-ad45-5a0e-a650-571d2e4b786a', 'd1c74636-8398-521d-907f-e5e9c40c498f', '1e01906e-7b4e-592e-88c5-ad0a5341aa72', 10, now() - interval '15 minutes'),
  ('020bc4c9-0252-56d5-ad80-7aa7b3de21a3', 'd1c74636-8398-521d-907f-e5e9c40c498f', '247fba58-b7f4-5fb4-bfd3-980186b679fa', 11, now() - interval '15 minutes'),
  ('ae196190-4173-546a-a02d-b256515ab79e', 'd1c74636-8398-521d-907f-e5e9c40c498f', '10dc7f35-94b2-5fac-89e1-7c04c28120e5', 12, now() - interval '15 minutes'),
  ('21f76823-af81-52aa-b9a3-7b4d230fd726', 'd1c74636-8398-521d-907f-e5e9c40c498f', '03e1181a-0c8a-5a40-924b-549ad8773160', 13, now() - interval '15 minutes'),
  ('f1239c8a-c6bd-53b3-9be3-77089d5887df', 'd1c74636-8398-521d-907f-e5e9c40c498f', '4126548f-fb13-5180-a17f-dfc80c95cad4', 14, now() - interval '15 minutes'),
  ('bb24ecdc-240b-5f35-9ebc-89c1509a9c98', 'd1c74636-8398-521d-907f-e5e9c40c498f', '24878880-f0f7-5243-b6ca-05f2b40ba769', 15, now() - interval '15 minutes')
ON CONFLICT (viaje_id, pedido_id) DO UPDATE SET orden = EXCLUDED.orden;

-- 10. difusiones_pedido (para los pedidos en buscando con columnas exactas de Supabase)
INSERT INTO difusiones_pedido (id, pedido_id, ronda, radio_metros, total_ofertas, clima, iniciada_en) VALUES
  ('1bb366ad-3732-5ee2-8e4d-4c1ee6f02ae5', '3a2c4c3d-dc9f-591a-9daf-64e7897c50cb', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('e8b1a3e0-5947-5705-8f7a-43c083f00cba', 'a33308ed-96f9-5e11-993c-580946fa87dd', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('e9435534-0538-5797-b6df-743ef6009d2a', '147b9457-1d78-5ea9-9d82-06b8b8db85d0', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('b50d5ccd-a18f-5000-bd3b-5a567358c4ad', '0314ac06-8dfe-548c-b74b-95c9b2204fef', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('b40f9d08-07da-5f62-a52e-ae6ba7e13e3f', 'c14cc69f-061e-5c6e-897e-511ed6e8ecfd', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('c9cfff1c-5805-58cc-94ed-c90ba1ad2334', 'a829c773-f659-5c6b-b6cc-6e47cd7139eb', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('2ada6de0-3e86-5020-9b70-364d1b7333a5', 'd5347188-aae9-57cb-bbb0-792a468132a3', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('22305ab9-6772-5d72-b40a-14a583e43399', '85a5b744-93d2-50e4-8946-09a6201273ca', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('955f66b9-ed2d-59ab-90a3-78b07b483630', 'd3f27c6c-90b5-5b3f-9afd-b56e485fa99d', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('33f38460-618d-5177-a686-62f34314e117', 'c82cf7cf-03d8-5772-86c8-43a872e55630', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('b393c820-1b0a-5139-9206-93eb1f5e574a', '561cd1d3-8934-541b-a476-a3b866322a38', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('f05cf3a3-951e-517a-8f0f-d95da658cf5f', '627ec430-10fa-51e7-9cc8-4c584f801b16', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('0848cc7d-4d84-531d-ab3f-d95a7a253073', 'd4bdc4cd-a042-5047-bc8b-3d616442a81d', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('22fd08db-89fd-533b-9988-c4577999fa30', '336eb33d-043e-5ff7-af9b-ccf3ced47337', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('75bcdfae-a56a-5470-8d6a-1667f41aa5c5', '91ea0466-8621-5ae8-a89e-b7b85a3251a3', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('7dd20477-f573-5e3d-af4e-89e25df15882', 'e1e4b463-d4ab-5e45-b04a-be4977f5361a', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('79d02468-456b-5ad3-a112-ef5ff49027e7', 'e3a3957a-b181-5223-852b-8b7aeef21ee2', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('10391e42-219c-577b-a0bb-3d13a5a10d93', '0c791fe6-846a-5440-b78f-e99d20faa438', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('3ecdb4b3-e149-5fc6-a4ae-3cb8320d5aa8', 'edfa5b2a-47f5-511a-96bc-f84ce9d902a3', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('7dfd2b98-8185-50a6-a5ee-859dfb8e225e', '7d04591d-01a3-5c9d-ad71-050e18516e75', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('8c146532-0430-51b8-bb47-2fbd557df2cb', 'a8fb8894-d776-5f32-9964-50056a2619cb', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('fd92a3c2-f5c6-5048-b12f-50c4c6b9ad2a', 'c84f260b-f115-5a60-8d8e-93bb5e948061', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('4ffe1e1b-bcb3-5c0f-b045-8934cb166241', 'df060571-bf86-5b95-a60e-f9eeb0845c42', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('b045c87d-5793-5afe-9776-879e335f9e65', '6cff037f-bc26-5ba0-ba8c-8fd87d0887a6', 1, 1500, 1, 'despejado', now() - interval '3 minutes'),
  ('42d8c7cc-f6e8-5c16-b14b-072f17b1764c', 'db40c1e9-fa3a-5c91-b7f9-465285470aa4', 1, 1500, 1, 'despejado', now() - interval '3 minutes')
ON CONFLICT (id) DO NOTHING;

-- 11. ofertas_pedido (8 ofertas pendientes con expira_en > now)
INSERT INTO ofertas_pedido (id, pedido_id, repartidor_id, viaje_id, ronda, radio_metros, desvio_estimado_metros, expira_en, clima, estado, ofrecida_en) VALUES
  ('f0be2191-1803-5dec-9f09-479c0da5013d', '3a2c4c3d-dc9f-591a-9daf-64e7897c50cb', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 1, 1500, 450.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('e9dba22d-cacb-57f5-8ebf-e0bba26b8534', 'a33308ed-96f9-5e11-993c-580946fa87dd', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 1, 1500, 680.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('9a2f96f0-dbe5-589c-8955-e85ec4cc3b24', '147b9457-1d78-5ea9-9d82-06b8b8db85d0', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 1, 1500, 890.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('e701e272-295a-5790-a598-5bcce0094e96', '0314ac06-8dfe-548c-b74b-95c9b2204fef', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 2, 3000, 1450.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('f23aeb05-4b82-564e-ac1c-0cb660a3c3dd', 'c14cc69f-061e-5c6e-897e-511ed6e8ecfd', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 2, 3000, 1850.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('73e4f791-afa7-508e-9226-f6932977c169', 'a829c773-f659-5c6b-b6cc-6e47cd7139eb', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 2, 3000, 2200.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('be15707d-654b-57f7-b898-7f4ab7c49d75', 'd5347188-aae9-57cb-bbb0-792a468132a3', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 3, 5000, 3100.0, now() + interval '60 seconds', 'despejado', 'pendiente', now()),
  ('61688b13-47de-5c1f-bdd1-4bd8c2b91d42', '85a5b744-93d2-50e4-8946-09a6201273ca', 'e9128a20-84fd-55e4-bd02-7b0d09f88010', 'd1c74636-8398-521d-907f-e5e9c40c498f', 3, 5000, 4200.0, now() + interval '60 seconds', 'despejado', 'pendiente', now())
ON CONFLICT (id) DO NOTHING;

COMMIT;