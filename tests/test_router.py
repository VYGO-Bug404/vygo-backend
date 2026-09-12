import time
from datetime import datetime, timezone, timedelta
import pytest

from app.core.schemas import Punto, PedidoActivo, OfertaEntrante
from app.core.router import (
    generar_items_paradas,
    resolver_secuencia_optima,
    construir_plan,
)

def test_precedencia_recoleccion_antes_de_entrega():
    p0 = Punto(lat=25.6714, lon=-100.3094)
    t0 = datetime.now(timezone.utc)
    
    # Dos pedidos no recogidos -> 4 paradas (P1, D1, P2, D2)
    p_act = [
        PedidoActivo(
            pedido_id="ped-1",
            app="uber",
            origen=Punto(lat=25.6800, lon=-100.3150),
            destino=Punto(lat=25.6600, lon=-100.2900),
            recogido=False,
        )
    ]
    oferta = OfertaEntrante(
        oferta_id="of-2",
        pedido_id="ped-2",
        app="rappi",
        origen=Punto(lat=25.6780, lon=-100.3120),
        destino=Punto(lat=25.6620, lon=-100.2920),
        precio_mxn=65.0,
    )

    items, carga = generar_items_paradas(p_act, oferta, t0)
    assert len(items) == 4
    
    sec, dist, dur, evals, motivo = resolver_secuencia_optima(
        p0, items, carga, capacidad_max=3, t0=t0
    )

    assert sec is not None
    # Verificar que para cada pedido, la recolección ocurra antes de la entrega
    indices = {}
    for idx, s in enumerate(sec):
        it = s["item"]
        indices.setdefault(it.pedido_id, {})[it.tipo] = idx

    for pid in ["ped-1", "ped-2"]:
        assert indices[pid]["recoleccion"] < indices[pid]["entrega"], f"Violación de precedencia para {pid}"

def test_restriccion_capacidad():
    p0 = Punto(lat=25.6714, lon=-100.3094)
    t0 = datetime.now(timezone.utc)

    # Si la carga inicial excede la capacidad máxima
    items, _ = generar_items_paradas([], None, t0)
    sec, dist, dur, evals, motivo = resolver_secuencia_optima(
        p0, items, carga_inicial=4, capacidad_max=3, t0=t0
    )
    assert sec is None
    assert motivo == "capacidad"

def test_rendimiento_evaluacion_90_secuencias_menor_15ms():
    p0 = Punto(lat=25.6714, lon=-100.3094)
    t0 = datetime.now(timezone.utc)

    # 3 pedidos con recolección y entrega simultáneas = 6 paradas
    # Permutaciones con precedencia: 6! / (2^3) = 720 / 8 = 90 secuencias posibles
    p_act = [
        PedidoActivo(
            pedido_id="ped-1", app="uber",
            origen=Punto(lat=25.6800, lon=-100.3150),
            destino=Punto(lat=25.6600, lon=-100.2900),
            recogido=False,
        ),
        PedidoActivo(
            pedido_id="ped-2", app="didi",
            origen=Punto(lat=25.6750, lon=-100.3120),
            destino=Punto(lat=25.6580, lon=-100.2950),
            recogido=False,
        ),
    ]
    oferta = OfertaEntrante(
        oferta_id="of-3", pedido_id="ped-3", app="rappi",
        origen=Punto(lat=25.6720, lon=-100.3110),
        destino=Punto(lat=25.6650, lon=-100.2920),
        precio_mxn=70.0,
    )

    items, carga = generar_items_paradas(p_act, oferta, t0)
    assert len(items) == 6

    t_inicio = time.perf_counter()
    sec, dist, dur, evals, motivo = resolver_secuencia_optima(
        p0, items, carga, capacidad_max=3, t0=t0
    )
    t_dur_ms = (time.perf_counter() - t_inicio) * 1000.0

    assert sec is not None
    assert evals == 90 # Exactamente 90 secuencias evaluadas respetando precedencia
    assert t_dur_ms < 15.0, f"Tiempo de cálculo excedió 15ms: {t_dur_ms:.2f}ms"
    print(f"90 secuencias evaluadas en {t_dur_ms:.2f} ms")

def test_construir_plan_geometria_geojson():
    p0 = Punto(lat=25.6714, lon=-100.3094)
    t0 = datetime.now(timezone.utc)
    p_act = [
        PedidoActivo(
            pedido_id="ped-1", app="uber",
            origen=Punto(lat=25.6800, lon=-100.3150),
            destino=Punto(lat=25.6600, lon=-100.2900),
            recogido=True, # Solo parada de entrega
        )
    ]
    items, carga = generar_items_paradas(p_act, None, t0)
    sec, dist, dur, evals, _ = resolver_secuencia_optima(p0, items, carga, 3, t0=t0)
    plan = construir_plan(p0, sec, dist, dur, 80.0, evals, t0)

    assert plan.resumen.optimo_exacto is True
    assert len(plan.paradas) == 1
    # Geometria contiene posicion inicial + 1 parada = 2 puntos [lon, lat]
    assert len(plan.geometria.coordinates) == 2
    assert plan.geometria.coordinates[0] == [-100.3094, 25.6714]
    assert plan.geometria.coordinates[1] == [-100.2900, 25.6600]

def test_rendimiento_branch_and_bound_8_paradas_menor_25ms():
    p0 = Punto(lat=25.6714, lon=-100.3094)
    t0 = datetime.now(timezone.utc)
    # 4 pedidos con recolección y entrega = 8 paradas (sin podar serían 8! = 40,320 permutaciones)
    p_act = [
        PedidoActivo(pedido_id="p1", app="uber", origen=Punto(lat=25.680, lon=-100.315), destino=Punto(lat=25.660, lon=-100.290), recogido=False),
        PedidoActivo(pedido_id="p2", app="didi", origen=Punto(lat=25.675, lon=-100.312), destino=Punto(lat=25.658, lon=-100.295), recogido=False),
        PedidoActivo(pedido_id="p3", app="rappi", origen=Punto(lat=25.672, lon=-100.311), destino=Punto(lat=25.665, lon=-100.292), recogido=False),
    ]
    oferta = OfertaEntrante(
        oferta_id="of-4", pedido_id="p4", app="uber",
        origen=Punto(lat=25.678, lon=-100.314), destino=Punto(lat=25.661, lon=-100.291), precio_mxn=70.0
    )
    items, carga = generar_items_paradas(p_act, oferta, t0)
    assert len(items) == 8

    t_inicio = time.perf_counter()
    sec, dist, dur, evals, motivo = resolver_secuencia_optima(p0, items, carga, capacidad_max=4, t0=t0)
    t_dur_ms = (time.perf_counter() - t_inicio) * 1000.0

    assert sec is not None
    # Con branch-and-bound debe podar agresivamente y terminar en menos de 25 ms
    assert t_dur_ms < 25.0, f"DFS Branch-and-Bound tardó más de 25ms: {t_dur_ms:.2f}ms"
    print(f"8 paradas resueltas en {t_dur_ms:.2f} ms ({evals} hojas evaluadas)")

