#!/usr/bin/env python3
"""
Script de prueba de integración de la API de Vygo.
Envía la petición de ejemplo del Contrato v1.0 a /decidir y muestra la decisión.
"""
import sys
import json
import httpx

API_BASE = "http://localhost:8000"

PAYLOAD_EJEMPLO = {
  "version": "1.0",
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

def main():
    print(f"Probando conexion con API Vygo en {API_BASE}...")
    try:
        with httpx.Client(base_url=API_BASE, timeout=5.0) as client:
            res_salud = client.get("/salud")
            print(f"[GET /salud] Status: {res_salud.status_code}, Body: {res_salud.json()}")

            res_decidir = client.post("/decidir", json=PAYLOAD_EJEMPLO)
            print(f"[POST /decidir] Status: {res_decidir.status_code}")
            data = res_decidir.json()
            print(f"  Politica: {data['politica']} (Latencia: {data['latencia_ms']} ms)")
            for d in data.get("decisiones", []):
                print(f"  Decision oferta {d['oferta_id']}: {d['decision'].upper()} ({d['explicacion_corta']})")
                print(f"    - Tasa marginal: ${d['economia']['tasa_marginal_mxn_h']:.1f}/h")
                print(f"    - Rho actual:    ${d['economia']['rho_actual_mxn_h']:.1f}/h")
                print(f"    - Ajuste PPO:    {d['economia']['ajuste_aprendido_mxn_h']:+.1f} MXN/h")
                print(f"    - Explicacion:   {d['explicacion']}")
            print(f"  Plan paradas: {len(data['plan']['paradas'])}")
            print(f"  Geometria: {data['plan']['geometria']['type']} con {len(data['plan']['geometria']['coordinates'])} coordenadas")

    except httpx.ConnectError:
        print(f"No se pudo conectar a {API_BASE}. Asegurese de ejecutar uvicorn app.main:app --port 8000")
        sys.exit(1)

if __name__ == "__main__":
    main()
