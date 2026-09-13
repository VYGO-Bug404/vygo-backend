"""FASE C (NIVEL-1-DEMO-MTY.md), Compuerta C: valida `vygo.nav.astar` sobre 30 pares
aleatorios (semilla fija) del grafo RUTEABLE (`grafo.cargar_grafo_ruteable` -- mayor
componente fuertemente conexa, 14690 de 15007 nodos; nunca el grafo completo, ver
docstring de `cargar_grafo_ruteable`: los ~317 nodos fuera de ahí no tienen camino de
vuelta y `nx.astar_path` devolvería infactibilidades que no son un bug de A*).

Tres pruebas por par:
1. Conexo: cada par consecutivo del camino es una arista real del grafo.
2. `segundos` coincide con `nx.shortest_path_length(G, o, d, weight='travel_time')`
   (Dijkstra) dentro de 0.1% -- si esto falla, la heurística NO es admisible.
3. La polilínea tiene al menos tantos puntos como nodos el camino.

Uso: `python -m pytest ai/nav/test_astar.py -v` (Compuerta C).
`python ai/nav/test_astar.py` (sin pytest) imprime además el resumen de rendimiento
(A* promedio, Dijkstra promedio, desviación peor caso) sobre los mismos 30 pares.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import networkx as nx
import pytest

_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

from nav.astar import heuristica_tiempo, ruta_astar  # noqa: E402
from nav.grafo import cargar_grafo_ruteable, velocidad_maxima_ms  # noqa: E402

SEMILLA = 42
N_PARES = 30
TOLERANCIA_RELATIVA = 0.001  # 0.1%


def _generar_pares(G: nx.MultiDiGraph, n: int, seed: int) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    nodos = list(G.nodes())
    pares: list[tuple[int, int]] = []
    while len(pares) < n:
        o, d = rng.choice(nodos), rng.choice(nodos)
        if o != d:
            pares.append((o, d))
    return pares


def _medir(G: nx.MultiDiGraph, v_max_ms: float, pares: list[tuple[int, int]]) -> list[dict]:
    """Por cada par: corre `ruta_astar` (cronometrado -- es la función bajo prueba),
    recalcula el camino de nodos crudo vía `nx.astar_path` directo (sin cronometrar --
    sólo para verificar conectividad; determinista, mismo resultado que adentro de
    `ruta_astar`), y corre Dijkstra de referencia (cronometrado, para el benchmark)."""

    h = heuristica_tiempo(G, v_max_ms)
    mediciones = []
    for o, d in pares:
        t0 = time.perf_counter()
        resultado = ruta_astar(G, o, d, v_max_ms)
        t_astar_s = time.perf_counter() - t0

        camino = nx.astar_path(G, o, d, heuristic=h, weight="travel_time")

        t0 = time.perf_counter()
        segundos_dijkstra = nx.shortest_path_length(G, o, d, weight="travel_time")
        t_dijkstra_s = time.perf_counter() - t0

        mediciones.append({
            "origen": o, "destino": d, "camino": camino, "resultado": resultado,
            "t_astar_s": t_astar_s, "segundos_dijkstra": segundos_dijkstra, "t_dijkstra_s": t_dijkstra_s,
        })
    return mediciones


def _resumen_benchmark(mediciones: list[dict]) -> dict:
    n = len(mediciones)
    t_astar_ms = [m["t_astar_s"] * 1000.0 for m in mediciones]
    t_dijkstra_ms = [m["t_dijkstra_s"] * 1000.0 for m in mediciones]
    desviaciones_pct = [
        abs(m["resultado"]["segundos"] - m["segundos_dijkstra"]) / m["segundos_dijkstra"] * 100.0
        for m in mediciones
    ]
    fuera_de_tolerancia = sum(1 for d in desviaciones_pct if d > TOLERANCIA_RELATIVA * 100.0)
    return {
        "astar_promedio_ms": sum(t_astar_ms) / n,
        "dijkstra_promedio_ms": sum(t_dijkstra_ms) / n,
        "desviacion_peor_caso_pct": max(desviaciones_pct),
        "fuera_de_tolerancia": fuera_de_tolerancia,
        "n_pares": n,
    }


@pytest.fixture(scope="module")
def grafo() -> nx.MultiDiGraph:
    return cargar_grafo_ruteable()


@pytest.fixture(scope="module")
def v_max(grafo: nx.MultiDiGraph) -> float:
    return velocidad_maxima_ms(grafo)


@pytest.fixture(scope="module")
def mediciones(grafo: nx.MultiDiGraph, v_max: float) -> list[dict]:
    pares = _generar_pares(grafo, N_PARES, SEMILLA)
    return _medir(grafo, v_max, pares)


def test_camino_conexo(grafo: nx.MultiDiGraph, mediciones: list[dict]) -> None:
    for m in mediciones:
        camino = m["camino"]
        assert len(camino) >= 2, f"camino con menos de 2 nodos: {camino}"
        for u, v in zip(camino[:-1], camino[1:]):
            assert grafo.has_edge(u, v), f"({u}, {v}) no es una arista real del grafo (par {m['origen']}->{m['destino']})"


def test_segundos_coincide_con_dijkstra(mediciones: list[dict]) -> None:
    for m in mediciones:
        assert m["resultado"] is not None, f"ruta_astar devolvió None para {m['origen']}->{m['destino']}"
        segundos_astar = m["resultado"]["segundos"]
        segundos_dijkstra = m["segundos_dijkstra"]
        tolerancia = TOLERANCIA_RELATIVA * segundos_dijkstra
        assert abs(segundos_astar - segundos_dijkstra) <= tolerancia, (
            f"par {m['origen']}->{m['destino']}: A*={segundos_astar:.4f}s vs "
            f"Dijkstra={segundos_dijkstra:.4f}s -- heurística probablemente inadmisible"
        )


def test_polilinea_longitud(mediciones: list[dict]) -> None:
    for m in mediciones:
        resultado = m["resultado"]
        assert len(resultado["polilinea"]) >= len(m["camino"]), (
            f"par {m['origen']}->{m['destino']}: polilinea con {len(resultado['polilinea'])} "
            f"puntos, camino con {len(m['camino'])} nodos"
        )


if __name__ == "__main__":
    G = cargar_grafo_ruteable()
    v_max_ms = velocidad_maxima_ms(G)
    pares = _generar_pares(G, N_PARES, SEMILLA)
    mediciones_ = _medir(G, v_max_ms, pares)
    r = _resumen_benchmark(mediciones_)
    print(f"pares={r['n_pares']}")
    print(f"A* promedio: {r['astar_promedio_ms']:.2f} ms")
    print(f"Dijkstra promedio: {r['dijkstra_promedio_ms']:.2f} ms")
    print(f"desviación peor caso vs Dijkstra: {r['desviacion_peor_caso_pct']:.4f}%, "
          f"{r['fuera_de_tolerancia']} de {r['n_pares']} pares fuera de tolerancia (0.1%)")
