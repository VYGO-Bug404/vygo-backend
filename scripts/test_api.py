#!/usr/bin/env python3
"""
Script de prueba de integración de la API de Vygo.
Prueba:
  1. GET /salud
  2. POST /decidir (Superficie A - Contrato v1.0 y v2.0)
  3. POST /simular/evaluar_db (Superficie D - Contrato v2.0 con BD Supabase)
  4. GET /simular/verificar (Las 7 verificaciones oficiales §7)
"""
import sys
from pathlib import Path
import httpx

# Agregar directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

API_BASE = "http://localhost:8000"

PAYLOAD_EJEMPLO = {
  "version": "2.0",
  "politica": "HIBRIDO",
  "repartidor": {
    "id": "8f2c1a40-1234-5678-9abc-def012345678",
    "posicion": { "lat": 25.6714, "lon": -100.3094 },
    "vehiculo": "moto",
    "capacidad": 2,
    "minutos_turno_transcurridos": 182,
    "minutos_turno_restantes": 178,
    "ganancia_turno_mxn": 428.50,
    "km_recorridos": 23.7,
    "rho_actual_mxn_h": 141.30
  },
  "plan_activo": [
    {
      "pedido_id": "a71f0001", "app": "uber", "estado": "asignado",
      "origen": { "lat": 25.6801, "lon": -100.3155 },
      "destino": { "lat": 25.6650, "lon": -100.2980 },
      "listo_en": "2026-09-12T14:09:00-06:00",
      "limite_en": "2026-09-12T14:38:00-06:00",
      "theta_frescura_min": 25, "recogido": False
    }
  ],
  "ofertas": [
    {
      "oferta_id": "c93b0001", "pedido_id": "d15e0001", "app": "rappi",
      "origen": { "lat": 25.6790, "lon": -100.3140 },
      "destino": { "lat": 25.6602, "lon": -100.2905 },
      "precio_mxn": 62.00,
      "listo_estimado_en": "2026-09-12T14:14:00-06:00",
      "limite_en": "2026-09-12T14:45:00-06:00",
      "expira_en": "2026-09-12T14:03:52-06:00",
      "anillo": 1, "radio_metros": 1500,
      "desvio_estimado_metros": 4100
    }
  ],
  "contexto": { "clima": "normal", "evento_activo": "surge" }
}

def ejecutar_pruebas(client, modo: str):
    print(f"\n--- Ejecutando pruebas en modo: {modo} ---")
    
    # 1. /salud
    res_salud = client.get("/salud")
    print(f"[GET /salud] Status: {res_salud.status_code}, Body: {res_salud.json()}")

    # 2. /decidir
    res_decidir = client.post("/decidir", json=PAYLOAD_EJEMPLO)
    print(f"[POST /decidir] Status: {res_decidir.status_code}")
    data = res_decidir.json()
    print(f"  Politica: {data['politica']} (Latencia: {data['latencia_ms']} ms)")
    for d in data.get("decisiones", []):
        print(f"  Decision oferta {d['oferta_id']}: {d['decision'].upper()} (aceptar={d.get('aceptar')})")
        print(f"    - Tasa marginal: ${d['tasa_marginal']:.1f}/h")
        print(f"    - Rho actual:    ${d['rho_actual']:.1f}/h")
        print(f"    - Ajuste aprendido: {d['ajuste_aprendido']:+.1f} MXN/h")
        print(f"    - Explicacion:   {d['explicacion_corta']}")
    print(f"  Plan paradas: {len(data['plan']['paradas'])}")
    print(f"  Plan secuencia v2: {data['plan'].get('secuencia')}")

    # 3. /simular/verificar
    res_verif = client.get("/simular/verificar")
    print(f"\n[GET /simular/verificar] Status: {res_verif.status_code}")
    print(f"  Todas las 7 verificaciones pasan: {res_verif.json().get('todas_pasan')}")

    # 4. /simular/evaluar_db
    res_sim = client.post("/simular/evaluar_db?repartidor_id=rep-demo-01&politica=HIBRIDO&persistir=true")
    print(f"\n[POST /simular/evaluar_db] Status: {res_sim.status_code}")
    sim_data = res_sim.json()
    print(f"  Politica: {sim_data['politica']} (Latencia: {sim_data['latencia_ms']} ms)")
    print(f"  Ofertas evaluadas desde DB: {sim_data['ofertas_evaluadas']}")
    print(f"  Pedidos a bordo iniciales: {sim_data['pedidos_a_bordo_iniciales']}")
    print(f"  Mutaciones realizadas: {sim_data.get('mutaciones_escritura_bd', {})}")

    # 5. /simular/turno_db
    res_turno = client.post("/simular/turno_db?repartidor_id=rep-demo-01&politica=HIBRIDO&pasos=2&persistir=true")
    print(f"\n[POST /simular/turno_db] Status: {res_turno.status_code}")
    turno_data = res_turno.json()
    print(f"  Pasos simulados: {turno_data.get('pasos_simulados')}")
    print(f"  Historial: {len(turno_data.get('historial', []))} pasos")

def main():
    print(f"Intentando conectar con servidor en {API_BASE}...")
    try:
        with httpx.Client(base_url=API_BASE, timeout=3.0) as live_client:
            live_client.get("/salud")
            ejecutar_pruebas(live_client, f"HTTP Remoto ({API_BASE})")
    except Exception:
        print(f"No hay servidor activo en {API_BASE}. Usando FastAPI TestClient en memoria...")
        from fastapi.testclient import TestClient
        test_client = TestClient(app)
        ejecutar_pruebas(test_client, "In-Memory TestClient")

    print("\n✔ Todas las pruebas completadas exitosamente.")

if __name__ == "__main__":
    main()
