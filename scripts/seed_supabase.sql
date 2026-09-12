-- ====================================================================
-- VYGO · PLAN DE INYECCIÓN DE DATOS V2.0 (12 de septiembre de 2026)
-- Reconciliado con Supabase ihmadvmoenkxanoxrwcy (11 tablas)
-- ====================================================================
BEGIN;

-- 1. Catalogo de Apps (3)
INSERT INTO apps (id, nombre) VALUES
  (1, 'uber'),
  (2, 'rappi'),
  (3, 'didi')
ON CONFLICT (id) DO NOTHING;

-- 2. Usuarios (1 repartidor + 30 clientes)
INSERT INTO usuarios (id, nombre, email, telefono) VALUES
  ('usr-rep-demo-01', 'Carlos Repartidor Demo', 'carlos.demo@vygo.mx', '8110000001'),
  ('usr-cli-01', 'Cliente Ficticio 1', 'cliente1@ejemplo.com', '8110000001'),
  ('usr-cli-02', 'Cliente Ficticio 2', 'cliente2@ejemplo.com', '8110000002'),
  ('usr-cli-03', 'Cliente Ficticio 3', 'cliente3@ejemplo.com', '8110000003'),
  ('usr-cli-04', 'Cliente Ficticio 4', 'cliente4@ejemplo.com', '8110000004'),
  ('usr-cli-05', 'Cliente Ficticio 5', 'cliente5@ejemplo.com', '8110000005'),
  ('usr-cli-06', 'Cliente Ficticio 6', 'cliente6@ejemplo.com', '8110000006'),
  ('usr-cli-07', 'Cliente Ficticio 7', 'cliente7@ejemplo.com', '8110000007'),
  ('usr-cli-08', 'Cliente Ficticio 8', 'cliente8@ejemplo.com', '8110000008'),
  ('usr-cli-09', 'Cliente Ficticio 9', 'cliente9@ejemplo.com', '8110000009'),
  ('usr-cli-10', 'Cliente Ficticio 10', 'cliente10@ejemplo.com', '8110000010'),
  ('usr-cli-11', 'Cliente Ficticio 11', 'cliente11@ejemplo.com', '8110000011'),
  ('usr-cli-12', 'Cliente Ficticio 12', 'cliente12@ejemplo.com', '8110000012'),
  ('usr-cli-13', 'Cliente Ficticio 13', 'cliente13@ejemplo.com', '8110000013'),
  ('usr-cli-14', 'Cliente Ficticio 14', 'cliente14@ejemplo.com', '8110000014'),
  ('usr-cli-15', 'Cliente Ficticio 15', 'cliente15@ejemplo.com', '8110000015'),
  ('usr-cli-16', 'Cliente Ficticio 16', 'cliente16@ejemplo.com', '8110000016'),
  ('usr-cli-17', 'Cliente Ficticio 17', 'cliente17@ejemplo.com', '8110000017'),
  ('usr-cli-18', 'Cliente Ficticio 18', 'cliente18@ejemplo.com', '8110000018'),
  ('usr-cli-19', 'Cliente Ficticio 19', 'cliente19@ejemplo.com', '8110000019'),
  ('usr-cli-20', 'Cliente Ficticio 20', 'cliente20@ejemplo.com', '8110000020'),
  ('usr-cli-21', 'Cliente Ficticio 21', 'cliente21@ejemplo.com', '8110000021'),
  ('usr-cli-22', 'Cliente Ficticio 22', 'cliente22@ejemplo.com', '8110000022'),
  ('usr-cli-23', 'Cliente Ficticio 23', 'cliente23@ejemplo.com', '8110000023'),
  ('usr-cli-24', 'Cliente Ficticio 24', 'cliente24@ejemplo.com', '8110000024'),
  ('usr-cli-25', 'Cliente Ficticio 25', 'cliente25@ejemplo.com', '8110000025'),
  ('usr-cli-26', 'Cliente Ficticio 26', 'cliente26@ejemplo.com', '8110000026'),
  ('usr-cli-27', 'Cliente Ficticio 27', 'cliente27@ejemplo.com', '8110000027'),
  ('usr-cli-28', 'Cliente Ficticio 28', 'cliente28@ejemplo.com', '8110000028'),
  ('usr-cli-29', 'Cliente Ficticio 29', 'cliente29@ejemplo.com', '8110000029'),
  ('usr-cli-30', 'Cliente Ficticio 30', 'cliente30@ejemplo.com', '8110000030')
ON CONFLICT (id) DO NOTHING;

-- 3. Repartidor de Demo
INSERT INTO repartidores (id, usuario_id, app_id, vehiculo, disponible, rating) VALUES
  ('rep-demo-01', 'usr-rep-demo-01', 1, 'moto', true, 4.95)
ON CONFLICT (id) DO UPDATE SET disponible = true, vehiculo = 'moto';

-- 4. Conexiones de plataforma activas (3)
INSERT INTO platform_connections (user_id, platform, is_active) VALUES
  ('usr-rep-demo-01', 'uber', true),
  ('usr-rep-demo-01', 'rappi', true),
  ('usr-rep-demo-01', 'didi', true)
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
  ('usr-rep-demo-01', 25.6714, -100.3094, now())
ON CONFLICT (user_id) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, updated_at = now();

-- 7. Viaje activo iniciado hace 90 min
INSERT INTO viajes_repartidor (id, repartidor_id, estado, iniciado_en, origen_actual) VALUES
  ('viaje-demo-01', 'rep-demo-01', 'activo', now() - interval '90 minutes', st_setsrid(st_makepoint(-100.3094, 25.6714), 4326)::geography)
ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado, origen_actual = EXCLUDED.origen_actual;

-- 8. Pedidos con contexto JSONB completo (12 entregados, 3 asignados, 25 buscando)
INSERT INTO pedidos (id, app_id, id_externo, cliente_id, origen, origen_direccion, destino, destino_direccion, estado, clima, contexto, precio, moneda, creado_en) VALUES
  ('ped-cen-01', 1, 'UBER-cen-01', 'usr-cli-01', st_setsrid(st_makepoint(-100.3014, 25.6714), 4326)::geography, 'Sushi Roll Centro, Centro', st_setsrid(st_makepoint(-100.2882, 25.6786), 4326)::geography, 'Calle Entrega 1, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Roll Centro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-02', 2, 'RAPPI-cen-02', 'usr-cli-02', st_setsrid(st_makepoint(-100.3073, 25.6791), 4326)::geography, 'Tacos El Primo, Centro', st_setsrid(st_makepoint(-100.3202, 25.6868), 4326)::geography, 'Calle Entrega 2, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos El Primo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-03', 3, 'DIDI-cen-03', 'usr-cli-03', st_setsrid(st_makepoint(-100.3163, 25.6755), 4326)::geography, 'La Bella Italia Centro, Centro', st_setsrid(st_makepoint(-100.3165, 25.6605), 4326)::geography, 'Calle Entrega 3, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "La Bella Italia Centro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-04', 1, 'UBER-cen-04', 'usr-cli-04', st_setsrid(st_makepoint(-100.3152, 25.6659), 4326)::geography, 'Burgers MTY Macroplaza, Centro', st_setsrid(st_makepoint(-100.3022, 25.6733), 4326)::geography, 'Calle Entrega 4, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burgers MTY Macroplaza", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-05', 2, 'RAPPI-cen-05', 'usr-cli-05', st_setsrid(st_makepoint(-100.3057, 25.6643), 4326)::geography, 'Chilaquiles Barrio Antiguo, Centro', st_setsrid(st_makepoint(-100.3187, 25.6718), 4326)::geography, 'Calle Entrega 5, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Chilaquiles Barrio Antiguo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-06', 3, 'DIDI-cen-06', 'usr-cli-06', st_setsrid(st_makepoint(-100.3016, 25.6731), 4326)::geography, 'Sushi Roll Centro, Centro', st_setsrid(st_makepoint(-100.3015, 25.6581), 4326)::geography, 'Calle Entrega 6, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Roll Centro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-07', 1, 'UBER-cen-07', 'usr-cli-07', st_setsrid(st_makepoint(-100.309, 25.6794), 4326)::geography, 'Tacos El Primo, Centro', st_setsrid(st_makepoint(-100.2961, 25.687), 4326)::geography, 'Calle Entrega 7, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos El Primo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-08', 2, 'RAPPI-cen-08', 'usr-cli-08', st_setsrid(st_makepoint(-100.317, 25.674), 4326)::geography, 'La Bella Italia Centro, Centro', st_setsrid(st_makepoint(-100.3301, 25.6813), 4326)::geography, 'Calle Entrega 8, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "La Bella Italia Centro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-09', 3, 'DIDI-cen-09', 'usr-cli-09', st_setsrid(st_makepoint(-100.3139, 25.6648), 4326)::geography, 'Burgers MTY Macroplaza, Centro', st_setsrid(st_makepoint(-100.3136, 25.6498), 4326)::geography, 'Calle Entrega 9, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burgers MTY Macroplaza", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '30 minutes'),
  ('ped-cen-10', 1, 'UBER-cen-10', 'usr-cli-10', st_setsrid(st_makepoint(-100.3042, 25.6653), 4326)::geography, 'Chilaquiles Barrio Antiguo, Centro', st_setsrid(st_makepoint(-100.2914, 25.6731), 4326)::geography, 'Calle Entrega 10, Centro', 'entregado', 'normal', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "centro", "propina_esperada_mxn": 0.0, "comercio_nombre": "Chilaquiles Barrio Antiguo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '30 minutes'),
  ('ped-san-01', 1, 'UBER-san-01', 'usr-cli-11', st_setsrid(st_makepoint(-100.348, 25.658), 4326)::geography, 'La Postrería Valle, San Pedro / Valle', st_setsrid(st_makepoint(-100.3348, 25.6652), 4326)::geography, 'Calle Entrega 1, San Pedro / Valle', 'entregado', 'normal', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "La Postrería Valle", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 60.0, 'MXN', now() - interval '30 minutes'),
  ('ped-san-02', 2, 'RAPPI-san-02', 'usr-cli-12', st_setsrid(st_makepoint(-100.3539, 25.6657), 4326)::geography, 'Steak House San Pedro, San Pedro / Valle', st_setsrid(st_makepoint(-100.3668, 25.6734), 4326)::geography, 'Calle Entrega 2, San Pedro / Valle', 'entregado', 'normal', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Steak House San Pedro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 64.5, 'MXN', now() - interval '30 minutes'),
  ('ped-san-03', 3, 'DIDI-san-03', 'usr-cli-13', st_setsrid(st_makepoint(-100.3629, 25.6621), 4326)::geography, 'Green Bowl Vasconcelos, San Pedro / Valle', st_setsrid(st_makepoint(-100.3631, 25.6471), 4326)::geography, 'Calle Entrega 3, San Pedro / Valle', 'asignado', 'normal', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Green Bowl Vasconcelos", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 69.0, 'MXN', now() - interval '2 minutes'),
  ('ped-san-04', 1, 'UBER-san-04', 'usr-cli-14', st_setsrid(st_makepoint(-100.3618, 25.6525), 4326)::geography, 'Poke Bar Del Valle, San Pedro / Valle', st_setsrid(st_makepoint(-100.3488, 25.6599), 4326)::geography, 'Calle Entrega 4, San Pedro / Valle', 'asignado', 'normal', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Poke Bar Del Valle", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 73.5, 'MXN', now() - interval '2 minutes'),
  ('ped-san-05', 2, 'RAPPI-san-05', 'usr-cli-15', st_setsrid(st_makepoint(-100.3523, 25.6509), 4326)::geography, 'Pizzeria Napolitana SP, San Pedro / Valle', st_setsrid(st_makepoint(-100.3653, 25.6584), 4326)::geography, 'Calle Entrega 5, San Pedro / Valle', 'asignado', 'normal', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizzeria Napolitana SP", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 78.0, 'MXN', now() - interval '2 minutes'),
  ('ped-san-06', 3, 'DIDI-san-06', 'usr-cli-16', st_setsrid(st_makepoint(-100.3482, 25.6597), 4326)::geography, 'La Postrería Valle, San Pedro / Valle', st_setsrid(st_makepoint(-100.3481, 25.6447), 4326)::geography, 'Calle Entrega 6, San Pedro / Valle', 'buscando', 'normal', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "La Postrería Valle", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 82.5, 'MXN', now() - interval '2 minutes'),
  ('ped-san-07', 1, 'UBER-san-07', 'usr-cli-17', st_setsrid(st_makepoint(-100.3556, 25.666), 4326)::geography, 'Steak House San Pedro, San Pedro / Valle', st_setsrid(st_makepoint(-100.3427, 25.6736), 4326)::geography, 'Calle Entrega 7, San Pedro / Valle', 'buscando', 'normal', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Steak House San Pedro", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 87.0, 'MXN', now() - interval '2 minutes'),
  ('ped-san-08', 2, 'RAPPI-san-08', 'usr-cli-18', st_setsrid(st_makepoint(-100.3636, 25.6606), 4326)::geography, 'Green Bowl Vasconcelos, San Pedro / Valle', st_setsrid(st_makepoint(-100.3767, 25.6679), 4326)::geography, 'Calle Entrega 8, San Pedro / Valle', 'buscando', 'normal', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Green Bowl Vasconcelos", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 91.5, 'MXN', now() - interval '2 minutes'),
  ('ped-san-09', 3, 'DIDI-san-09', 'usr-cli-19', st_setsrid(st_makepoint(-100.3605, 25.6514), 4326)::geography, 'Poke Bar Del Valle, San Pedro / Valle', st_setsrid(st_makepoint(-100.3602, 25.6364), 4326)::geography, 'Calle Entrega 9, San Pedro / Valle', 'buscando', 'normal', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Poke Bar Del Valle", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 96.0, 'MXN', now() - interval '2 minutes'),
  ('ped-san-10', 1, 'UBER-san-10', 'usr-cli-20', st_setsrid(st_makepoint(-100.3508, 25.6519), 4326)::geography, 'Pizzeria Napolitana SP, San Pedro / Valle', st_setsrid(st_makepoint(-100.338, 25.6597), 4326)::geography, 'Calle Entrega 10, San Pedro / Valle', 'buscando', 'normal', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "san_pedro", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizzeria Napolitana SP", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 100.5, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-01', 1, 'UBER-cum-01', 'usr-cli-21', st_setsrid(st_makepoint(-100.368, 25.718), 4326)::geography, 'Burger Lab Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3548, 25.7252), 4326)::geography, 'Calle Entrega 1, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burger Lab Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-02', 2, 'RAPPI-cum-02', 'usr-cli-22', st_setsrid(st_makepoint(-100.3739, 25.7257), 4326)::geography, 'Tacos Leones Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3868, 25.7334), 4326)::geography, 'Calle Entrega 2, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos Leones Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-03', 3, 'DIDI-cum-03', 'usr-cli-23', st_setsrid(st_makepoint(-100.3829, 25.7221), 4326)::geography, 'Sushi Master Paseo, Cumbres', st_setsrid(st_makepoint(-100.3831, 25.7071), 4326)::geography, 'Calle Entrega 3, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Master Paseo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-04', 1, 'UBER-cum-04', 'usr-cli-24', st_setsrid(st_makepoint(-100.3818, 25.7125), 4326)::geography, 'Tortas Bravas Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3688, 25.7199), 4326)::geography, 'Calle Entrega 4, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tortas Bravas Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-05', 2, 'RAPPI-cum-05', 'usr-cli-25', st_setsrid(st_makepoint(-100.3723, 25.7109), 4326)::geography, 'Alitas & Ribs Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3853, 25.7184), 4326)::geography, 'Calle Entrega 5, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Alitas & Ribs Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-06', 3, 'DIDI-cum-06', 'usr-cli-26', st_setsrid(st_makepoint(-100.3682, 25.7197), 4326)::geography, 'Burger Lab Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3681, 25.7047), 4326)::geography, 'Calle Entrega 6, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Burger Lab Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-07', 1, 'UBER-cum-07', 'usr-cli-27', st_setsrid(st_makepoint(-100.3756, 25.726), 4326)::geography, 'Tacos Leones Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3627, 25.7336), 4326)::geography, 'Calle Entrega 7, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tacos Leones Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-08', 2, 'RAPPI-cum-08', 'usr-cli-28', st_setsrid(st_makepoint(-100.3836, 25.7206), 4326)::geography, 'Sushi Master Paseo, Cumbres', st_setsrid(st_makepoint(-100.3967, 25.7279), 4326)::geography, 'Calle Entrega 8, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Sushi Master Paseo", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-09', 3, 'DIDI-cum-09', 'usr-cli-29', st_setsrid(st_makepoint(-100.3805, 25.7114), 4326)::geography, 'Tortas Bravas Cumbres, Cumbres', st_setsrid(st_makepoint(-100.3802, 25.6964), 4326)::geography, 'Calle Entrega 9, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Tortas Bravas Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '2 minutes'),
  ('ped-cum-10', 1, 'UBER-cum-10', 'usr-cli-30', st_setsrid(st_makepoint(-100.3708, 25.7119), 4326)::geography, 'Alitas & Ribs Cumbres, Cumbres', st_setsrid(st_makepoint(-100.358, 25.7197), 4326)::geography, 'Calle Entrega 10, Cumbres', 'buscando', 'normal', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "cumbres", "propina_esperada_mxn": 0.0, "comercio_nombre": "Alitas & Ribs Cumbres", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-01', 1, 'UBER-tec-01', 'usr-cli-01', st_setsrid(st_makepoint(-100.281, 25.651), 4326)::geography, 'Chilaquiles del Tec, Tec / Contry', st_setsrid(st_makepoint(-100.2678, 25.6582), 4326)::geography, 'Calle Entrega 1, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 8, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Chilaquiles del Tec", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 45.0, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-02', 2, 'RAPPI-tec-02', 'usr-cli-02', st_setsrid(st_makepoint(-100.2869, 25.6587), 4326)::geography, 'Burritos Garza Sada, Tec / Contry', st_setsrid(st_makepoint(-100.2998, 25.6664), 4326)::geography, 'Calle Entrega 2, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 9, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Burritos Garza Sada", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 49.5, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-03', 3, 'DIDI-tec-03', 'usr-cli-03', st_setsrid(st_makepoint(-100.2959, 25.6551), 4326)::geography, 'Bao Bao Contry, Tec / Contry', st_setsrid(st_makepoint(-100.2961, 25.6401), 4326)::geography, 'Calle Entrega 3, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 10, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bao Bao Contry", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 54.0, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-04', 1, 'UBER-tec-04', 'usr-cli-04', st_setsrid(st_makepoint(-100.2948, 25.6455), 4326)::geography, 'Pizza Express Alfonso Reyes, Tec / Contry', st_setsrid(st_makepoint(-100.2818, 25.6529), 4326)::geography, 'Calle Entrega 4, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 11, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizza Express Alfonso Reyes", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 58.5, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-05', 2, 'RAPPI-tec-05', 'usr-cli-05', st_setsrid(st_makepoint(-100.2853, 25.6439), 4326)::geography, 'Bowl Fresco Tec, Tec / Contry', st_setsrid(st_makepoint(-100.2983, 25.6514), 4326)::geography, 'Calle Entrega 5, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 12, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bowl Fresco Tec", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 63.0, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-06', 3, 'DIDI-tec-06', 'usr-cli-06', st_setsrid(st_makepoint(-100.2812, 25.6527), 4326)::geography, 'Chilaquiles del Tec, Tec / Contry', st_setsrid(st_makepoint(-100.2811, 25.6377), 4326)::geography, 'Calle Entrega 6, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 13, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Chilaquiles del Tec", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 67.5, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-07', 1, 'UBER-tec-07', 'usr-cli-07', st_setsrid(st_makepoint(-100.2886, 25.659), 4326)::geography, 'Burritos Garza Sada, Tec / Contry', st_setsrid(st_makepoint(-100.2757, 25.6666), 4326)::geography, 'Calle Entrega 7, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 14, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Burritos Garza Sada", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 72.0, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-08', 2, 'RAPPI-tec-08', 'usr-cli-08', st_setsrid(st_makepoint(-100.2966, 25.6536), 4326)::geography, 'Bao Bao Contry, Tec / Contry', st_setsrid(st_makepoint(-100.3097, 25.6609), 4326)::geography, 'Calle Entrega 8, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 15, "tipo_producto": "caliente", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bao Bao Contry", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 25.0}'::jsonb, 76.5, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-09', 3, 'DIDI-tec-09', 'usr-cli-09', st_setsrid(st_makepoint(-100.2935, 25.6444), 4326)::geography, 'Pizza Express Alfonso Reyes, Tec / Contry', st_setsrid(st_makepoint(-100.2932, 25.6294), 4326)::geography, 'Calle Entrega 9, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 16, "tipo_producto": "no_perecedero", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Pizza Express Alfonso Reyes", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00"}'::jsonb, 81.0, 'MXN', now() - interval '2 minutes'),
  ('ped-tec-10', 1, 'UBER-tec-10', 'usr-cli-10', st_setsrid(st_makepoint(-100.2838, 25.6449), 4326)::geography, 'Bowl Fresco Tec, Tec / Contry', st_setsrid(st_makepoint(-100.271, 25.6527), 4326)::geography, 'Calle Entrega 10, Tec / Contry', 'buscando', 'normal', '{"tiempo_preparacion_min": 17, "tipo_producto": "frio", "zona": "tec", "propina_esperada_mxn": 12.0, "comercio_nombre": "Bowl Fresco Tec", "limite_entrega_en": "2026-09-13T00:26:05.960405+00:00", "theta_frescura_min": 35.0}'::jsonb, 85.5, 'MXN', now() - interval '2 minutes')
ON CONFLICT (id) DO NOTHING;

-- 9. viaje_pedidos (12 entregados + 3 a bordo con orden consecutivo 1..15)
INSERT INTO viaje_pedidos (viaje_id, pedido_id, orden, agregado_en) VALUES
  ('viaje-demo-01', 'ped-cen-01', 1, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-02', 2, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-03', 3, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-04', 4, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-05', 5, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-06', 6, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-07', 7, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-08', 8, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-09', 9, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-cen-10', 10, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-san-01', 11, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-san-02', 12, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-san-03', 13, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-san-04', 14, now() - interval '15 minutes'),
  ('viaje-demo-01', 'ped-san-05', 15, now() - interval '15 minutes')
ON CONFLICT (viaje_id, pedido_id) DO UPDATE SET orden = EXCLUDED.orden;

-- 10. difusiones_pedido (para los pedidos en buscando)
INSERT INTO difusiones_pedido (id, pedido_id, ronda, creado_en) VALUES
  ('dif-ped-san-06', 'ped-san-06', 1, now()),
  ('dif-ped-san-07', 'ped-san-07', 1, now()),
  ('dif-ped-san-08', 'ped-san-08', 1, now()),
  ('dif-ped-san-09', 'ped-san-09', 1, now()),
  ('dif-ped-san-10', 'ped-san-10', 1, now()),
  ('dif-ped-cum-01', 'ped-cum-01', 1, now()),
  ('dif-ped-cum-02', 'ped-cum-02', 1, now()),
  ('dif-ped-cum-03', 'ped-cum-03', 1, now()),
  ('dif-ped-cum-04', 'ped-cum-04', 1, now()),
  ('dif-ped-cum-05', 'ped-cum-05', 1, now()),
  ('dif-ped-cum-06', 'ped-cum-06', 1, now()),
  ('dif-ped-cum-07', 'ped-cum-07', 1, now()),
  ('dif-ped-cum-08', 'ped-cum-08', 1, now()),
  ('dif-ped-cum-09', 'ped-cum-09', 1, now()),
  ('dif-ped-cum-10', 'ped-cum-10', 1, now()),
  ('dif-ped-tec-01', 'ped-tec-01', 1, now()),
  ('dif-ped-tec-02', 'ped-tec-02', 1, now()),
  ('dif-ped-tec-03', 'ped-tec-03', 1, now()),
  ('dif-ped-tec-04', 'ped-tec-04', 1, now()),
  ('dif-ped-tec-05', 'ped-tec-05', 1, now()),
  ('dif-ped-tec-06', 'ped-tec-06', 1, now()),
  ('dif-ped-tec-07', 'ped-tec-07', 1, now()),
  ('dif-ped-tec-08', 'ped-tec-08', 1, now()),
  ('dif-ped-tec-09', 'ped-tec-09', 1, now()),
  ('dif-ped-tec-10', 'ped-tec-10', 1, now())
ON CONFLICT (id) DO NOTHING;

-- 11. ofertas_pedido (8 ofertas pendientes con expira_en > now)
INSERT INTO ofertas_pedido (id, pedido_id, repartidor_id, viaje_id, ronda, radio_metros, desvio_estimado_metros, expira_en, clima, estado, ofrecida_en) VALUES
  ('oferta-demo-01', 'ped-san-06', 'rep-demo-01', 'viaje-demo-01', 1, 1500, 450.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-02', 'ped-san-07', 'rep-demo-01', 'viaje-demo-01', 1, 1500, 680.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-03', 'ped-san-08', 'rep-demo-01', 'viaje-demo-01', 1, 1500, 890.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-04', 'ped-san-09', 'rep-demo-01', 'viaje-demo-01', 2, 3000, 1450.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-05', 'ped-san-10', 'rep-demo-01', 'viaje-demo-01', 2, 3000, 1850.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-06', 'ped-cum-01', 'rep-demo-01', 'viaje-demo-01', 2, 3000, 2200.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-07', 'ped-cum-02', 'rep-demo-01', 'viaje-demo-01', 3, 5000, 3100.0, now() + interval '60 seconds', 'normal', 'pendiente', now()),
  ('oferta-demo-08', 'ped-cum-03', 'rep-demo-01', 'viaje-demo-01', 3, 5000, 4200.0, now() + interval '60 seconds', 'normal', 'pendiente', now())
ON CONFLICT (id) DO NOTHING;

COMMIT;