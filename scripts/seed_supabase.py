#!/usr/bin/env python3
"""
scripts/seed_supabase.py
Script de inyección de datos oficial para Supabase según el Contrato v2.0 (§6).
Puebla las 11 tablas en orden estricto de llaves foráneas:
  1. apps (3)
  2. usuarios (1 repartidor + 30 clientes)
  3. repartidores (1 moto demo)
  4. platform_connections (3 activas)
  5. configuracion (10 claves del sistema §3.5)
  6. ubicaciones_conductores (1 posición GPS en Monterrey ZM)
  7. viajes_repartidor (1 viaje activo)
  8. pedidos (40 pedidos en 4 clústeres: 12 entregados, 3 asignados, 25 buscando)
  9. viaje_pedidos (15 paradas con orden consecutivo 1..15)
  10. difusiones_pedido (25 rondas de búsqueda)
  11. ofertas_pedido (8 pendientes con expiración futura y anillos 1, 2, 3)

Ejecución:
  python scripts/seed_supabase.py             # Siembra local y corre las 7 verificaciones (§7)
  python scripts/seed_supabase.py --sql       # Genera y muestra el script SQL completo
  python scripts/seed_supabase.py --export sql # Guarda scripts/seed_supabase.sql
  python scripts/seed_supabase.py --verify    # Corre y valida las 7 reglas de verificación
"""

import sys
import os
import argparse
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import (
    obtener_db,
    generar_sql_inyeccion_completo,
    MockSupabaseDB,
)

def main():
    parser = argparse.ArgumentParser(description="VYGO - Inyector de datos para Supabase v2.0")
    parser.add_argument("--sql", action="store_true", help="Imprimir script SQL para Supabase SQL Editor")
    parser.add_argument("--export", type=str, choices=["sql", "json"], help="Exportar archivo de semilla a disco")
    parser.add_argument("--verify", action="store_true", help="Ejecutar las 7 verificaciones del Contrato v2.0 (§7)")
    args = parser.parse_args()

    db = obtener_db()

    if args.sql:
        sql = generar_sql_inyeccion_completo(db)
        print(sql)
        return

    if args.export == "sql":
        out_path = Path(__file__).resolve().parent / "seed_supabase.sql"
        sql = generar_sql_inyeccion_completo(db)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f"✅ Script SQL exportado exitosamente a {out_path} ({len(sql.splitlines())} líneas).")
        return

    print("=" * 75)
    print("  VYGO · PLAN DE INYECCIÓN DE DATOS V2.0 (12 de septiembre de 2026)")
    print("  Reconciliado con Supabase ihmadvmoenkxanoxrwcy (11 tablas)")
    print("=" * 75)

    # Población / resiembra
    db.inicializar_datos_semilla()
    print(f"✔ 1. apps:                  {len(db.apps)} filas (uber, rappi, didi)")
    print(f"✔ 2. usuarios:              {len(db.usuarios)} filas (1 repartidor + 30 clientes)")
    print(f"✔ 3. repartidores:          {len(db.repartidores)} fila (rep-demo-01, moto, disponible=True)")
    print(f"✔ 4. platform_connections:  {len(db.platform_connections)} conexiones activas")
    print(f"✔ 5. configuracion:         {len(db.configuracion)} claves de sistema (§3.5)")
    print(f"✔ 6. ubicaciones_conductores:{len(db.ubicaciones_conductores)} ping GPS activo en Monterrey")
    print(f"✔ 7. viajes_repartidor:     {len(db.viajes_repartidor)} viaje activo iniciado hace 90 min")
    print(f"✔ 8. pedidos:               {len(db.pedidos)} pedidos con contexto JSONB en 4 clústeres:")
    print("       - 12 entregados")
    print("       -  3 asignados (a bordo de viaje-demo-01)")
    print("       - 25 buscando (ofertables)")
    print(f"✔ 9. viaje_pedidos:         {len(db.viaje_pedidos)} paradas con orden consecutivo (1..15)")
    print(f"✔ 10. difusiones_pedido:    {len(db.difusiones_pedido)} rondas activas")
    print(f"✔ 11. ofertas_pedido:       {len(db.ofertas_pedido)} ofertas pendientes con expira_en > now")
    print("-" * 75)

    # 7 Verificaciones obligatorias (§7)
    print("Ejecutando las 7 Verificaciones Oficiales (§7):")
    v = db.verificar_estado_inyeccion()

    checks = [
        ("1. Ningún pedido sin contexto completo", v["v1_contexto_completo"], f"pedidos_sin_prep={v['totales']['pedidos_sin_prep']}"),
        ("2. Coordenadas dentro de ZM Monterrey", v["v2_coordenadas_mty"], f"fuera_de_zona={v['totales']['coords_invalidas']}"),
        ("3. Coherencia tipo_producto y theta", v["v3_coherencia_frescura"], f"no_perecederos_con_theta={v['totales']['no_perecederos_con_theta']}"),
        ("4. viaje_pedidos.orden consecutivo 1..n", v["v4_orden_consecutivo"], f"total_paradas={v['totales']['viaje_pedidos']}"),
        ("5. Ofertas pendientes con expira_en > now", v["v5_ofertas_vigentes"], f"ofertas_vigentes={v['totales']['ofertas_vigentes']}"),
        ("6. Las 10 claves de configuración existen", v["v6_configuracion_10_claves"], f"claves={v['totales']['configuracion_claves']}/10"),
        ("7. platform_connections activas para demo", v["v7_conexiones_activas"], f"conexiones={v['totales']['conns_activas']}"),
    ]

    for label, passed, detail in checks:
        icon = "  [PASS] ✔" if passed else "  [FAIL] ✘"
        print(f"{icon} {label:<45} ({detail})")

    print("-" * 75)
    if v["todas_pasan"]:
        print("🎉 ESTADO: 100% CONFORME CON EL CONTRATO V2.0. Listo para conectar.")
        sys.exit(0)
    else:
        print("❌ ESTADO: FALLARON UNA O MÁS VERIFICACIONES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
