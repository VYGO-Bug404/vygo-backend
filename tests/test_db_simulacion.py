"""
tests/test_db_simulacion.py
Pruebas exhaustivas del motor de simulación de datos y persistencia Supabase
según el Contrato de Datos del Agente v2.0 (§4, §5.3, §6, §7).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import (
    obtener_db,
    construir_peticion_desde_db,
    generar_sql_inyeccion_completo,
    MockSupabaseDB,
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def reiniciar_db():
    db = obtener_db()
    db.inicializar_datos_semilla()
    yield
    db.inicializar_datos_semilla()

def test_plan_inyeccion_11_tablas_y_40_pedidos():
    db = obtener_db()
    # Verificar las 11 tablas según §6
    assert len(db.apps) == 3
    assert len(db.usuarios) == 31  # 1 repartidor + 30 clientes
    assert len(db.repartidores) == 1
    assert len(db.platform_connections) == 3
    assert len(db.configuracion) == 10
    assert len(db.ubicaciones_conductores) == 1
    assert len(db.viajes_repartidor) == 1
    assert len(db.pedidos) == 40
    assert len(db.viaje_pedidos) == 15  # 12 entregados + 3 a bordo
    assert len(db.difusiones_pedido) == 25
    assert len(db.ofertas_pedido) == 8

    # Desglose de estados de los 40 pedidos
    entregados = sum(1 for p in db.pedidos.values() if p["estado"] == "entregado")
    asignados = sum(1 for p in db.pedidos.values() if p["estado"] == "asignado")
    buscando = sum(1 for p in db.pedidos.values() if p["estado"] == "buscando")
    assert entregados == 12
    assert asignados == 3
    assert buscando == 25

def test_7_verificaciones_contrato_todas_pasan():
    db = obtener_db()
    v = db.verificar_estado_inyeccion()
    assert v["v1_contexto_completo"] is True
    assert v["v2_coordenadas_mty"] is True
    assert v["v3_coherencia_frescura"] is True
    assert v["v4_orden_consecutivo"] is True
    assert v["v5_ofertas_vigentes"] is True
    assert v["v6_configuracion_10_claves"] is True
    assert v["v7_conexiones_activas"] is True
    assert v["todas_pasan"] is True

def test_4_consultas_sql_oficiales_4_1():
    db = obtener_db()

    # Consulta 1: Estado del repartidor
    rep_st = db.obtener_estado_repartidor("rep-demo-01")
    assert rep_st is not None
    assert rep_st["id"] == "rep-demo-01"
    assert rep_st["disponible"] is True
    assert rep_st["vehiculo"] == "moto"
    assert 25.5 <= rep_st["lat"] <= 25.9
    assert -100.5 <= rep_st["lng"] <= -100.1
    assert rep_st["viaje_id"] == "viaje-demo-01"

    # Consulta 2: Plan activo (3 a bordo)
    plan_activo = db.obtener_plan_activo("viaje-demo-01")
    assert len(plan_activo) == 3
    assert all(p["estado"] in ("asignado", "en_camino") for p in plan_activo)

    # Consulta 3: Ofertas pendientes (máx 8, ordenadas por ronda y desvío)
    ofertas = db.obtener_ofertas_pendientes("rep-demo-01", limit=8)
    assert len(ofertas) == 8
    # Verificar orden no decreciente por ronda
    rondas = [o["ronda"] for o in ofertas]
    assert rondas == sorted(rondas)

    # Consulta 4: Métricas del turno para rho_actual
    metricas = db.obtener_metricas_turno("rep-demo-01")
    assert metricas["entregados"] == 12
    assert metricas["ingreso_mxn"] > 0
    assert metricas["horas"] > 0
    assert metricas["rho_actual"] >= 80.0

def test_construir_peticion_desde_db():
    req = construir_peticion_desde_db("rep-demo-01")
    assert req.version == "2.0"
    assert req.repartidor.id == "rep-demo-01"
    assert len(req.plan_activo) == 3
    assert len(req.ofertas) == 8
    assert req.repartidor.rho_actual_mxn_h > 0

def test_escritura_bd_aceptar_y_rechazar_5_3():
    db = obtener_db()
    # Aceptar oferta-demo-01
    res = db.persistir_decision_aceptar(
        oferta_id="oferta-demo-01",
        pedido_id="ped-cen-01",
        viaje_id="viaje-demo-01",
        nuevo_orden_secuencia=[("ped-cen-01", 1), ("ped-cen-02", 2)],
        coordenadas_ruta=[[-100.31, 25.67], [-100.30, 25.66]],
    )
    assert res["ok"] is True
    assert db.ofertas_pedido["oferta-demo-01"]["estado"] == "aceptada"
    assert db.pedidos["ped-cen-01"]["estado"] == "asignado"
    assert db.viajes_repartidor["viaje-demo-01"]["ruta_linea"] is not None

    # Rechazar oferta-demo-02
    res_rech = db.persistir_decision_rechazar("oferta-demo-02")
    assert res_rech["ok"] is True
    assert db.ofertas_pedido["oferta-demo-02"]["estado"] == "rechazada"

    # Verificar que tras aceptar y rechazar, el orden de paradas sigue consecutivo
    v = db.verificar_estado_inyeccion()
    assert v["v4_orden_consecutivo"] is True

def test_endpoint_simular_inyeccion():
    res = client.post("/simular/inyeccion")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["tablas"]["pedidos"] == 40
    assert data["verificaciones"]["todas_pasan"] is True

def test_endpoint_simular_verificar():
    res = client.get("/simular/verificar")
    assert res.status_code == 200
    data = res.json()
    assert data["todas_pasan"] is True
    assert data["v1_contexto_completo"] is True
    assert data["v4_orden_consecutivo"] is True

def test_endpoint_simular_evaluar_db_ppo():
    res = client.post("/simular/evaluar_db?repartidor_id=rep-demo-01&politica=PPO&persistir=true")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["politica"] == "PPO"
    assert data["repartidor_id"] == "rep-demo-01"
    assert data["latencia_ms"] < 150.0
    assert data["pedidos_a_bordo_iniciales"] == 3
    assert data["ofertas_evaluadas"] == 8

    resp = data["respuesta_decidir"]
    assert len(resp["decisiones"]) == 8
    for d in resp["decisiones"]:
        assert isinstance(d["aceptar"], bool)
        assert d["politica"] == "PPO"
        assert "tasa_marginal" in d
        assert "rho_actual" in d
        assert "ajuste_aprendido" in d

    assert data["verificaciones_contrato"]["todas_pasan"] is True

def test_endpoint_simular_evaluar_db_hibrido():
    res = client.post("/simular/evaluar_db?repartidor_id=rep-demo-01&politica=HIBRIDO&persistir=false")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["politica"] == "HIBRIDO"

    resp = data["respuesta_decidir"]
    for d in resp["decisiones"]:
        assert d["politica"] == "HIBRIDO"
        # En HÍBRIDO el ajuste aprendido es 0.0 (§1 & §5.1)
        assert d["ajuste_aprendido"] == 0.0

def test_generador_sql_st_makepoint_lon_primero():
    sql = generar_sql_inyeccion_completo()
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql
    assert "INSERT INTO apps" in sql
    assert "INSERT INTO pedidos" in sql
    assert "st_makepoint(-100." in sql  # Lon negativo (-100.x) primero
    assert "geography" in sql
