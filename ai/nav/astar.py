"""FASE C (NIVEL-1-DEMO-MTY.md): A* propio sobre el grafo vial ruteable de Monterrey
(`vygo.nav.grafo.cargar_grafo_ruteable`). Éste es el algoritmo de navegación que se
presenta como propio: usa `networkx.astar_path`, pero la heurística la escribimos
nosotros, y ahí está todo el riesgo.

El peso de las aristas es `travel_time`, en SEGUNDOS (`geo.grafo.cargar_grafo` ya corre
`ox.routing.add_edge_travel_times`). La heurística tiene que devolver también SEGUNDOS
-- si devolviera metros, sobreestimaría por un factor de ~25 (la velocidad máxima del
grafo, 25 m/s), la heurística dejaría de ser ADMISIBLE, y `nx.astar_path` ya no
garantiza el camino más corto (NetworkX lo advierte explícitamente en su documentación).

Por qué se divide entre la velocidad MÁXIMA del grafo y nunca la promedio: la
admisibilidad exige que la heurística NUNCA sobreestime el costo real de llegar a la
meta. Ningún tramo real puede tomar menos tiempo que recorrer su distancia en línea
recta a la velocidad más alta que existe en todo el grafo -- así que
`haversine(n, meta) / v_max` es SIEMPRE <= el `travel_time` real de cualquier camino
posible entre n y meta. Con la velocidad PROMEDIO, en cambio, cualquier tramo más rápido
que el promedio (una vía rápida, por ejemplo) haría que la heurística sobreestime ese
tramo -- exactamente la inadmisibilidad que rompe la garantía de optimalidad.

El grafo es un MULTIGRAFO (`nx.MultiDiGraph`): puede haber varias aristas entre el mismo
par de nodos (p.ej. una vía dividida con carriles en direcciones ligeramente distintas
representados por separado). `nx.astar_path` ya resuelve esto internamente al buscar
-- `networkx.algorithms.shortest_paths.weighted._weight_function` usa
`min(travel_time de las aristas paralelas)` cuando el grafo es multigrafo (verificado
en el código fuente de networkx antes de escribir este módulo, no supuesto). Al
RECONSTRUIR segundos/metros sobre el camino ya encontrado, `ruta_astar` usa el mismo
criterio -- la arista de MENOR `travel_time` entre cada par consecutivo -- para que la
suma sea consistente con lo que A* realmente optimizó, no con una arista arbitraria.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

import networkx as nx

_RADIO_TIERRA_M = 6_371_000.0


def _haversine_metros(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distancia del círculo máximo entre dos puntos (lon, lat) en grados, en metros."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _RADIO_TIERRA_M * math.asin(math.sqrt(min(1.0, a)))


def heuristica_tiempo(G: nx.MultiDiGraph, v_max_ms: float) -> Callable[[int, int], float]:
    """Devuelve `h(n, meta) = haversine_metros(n, meta) / v_max_ms`, en SEGUNDOS.

    Los nodos de OSMnx traen `x` = longitud, `y` = latitud (no al revés)."""

    def h(n: int, meta: int) -> float:
        x1, y1 = G.nodes[n]["x"], G.nodes[n]["y"]
        x2, y2 = G.nodes[meta]["x"], G.nodes[meta]["y"]
        return _haversine_metros(x1, y1, x2, y2) / v_max_ms

    return h


def _arista_mas_rapida(G: nx.MultiDiGraph, u: int, v: int) -> dict:
    """Entre las aristas paralelas u->v, la de menor `travel_time` -- mismo criterio que
    usa `nx.astar_path` internamente para grafos multigrafo (ver docstring del módulo)."""

    aristas = G[u][v]
    mejor_key = min(aristas, key=lambda k: aristas[k]["travel_time"])
    return aristas[mejor_key]


def ruta_astar(
    G: nx.MultiDiGraph, nodo_origen: int, nodo_destino: int, v_max_ms: float,
) -> Optional[dict]:
    """`nx.astar_path(G, o, d, heuristic=..., weight='travel_time')`.

    Devuelve `{"segundos": float, "metros": float, "polilinea": [[lon, lat], ...],
    "nodos": int}` -- polilínea en orden GeoJSON, lista para MapLibre. `segundos` y
    `metros` se acumulan arista por arista sobre el camino devuelto, tomando siempre la
    de menor `travel_time` entre aristas paralelas. `None` si no hay camino."""

    h = heuristica_tiempo(G, v_max_ms)
    try:
        camino = nx.astar_path(G, nodo_origen, nodo_destino, heuristic=h, weight="travel_time")
    except nx.NetworkXNoPath:
        return None

    segundos = 0.0
    metros = 0.0
    for u, v in zip(camino[:-1], camino[1:]):
        datos = _arista_mas_rapida(G, u, v)
        segundos += datos["travel_time"]
        metros += datos["length"]

    polilinea = [[G.nodes[n]["x"], G.nodes[n]["y"]] for n in camino]

    return {"segundos": segundos, "metros": metros, "polilinea": polilinea, "nodos": len(camino)}
