"""FASE B (NIVEL-1-DEMO-MTY.md): grafo vial real de Monterrey (OSMnx) para la Fase C
(A* propio). Se descarga UNA VEZ y se cachea en disco -- todo lo demás (Fase C en
adelante) es offline.

BBOX_MTY cubre Centro, Barrio Antiguo, Obispado y Mitras: zona densa en restaurantes y
casi toda del mismo lado del río Santa Catarina, lejos de la Loma Larga -- elimina por
construcción el problema de rutas que cruzan donde no hay puente. No cambiarlo sin avisar
(nota de dimensiones ya verificada: el grid del simulador es 20x20 a 0.5 km/celda = 10x10
km; este bbox mide ~12.0 x 9.9 km, cabe sin expandir).

Orden de descarga, exacto (no reordenar): `graph_from_bbox(network_type="drive")` --
"drive" respeta sentidos únicos, que en el centro de Monterrey importan muchísimo --
luego `add_edge_speeds` (imputa `speed_kph`), luego `add_edge_travel_times` (crea
`travel_time` en SEGUNDOS), luego `save_graphml`.
"""

from __future__ import annotations

# Debe ir ANTES de importar osmnx/requests: hace que `ssl`/`requests` usen el almacén de
# certificados del SISTEMA OPERATIVO (Windows) en vez del bundle embebido de `certifi`.
# Esta red intercepta HTTPS con un proxy corporativo cuya CA Windows ya conoce y en la
# que ya confía (el navegador funciona en esta misma red) pero que `certifi` no trae --
# de ahí el `CERTIFICATE_VERIFY_FAILED` al pegarle a Overpass. Esto NO desactiva la
# verificación de certificados: la verificación sigue activa, sólo cambia de dónde salen
# las CAs de confianza (del almacén de Windows, no del bundle de certifi).
import truststore

truststore.inject_into_ssl()

from pathlib import Path

import networkx as nx
import osmnx as ox

BBOX_MTY = (-100.360, 25.630, -100.240, 25.720)  # (izq, abajo, der, arriba) = (left, bottom, right, top)

_AI_NAV_DIR = Path(__file__).resolve().parent
RUTA_CACHE = _AI_NAV_DIR / "cache" / "mty_drive.graphml"  # == "ai/nav/cache/mty_drive.graphml"


def cargar_grafo() -> nx.MultiDiGraph:
    """Si existe el cache lo carga; si no, lo descarga y lo guarda."""

    if RUTA_CACHE.exists():
        return ox.io.load_graphml(RUTA_CACHE)

    G = ox.graph_from_bbox(BBOX_MTY, network_type="drive")
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)

    RUTA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ox.io.save_graphml(G, RUTA_CACHE)
    return G


def velocidad_maxima_ms(G: nx.MultiDiGraph) -> float:
    """Máximo de speed_kph sobre todas las aristas, convertido a m/s."""

    velocidades_kph = [datos["speed_kph"] for _u, _v, datos in G.edges(data=True) if "speed_kph" in datos]
    return max(velocidades_kph) / 3.6


if __name__ == "__main__":
    G = cargar_grafo()
    n_nodos = G.number_of_nodes()
    n_aristas = G.number_of_edges()
    mb = RUTA_CACHE.stat().st_size / (1024 * 1024)
    print(f"nodos={n_nodos}  aristas={n_aristas}  archivo={RUTA_CACHE} ({mb:.2f} MB)")
    print(f"velocidad_maxima_ms={velocidad_maxima_ms(G):.2f}")
