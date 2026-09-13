import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoint_salud():
    res = client.get("/salud")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["politica"] in ("HIBRIDO", "agente_ppo")
    assert "version" in data
    assert "timestamp" in data

def test_endpoint_decidir_oferta_rentable_aceptada():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-001",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "vehiculo": "moto",
            "capacidad": 3,
            "minutos_turno_transcurridos": 120,
            "minutos_turno_restantes": 240,
            "ganancia_turno_mxn": 280.0,
            "km_recorridos": 18.0,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [
            {
                "pedido_id": "ped-activo-1",
                "app": "uber",
                "estado": "asignado",
                "origen": {"lat": 25.6800, "lon": -100.3150},
                "destino": {"lat": 25.6650, "lon": -100.2980},
                "listo_en": "2026-09-12T14:10:00-06:00",
                "limite_en": "2026-09-12T14:40:00-06:00",
                "theta_frescura_min": 30,
                "recogido": False,
            }
        ],
        "ofertas": [
            {
                "oferta_id": "of-rentable-1",
                "pedido_id": "ped-nuevo-1",
                "app": "rappi",
                "origen": {"lat": 25.6790, "lon": -100.3140},
                "destino": {"lat": 25.6600, "lon": -100.2900},
                "precio_mxn": 75.0,
                "listo_estimado_en": "2026-09-12T14:12:00-06:00",
                "limite_en": "2026-09-12T14:45:00-06:00",
                "anillo": 1,
            }
        ],
        "contexto": {"clima": "normal", "evento_activo": "surge"},
    }

    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "1.0"
    assert data["politica"] in ("HIBRIDO", "agente_ppo")
    assert data["latencia_ms"] < 150.0

    dec = data["decisiones"][0]
    assert dec["decision"] == "aceptar"
    assert dec["factible"] is True
    assert dec["motivo_infactible"] is None
    # Verificación de los 3 números clave de explicabilidad
    assert dec["economia"]["tasa_marginal_mxn_h"] > 0
    assert dec["economia"]["rho_actual_mxn_h"] == 140.0
    assert "ajuste_aprendido_mxn_h" in dec["economia"]
    assert "$" in dec["explicacion_corta"]
    assert len(data["plan"]["paradas"]) == 4

def test_endpoint_decidir_oferta_desvio_rechazada():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-002",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "vehiculo": "moto",
            "capacidad": 2,
            "minutos_turno_transcurridos": 180,
            "minutos_turno_restantes": 180,
            "ganancia_turno_mxn": 500.0,
            "km_recorridos": 25.0,
            "rho_actual_mxn_h": 166.7,
        },
        "plan_activo": [],
        "ofertas": [
            {
                "oferta_id": "of-baja-1",
                "pedido_id": "ped-baja-1",
                "app": "didi",
                # Gran desvío hacia la periferia con baja paga
                "origen": {"lat": 25.7500, "lon": -100.4200},
                "destino": {"lat": 25.8000, "lon": -100.5000},
                "precio_mxn": 35.0,
                "anillo": 2,
            }
        ],
    }

    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    dec = data["decisiones"][0]
    assert dec["decision"] == "rechazar"

def test_endpoint_decidir_exceso_capacidad_infactible():
    # Repartidor con capacidad 2 y ya tiene 2 pedidos a bordo
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-003",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 2,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [
            {
                "pedido_id": "p1", "app": "uber",
                "origen": {"lat": 25.68, "lon": -100.31}, "destino": {"lat": 25.66, "lon": -100.29},
                "recogido": True
            },
            {
                "pedido_id": "p2", "app": "rappi",
                "origen": {"lat": 25.68, "lon": -100.31}, "destino": {"lat": 25.66, "lon": -100.29},
                "recogido": True
            },
        ],
        "ofertas": [
            {
                "oferta_id": "of-extra", "pedido_id": "p3", "app": "didi",
                "origen": {"lat": 25.679, "lon": -100.314}, "destino": {"lat": 25.661, "lon": -100.291},
                "precio_mxn": 80.0
            }
        ],
    }

    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    dec = data["decisiones"][0]
    assert dec["decision"] == "rechazar"
    assert dec["factible"] is False
    assert dec["motivo_infactible"] == "capacidad"

def test_endpoint_decidir_coordenadas_invalidas_retorna_422():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-004",
            # Coordenadas invertidas
            "posicion": {"lat": -100.3094, "lon": 25.6714},
        },
        "plan_activo": [],
        "ofertas": [],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 422

def test_endpoint_replay():
    res = client.get("/replay/12.json")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "1.0"
    assert data["escenario"]["id"] == 12
    assert len(data["pistas"]) == 3
    politicas = [p["politica"] for p in data["pistas"]]
    assert "B1_simple" in politicas
    assert "B2_umbral" in politicas
    assert "agente_ppo" in politicas

def test_endpoint_replay_inexistente_retorna_404():
    res = client.get("/replay/9999.json")
    assert res.status_code == 404

def test_endpoint_turno_stream_sse():
    with client.stream("GET", "/turno/stream?escenario=12&politica=HIBRIDO&velocidad=10000.0") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        for line in response.iter_lines():
            if line.startswith("data:"):
                assert len(line) > 5
                break

def test_endpoint_decidir_multiples_ofertas():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-multi",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [],
        "ofertas": [
            {
                "oferta_id": "of-1", "pedido_id": "p1", "app": "uber",
                "origen": {"lat": 25.68, "lon": -100.31}, "destino": {"lat": 25.66, "lon": -100.29},
                "precio_mxn": 75.0,
            },
            {
                "oferta_id": "of-2", "pedido_id": "p2", "app": "rappi",
                "origen": {"lat": 25.75, "lon": -100.42}, "destino": {"lat": 25.80, "lon": -100.50},
                "precio_mxn": 30.0,
            },
        ],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["decisiones"]) == 2
    # La oferta en zona céntrica debe ser aceptada y la lejana con baja paga debe ser rechazada
    decs = {d["oferta_id"]: d["decision"] for d in data["decisiones"]}
    assert decs["of-1"] == "aceptar"
    assert decs["of-2"] == "rechazar"

def test_endpoint_replay_metricas_exactas_pitch():
    res = client.get("/replay/12.json")
    assert res.status_code == 200
    data = res.json()
    pistas = {p["politica"]: p["resumen"] for p in data["pistas"]}

    # B1_simple
    assert pistas["B1_simple"]["entregados"] == 11
    assert pistas["B1_simple"]["ingreso_mxn"] == 612
    assert pistas["B1_simple"]["km"] == 41.2
    assert pistas["B1_simple"]["rho_mxn_h"] == 102.0
    assert pistas["B1_simple"]["puntualidad"] == 0.72

    # B2_umbral
    assert pistas["B2_umbral"]["entregados"] == 17
    assert pistas["B2_umbral"]["ingreso_mxn"] == 948
    assert pistas["B2_umbral"]["km"] == 28.7
    assert pistas["B2_umbral"]["rho_mxn_h"] == 158.0
    assert pistas["B2_umbral"]["puntualidad"] == 0.91

    # agente_ppo
    assert pistas["agente_ppo"]["entregados"] == 18
    assert pistas["agente_ppo"]["ingreso_mxn"] == 1014
    assert pistas["agente_ppo"]["km"] == 27.1
    assert pistas["agente_ppo"]["rho_mxn_h"] == 169.0
    assert pistas["agente_ppo"]["puntualidad"] == 0.93

def test_endpoint_decidir_surge_hora_23_utc():
    # Contexto con surge no debe fallar sin importar la hora del sistema
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-surge",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 2,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [],
        "ofertas": [],
        "contexto": {"clima": "normal", "evento_activo": "surge"},
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["evento_activo"] is not None
    assert data["evento_activo"]["tipo"] == "surge"
    assert data["evento_activo"]["multiplicador_tarifa"] == 1.4

def test_endpoint_decidir_query_param_politica():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-pol",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [],
        "ofertas": [
            {
                "oferta_id": "of-pol", "pedido_id": "ped-pol", "app": "uber",
                "origen": {"lat": 25.68, "lon": -100.31}, "destino": {"lat": 25.66, "lon": -100.29},
                "precio_mxn": 70.0,
            }
        ],
    }
    # Forzar B1_simple vía query param
    res_b1 = client.post("/decidir?politica=B1_simple", json=payload)
    assert res_b1.status_code == 200
    assert res_b1.json()["politica"] == "B1_simple"

    # Forzar B2_umbral vía query param
    res_b2 = client.post("/decidir?politica=B2_umbral", json=payload)
    assert res_b2.status_code == 200
    assert res_b2.json()["politica"] == "B2_umbral"

def test_tasa_proyectada_no_inflada_por_ganancia_turno():
    # Un repartidor que ya ganó 8000 MXN en el turno no debe inflar la tasa proyectada del viaje activo
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-rico",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "ganancia_turno_mxn": 8000.0,
            "minutos_turno_transcurridos": 240,
            "rho_actual_mxn_h": 150.0,
        },
        "plan_activo": [
            {
                "pedido_id": "ped-activo", "app": "uber",
                "origen": {"lat": 25.680, "lon": -100.315}, "destino": {"lat": 25.665, "lon": -100.298},
                "precio_mxn": 65.0,
                "recogido": True,
            }
        ],
        "ofertas": [],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    plan_res = data["plan"]["resumen"]
    # El ingreso proyectado del plan debe ser el del pedido activo (~65 MXN), no 8065 MXN
    assert plan_res["ingreso_mxn"] == 65.0
    assert plan_res["tasa_proyectada_mxn_h"] < 1000.0, f"Tasa proyectada distorsionada: {plan_res['tasa_proyectada_mxn_h']}"

def test_pedidos_a_bordo_solo_recogidos():
    payload = {
        "version": "1.0",
        "repartidor": {
            "id": "rep-bordo",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [
            {
                "pedido_id": "ped-recogido", "app": "uber",
                "origen": {"lat": 25.680, "lon": -100.315}, "destino": {"lat": 25.665, "lon": -100.298},
                "recogido": True,
            },
            {
                "pedido_id": "ped-no-recogido", "app": "rappi",
                "origen": {"lat": 25.675, "lon": -100.310}, "destino": {"lat": 25.658, "lon": -100.295},
                "recogido": False,
            },
        ],
        "ofertas": [],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Solo 1 de los 2 pedidos está recogido ("a bordo")
    assert data["plan"]["resumen"]["pedidos_a_bordo"] == 1

