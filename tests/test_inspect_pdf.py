"""
tests/test_contrato_invariantes.py (formerly test_inspect_pdf.py)
Pruebas exhaustivas de invariantes y casos borde del Contrato v2.0:
  - §3.4: Ubicaciones obsoletas (>60s) caen a origen_actual
  - §3.4: Repartidor no disponible recibe 0 ofertas
  - §4.1: Filtrado estricto por platform_connections activas
  - §4.1: Consulta 4 calcula rho_actual = rho_inicial antes de la primera entrega
  - §5.1: riesgo.holgura representa tiempo de espera en cocina (σ_i)
  - §5.2: riesgo.frescura_restante es None para productos no perecederos
  - §5.1: Plantilla de explicación corta para rechazo
  - §5.3 / API: Endpoint /simular/turno_db con simulación multipaso
  - §6: Idempotencia en script SQL (ON CONFLICT)
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.schemas import (
    Punto,
    PedidoContexto,
    PedidoActivo,
    OfertaEntrante,
    RepartidorEstado,
    DecisionOferta,
    Economia,
    Riesgo,
)
from app.core.policies import evaluar_oferta
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

def test_riesgo_holgura_es_espera_cocina():
    """§5.1: riesgo.holgura es max(0, r_i - llegada_comercio) = σ_i."""
    rep = RepartidorEstado(
        id="rep-01",
        posicion=Punto(lat=25.6714, lon=-100.3094),
        capacidad=3,
        rho_actual_mxn_h=120.0,
    )
    # Oferta muy cercana donde se llega en 2 min pero preparación tarda 15 min -> espera en cocina = ~13 min
    of = OfertaEntrante(
        oferta_id="of-holgura-01",
        pedido_id="ped-holgura-01",
        app="uber",
        origen=Punto(lat=25.6720, lon=-100.3100),
        destino=Punto(lat=25.6780, lon=-100.3150),
        precio_mxn=75.0,
        contexto=PedidoContexto(
            tiempo_preparacion_min=15,
            tipo_producto="caliente",
            theta_frescura_min=25.0,
        ),
    )
    t0 = datetime.now(timezone.utc)
    dec, _ = evaluar_oferta(rep, [], of, None, "HIBRIDO", t0)
    assert dec.factible is True
    # La holgura en cocina debe ser positiva (~12-14 min)
    assert dec.riesgo.holgura >= 10.0
    assert dec.riesgo.holgura_limite_min > 0.0

def test_riesgo_no_perecedero_frescura_restante_none():
    """§5.2: Si producto es no_perecedero, frescura_restante debe ser None."""
    rep = RepartidorEstado(
        id="rep-01",
        posicion=Punto(lat=25.6714, lon=-100.3094),
        capacidad=3,
        rho_actual_mxn_h=120.0,
    )
    of = OfertaEntrante(
        oferta_id="of-nop-01",
        pedido_id="ped-nop-01",
        app="didi",
        origen=Punto(lat=25.6720, lon=-100.3100),
        destino=Punto(lat=25.6780, lon=-100.3150),
        precio_mxn=70.0,
        contexto=PedidoContexto(
            tiempo_preparacion_min=5,
            tipo_producto="no_perecedero",
            zona="centro",
        ),
    )
    t0 = datetime.now(timezone.utc)
    dec, _ = evaluar_oferta(rep, [], of, None, "HIBRIDO", t0)
    assert dec.factible is True
    assert dec.riesgo.frescura_restante is None

def test_explicacion_corta_rechazo_template():
    """§5.1: Plantilla de explicacion_corta al rechazar: «Rechazado: te paga a $X/h, tu promedio hoy es $Y/h»."""
    rep = RepartidorEstado(
        id="rep-01",
        posicion=Punto(lat=25.6714, lon=-100.3094),
        capacidad=3,
        rho_actual_mxn_h=250.0, # Umbral muy alto para forzar rechazo económico
    )
    of = OfertaEntrante(
        oferta_id="of-rech-01",
        pedido_id="ped-rech-01",
        app="rappi",
        origen=Punto(lat=25.6800, lon=-100.3200),
        destino=Punto(lat=25.6900, lon=-100.3300),
        precio_mxn=40.0,
    )
    t0 = datetime.now(timezone.utc)
    dec, _ = evaluar_oferta(rep, [], of, None, "HIBRIDO", t0)
    assert dec.decision == "rechazar"
    assert dec.aceptar is False
    assert "Rechazado: te paga a $" in dec.explicacion_corta
    assert "tu promedio hoy es $250/h" in dec.explicacion_corta

def test_repartidor_no_disponible_cero_ofertas():
    """§3.4: Si repartidores.disponible es false, no se le ofrece nada."""
    db = obtener_db()
    db.repartidores["rep-demo-01"]["disponible"] = False
    ofertas = db.obtener_ofertas_pendientes("rep-demo-01")
    assert len(ofertas) == 0

def test_repartidor_sin_plataformas_activas_cero_ofertas():
    """§4.1 Consulta 3: Si no tiene conexiones activas, no recibe ofertas."""
    db = obtener_db()
    for conn in db.platform_connections:
        conn["is_active"] = False
    ofertas = db.obtener_ofertas_pendientes("rep-demo-01")
    assert len(ofertas) == 0

def test_ubicacion_stale_cae_a_origen_actual():
    """§3.4: Si ubicaciones_conductores.updated_at tiene más de 60s, cae a origen_actual."""
    db = obtener_db()
    now = datetime.now(timezone.utc)
    # Ping GPS viejo (120 s atrás) con latitud 25.80
    db.ubicaciones_conductores["usr-rep-demo-01"] = {
        "user_id": "usr-rep-demo-01",
        "lat": 25.8000,
        "lng": -100.3500,
        "updated_at": (now - timedelta(seconds=120)).isoformat(),
    }
    # Origen actual en viaje activo es 25.6714
    st = db.obtener_estado_repartidor("rep-demo-01")
    assert st is not None
    # Debe haber caído a origen_actual (25.6714), no al GPS viejo
    assert st["lat"] == 25.6714

def test_metricas_sin_entregas_usa_rho_inicial():
    """§5.1 & §4.1: Sin entregas previas, rho_actual = rho_inicial_mxn_h (140.0)."""
    db = obtener_db()
    # Poner todos los pedidos en buscando para tener 0 entregados
    for p in db.pedidos.values():
        if p["estado"] == "entregado":
            p["estado"] = "buscando"
    metricas = db.obtener_metricas_turno("rep-demo-01")
    assert metricas["entregados"] == 0
    assert metricas["rho_actual"] == 140.0

def test_endpoint_simular_turno_db_multipasos():
    """Prueba del nuevo endpoint POST /simular/turno_db con pasos secuenciales."""
    res = client.post("/simular/turno_db?repartidor_id=rep-demo-01&politica=HIBRIDO&pasos=2&persistir=true")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["pasos_simulados"] >= 1
    assert len(data["historial"]) >= 1

def test_sql_inyeccion_idempotente():
    """§6: El SQL generado incluye ON CONFLICT para inserciones repetibles."""
    from pathlib import Path
    sql = generar_sql_inyeccion_completo()
    assert "INSERT INTO platform_connections" in sql
    assert "ON CONFLICT (user_id, platform)" in sql
    assert "INSERT INTO viaje_pedidos" in sql
    assert "ON CONFLICT (viaje_id, pedido_id)" in sql
    assert "INSERT INTO difusiones_pedido" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql

    # Sincronizar scripts/seed_supabase.sql con el SQL idempotente actualizado
    sql_path = Path(__file__).resolve().parent.parent / "scripts" / "seed_supabase.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql)
def test_ejecutar_pruebas_test_api():
    """Ejecuta el script completo scripts/test_api.py en memoria y verifica su salida."""
    from scripts.test_api import ejecutar_pruebas
    ejecutar_pruebas(client, "Pytest TestClient")
