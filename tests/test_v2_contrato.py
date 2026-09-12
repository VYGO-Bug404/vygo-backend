"""
tests/test_v2_contrato.py
Pruebas de cumplimiento estricto con el Contrato de Datos del Agente v2.0
(12 de septiembre de 2026 - Reconciliado con Supabase y Frontend src/lib/vygoAgent.ts).
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.schemas import (
    Punto,
    PedidoContexto,
    PedidoActivo,
    OfertaEntrante,
    RepartidorEstado,
    PeticionDecidir,
    RespuestaDecidir,
    DecisionOferta,
    Economia,
    Riesgo,
    Plan,
)
from app.core.policies import evaluar_oferta, normalizar_politica

client = TestClient(app)

def test_pedido_contexto_valido_caliente():
    ctx = PedidoContexto(
        tiempo_preparacion_min=12,
        tipo_producto="caliente",
        theta_frescura_min=25.0,
        zona="centro",
        limite_entrega_en="2026-09-12T14:45:00-06:00",
        propina_esperada_mxn=18.0,
        comercio_nombre="Sushi Roll Centro",
    )
    assert ctx.tiempo_preparacion_min == 12
    assert ctx.tipo_producto == "caliente"
    assert ctx.theta_frescura_min == 25.0
    assert ctx.zona == "centro"
    assert ctx.propina_esperada_mxn == 18.0
    assert ctx.comercio_nombre == "Sushi Roll Centro"

def test_pedido_contexto_no_perecedero_omite_theta():
    # §4: Si inyectas un pedido no_perecedero, omite theta_frescura_min
    ctx = PedidoContexto(
        tiempo_preparacion_min=5,
        tipo_producto="no_perecedero",
        theta_frescura_min=25.0,  # Debe anularse automáticamente
        zona="san_pedro",
    )
    assert ctx.tipo_producto == "no_perecedero"
    assert ctx.theta_frescura_min is None

def test_normalizar_politica_v2():
    assert normalizar_politica("PPO") == ("agente_ppo", "PPO")
    assert normalizar_politica("HIBRIDO") == ("B2_umbral", "HIBRIDO")
    assert normalizar_politica("B1") == ("B1_simple", "B1")
    assert normalizar_politica("B2") == ("B2_umbral", "HIBRIDO")
    assert normalizar_politica("agente_ppo") == ("agente_ppo", "agente_ppo")
    assert normalizar_politica("B2_umbral") == ("B2_umbral", "B2_umbral")

def test_decision_oferta_campos_top_level_v2():
    # §5: DecisionOferta debe tener aceptar: bool, tasa_marginal, rho_actual, ajuste_aprendido, politica
    dec = DecisionOferta(
        oferta_id="of-test-01",
        pedido_id="ped-test-01",
        app="rappi",
        decision="aceptar",
        explicacion_corta="+$185/h vs tu $140/h",
        explicacion="Acepta: supera umbral",
        economia=Economia(
            tarifa_mxn=65.0,
            delta_tiempo_min=15.0,
            delta_distancia_km=2.5,
            costo_marginal_mxn=7.5,
            ganancia_neta_mxn=57.5,
            tasa_marginal_mxn_h=185.0,
            rho_actual_mxn_h=140.0,
            ajuste_aprendido_mxn_h=0.0,
            umbral_superado=True,
        ),
        riesgo=Riesgo(
            holgura_frescura_min=18.0,
            holgura_limite_min=22.0,
            prob_entrega_a_tiempo=0.92,
            p_gana=0.75,
            anillo=1,
        ),
    )
    # Validar campos autocompletados para v2.0
    assert dec.aceptar is True
    assert dec.tasa_marginal == 185.0
    assert dec.rho_actual == 140.0
    assert dec.ajuste_aprendido == 0.0
    assert dec.economia.tarifa == 65.0
    assert dec.economia.ganancia_neta == 57.5
    assert dec.riesgo.prob_retraso == 0.08
    assert dec.riesgo.frescura_restante == 18.0
    assert dec.riesgo.holgura == 22.0

def test_politica_hibrido_ajuste_aprendido_cero():
    # §1 & §5.1: En HÍBRIDO, ajuste_aprendido es estrictamente 0.0
    rep = RepartidorEstado(
        id="rep-01",
        posicion=Punto(lat=25.6714, lon=-100.3094),
        capacidad=3,
        rho_actual_mxn_h=140.0,
    )
    of = OfertaEntrante(
        oferta_id="of-hibrido-01",
        pedido_id="ped-01",
        app="uber",
        origen=Punto(lat=25.6780, lon=-100.3120),
        destino=Punto(lat=25.6620, lon=-100.2920),
        precio_mxn=70.0,
    )
    t0 = datetime.now(timezone.utc)
    dec, _ = evaluar_oferta(rep, [], of, None, "HIBRIDO", t0)

    assert dec.politica == "HIBRIDO"
    assert dec.ajuste_aprendido == 0.0
    assert dec.economia.ajuste_aprendido_mxn_h == 0.0

def test_endpoint_decidir_con_politica_v2_hibrido():
    payload = {
        "version": "2.0",
        "politica": "HIBRIDO",
        "repartidor": {
            "id": "rep-hibrido",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [],
        "ofertas": [
            {
                "oferta_id": "of-v2-1",
                "pedido_id": "ped-v2-1",
                "app": "didi",
                "origen": {"lat": 25.6790, "lon": -100.3140},
                "destino": {"lat": 25.6600, "lon": -100.2900},
                "precio_mxn": 78.0,
            }
        ],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["politica"] == "HIBRIDO"

    dec = data["decisiones"][0]
    assert dec["aceptar"] is True
    assert dec["politica"] == "HIBRIDO"
    assert dec["ajuste_aprendido"] == 0.0
    assert dec["tasa_marginal"] > 0.0
    assert dec["rho_actual"] == 140.0
    assert "secuencia" in data["plan"]
    assert len(data["plan"]["secuencia"]) >= 1

def test_endpoint_decidir_con_politica_v2_ppo():
    payload = {
        "version": "2.0",
        "politica": "PPO",
        "repartidor": {
            "id": "rep-ppo",
            "posicion": {"lat": 25.6714, "lon": -100.3094},
            "capacidad": 3,
            "rho_actual_mxn_h": 140.0,
        },
        "plan_activo": [],
        "ofertas": [
            {
                "oferta_id": "of-v2-ppo",
                "pedido_id": "ped-v2-ppo",
                "app": "rappi",
                "origen": {"lat": 25.6790, "lon": -100.3140},
                "destino": {"lat": 25.6600, "lon": -100.2900},
                "precio_mxn": 72.0,
            }
        ],
    }
    res = client.post("/decidir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["politica"] == "PPO"
    dec = data["decisiones"][0]
    assert dec["politica"] == "PPO"
    assert dec["aceptar"] is True

def test_no_perecedero_no_falla_por_frescura_en_trayecto_largo():
    # §4: Consistencia obligatoria. Para paquetería / no_perecedero, omite theta_frescura
    # Un trayecto de 35 min fallaría si theta_frescura fuera 25 min, pero al ser no_perecedero debe ser factible
    rep = RepartidorEstado(
        id="rep-paquete",
        posicion=Punto(lat=25.6714, lon=-100.3094),
        capacidad=3,
        rho_actual_mxn_h=100.0,
    )
    of_no_perecedero = OfertaEntrante(
        oferta_id="of-paquete-01",
        pedido_id="ped-paquete-01",
        app="uber",
        # Origen y destino lejanos
        origen=Punto(lat=25.7180, lon=-100.3760),
        destino=Punto(lat=25.6510, lon=-100.2890),
        precio_mxn=120.0,
        contexto=PedidoContexto(
            tiempo_preparacion_min=5,
            tipo_producto="no_perecedero",
            zona="cumbres",
        ),
    )
    t0 = datetime.now(timezone.utc)
    dec, sec = evaluar_oferta(rep, [], of_no_perecedero, None, "HIBRIDO", t0)
    assert dec.factible is True
    assert dec.motivo_infactible is None

def test_oferta_con_contexto_dict_deriva_tiempos():
    # Oferta con contexto en formato dict JSONB plano
    of = OfertaEntrante(
        oferta_id="of-dict-01",
        pedido_id="ped-dict-01",
        app="rappi",
        origen=Punto(lat=25.6714, lon=-100.3094),
        destino=Punto(lat=25.6600, lon=-100.2900),
        precio_mxn=65.0,
        contexto={
            "tiempo_preparacion_min": 15,
            "tipo_producto": "caliente",
            "theta_frescura_min": 25,
            "limite_entrega_en": "2026-09-12T15:00:00-06:00",
            "comercio_nombre": "Tacos El Chivo",
            "propina_esperada_mxn": 20.0,
        },
    )
    assert of.limite_en == "2026-09-12T15:00:00-06:00"

def test_simular_evaluar_db_repartidor_inexistente_retorna_404():
    res = client.post("/simular/evaluar_db?repartidor_id=rep-fantasma-999")
    assert res.status_code == 404
    assert "no encontrado" in res.json()["detail"]

