import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.rag.knowledge import buscar_conocimiento
from app.ai.rag.copiloto import CopilotoVygo, obtener_copiloto


@pytest.fixture
def client():
    return TestClient(app)


def test_buscar_conocimiento():
    # Búsqueda por restaurante
    docs_sushi = buscar_conocimiento("sushi", restaurante="Sushi Roll Centro")
    assert len(docs_sushi) > 0
    assert any("Sushi Roll" in d.titulo for d in docs_sushi)

    # Búsqueda por zona
    docs_sp = buscar_conocimiento("san pedro", zona="san_pedro")
    assert len(docs_sp) > 0
    assert any("San Pedro" in d.titulo for d in docs_sp)

    # Búsqueda por plataforma
    docs_uber = buscar_conocimiento("uber", app="uber")
    assert len(docs_uber) > 0
    assert any("Uber Eats" in d.titulo for d in docs_uber)


def test_copiloto_explicar_decision():
    copiloto = CopilotoVygo()

    # Caso aceptar
    res_aceptar = copiloto.explicar_decision(
        oferta_id="oferta-test-01",
        decision="aceptar",
        tasa_marginal=185.0,
        rho_actual=140.0,
        delta_km=1.2,
        delta_min=6.5,
        ganancia_neta=42.0,
        holgura_frescura_min=18.0,
        restaurante="Sushi Roll Centro",
        zona="centro",
        app="uber",
    )

    assert res_aceptar["oferta_id"] == "oferta-test-01"
    assert res_aceptar["decision"] == "aceptar"
    assert "+$185/h" in res_aceptar["frase_corta"]
    assert "Tómala" in res_aceptar["explicacion_copiloto"] or "uber" in res_aceptar["explicacion_copiloto"].lower()
    assert res_aceptar["metricas"]["tasa_marginal_mxn_h"] == 185.0
    assert res_aceptar["latencia_ms"] >= 0

    # Caso rechazar
    res_rechazar = copiloto.explicar_decision(
        oferta_id="oferta-test-02",
        decision="rechazar",
        tasa_marginal=75.0,
        rho_actual=140.0,
        delta_km=4.8,
        delta_min=18.0,
        ganancia_neta=12.0,
        restaurante="Tacos El Primo",
        zona="san_pedro",
        app="didi",
    )

    assert res_rechazar["decision"] == "rechazar"
    assert "$75/h < tu $140/h" in res_rechazar["frase_corta"]
    assert "Déjala pasar" in res_rechazar["explicacion_copiloto"]


def test_copiloto_responder_chat():
    copiloto = CopilotoVygo()
    res = copiloto.responder_chat("¿Cuánto tiempo tardan en Sushi Roll Centro?")
    assert "pregunta" in res
    assert "respuesta" in res
    assert len(res["fuentes"]) > 0


def test_endpoint_copiloto_explicar(client):
    payload = {
        "oferta_id": "of-api-01",
        "decision": "aceptar",
        "tasa_marginal": 190.0,
        "rho_actual": 135.0,
        "delta_km": 1.5,
        "delta_min": 7.0,
        "ganancia_neta": 45.0,
        "holgura_frescura_min": 20.0,
        "restaurante": "Sushi Roll Centro",
        "zona": "centro",
        "app": "uber",
    }
    resp = client.post("/copiloto/explicar", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["oferta_id"] == "of-api-01"
    assert data["decision"] == "aceptar"
    assert "frase_corta" in data
    assert "explicacion_copiloto" in data
    assert data["metricas"]["tasa_marginal_mxn_h"] == 190.0


def test_endpoint_copiloto_chat(client):
    payload = {
        "pregunta": "¿Cuál es la penalización de cancelación en Rappi?",
    }
    resp = client.post("/copiloto/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pregunta"] == payload["pregunta"]
    assert "respuesta" in data
    assert len(data["fuentes"]) > 0


def test_endpoint_demo_geometria(client):
    resp = client.get("/demo/geometria.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "tramos" in data
    assert "serial" in data["tramos"]
    assert "vygo" in data["tramos"]
    primer_tramo = data["tramos"]["vygo"][0]
    assert "polilinea" in primer_tramo
    assert len(primer_tramo["polilinea"]) > 0
    assert "meta" in data
    assert data["meta"]["pares_resueltos"] == 40


def test_endpoint_demo_replay(client):
    resp = client.get("/demo/replay.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "serial" in data
    assert "vygo" in data
    assert data["serial"]["entregas"] == 5
    assert data["vygo"]["entregas"] == 16



def test_endpoint_demo_turno_html(client):
    resp = client.get("/demo/turno.html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "VYGO" in resp.text or "MapLibre" in resp.text
